from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import chess
import chess.pgn

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_PATH = Path(os.getenv("CHESS_COACH_DB", "chess_coach_v11.db"))
_db_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
  id TEXT PRIMARY KEY, created_at DOUBLE PRECISION NOT NULL, pgn TEXT NOT NULL,
  result TEXT, white TEXT, black TEXT, report_json TEXT
);
CREATE TABLE IF NOT EXISTS training (
  id BIGSERIAL PRIMARY KEY, created_at DOUBLE PRECISION NOT NULL,
  kind TEXT NOT NULL, score DOUBLE PRECISION, topic TEXT, payload_json TEXT
);
CREATE TABLE IF NOT EXISTS profile (
  key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS puzzles (
  id TEXT PRIMARY KEY, created_at DOUBLE PRECISION NOT NULL, fen TEXT NOT NULL,
  solution_uci TEXT NOT NULL, topic TEXT, source_game TEXT,
  difficulty DOUBLE PRECISION, payload_json TEXT
);
CREATE TABLE IF NOT EXISTS lessons (
  id TEXT PRIMARY KEY, created_at DOUBLE PRECISION NOT NULL, topic TEXT NOT NULL,
  title TEXT NOT NULL, body TEXT NOT NULL, payload_json TEXT
);
CREATE TABLE IF NOT EXISTS achievements (
  id TEXT PRIMARY KEY, created_at DOUBLE PRECISION NOT NULL, kind TEXT NOT NULL,
  title TEXT NOT NULL, detail TEXT NOT NULL
);
"""

SQLITE_SCHEMA = SCHEMA.replace("DOUBLE PRECISION", "REAL").replace("BIGSERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")


def connect():
    if DATABASE_URL:
        import psycopg
        con = psycopg.connect(DATABASE_URL)
        con.row_factory = psycopg.rows.dict_row
        return con
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def _execute_script(con):
    if DATABASE_URL:
        for statement in SCHEMA.split(";"):
            if statement.strip():
                con.execute(statement)
        con.commit()
    else:
        con.executescript(SQLITE_SCHEMA)


def _execute(con, sql, params=()):
    if DATABASE_URL:
        return con.execute(sql.replace("?", "%s"), params)
    return con.execute(sql, params)


def init_db():
    with _db_lock, connect() as con:
        _execute_script(con)


def save_profile(key: str, value: Any):
    with _db_lock, connect() as con:
        if DATABASE_URL:
            _execute(con, "INSERT INTO profile(key,value_json,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at", (key, json.dumps(value), time.time()))
        else:
            _execute(con, "INSERT INTO profile(key,value_json,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at", (key, json.dumps(value), time.time()))
        con.commit()


def load_profile(key: str, default=None):
    with connect() as con:
        row = _execute(con, "SELECT value_json FROM profile WHERE key=?", (key,)).fetchone()
    return json.loads(row["value_json"]) if row else default


def save_game(pgn: str, report: dict | None = None) -> str:
    gid = str(uuid.uuid4())
    game = chess.pgn.read_game(__import__("io").StringIO(pgn))
    headers = dict(game.headers) if game else {}
    with _db_lock, connect() as con:
        _execute(con, "INSERT INTO games VALUES(?,?,?,?,?,?,?)",
                 (gid, time.time(), pgn, headers.get("Result"), headers.get("White"),
                  headers.get("Black"), json.dumps(report) if report else None))
        con.commit()
    return gid


def save_training(kind: str, score: float | None, topic: str | None, payload: dict):
    with _db_lock, connect() as con:
        _execute(con, "INSERT INTO training(created_at,kind,score,topic,payload_json) VALUES(?,?,?,?,?)",
                 (time.time(), kind, score, topic, json.dumps(payload)))
        con.commit()


def recent_games(limit=20):
    with connect() as con:
        rows = _execute(con, "SELECT id,created_at,result,white,black,report_json FROM games ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    out=[]
    for r in rows:
        d=dict(r)
        d["report"]=json.loads(d.pop("report_json")) if d.get("report_json") else None
        out.append(d)
    return out


def training_history(limit=100):
    with connect() as con:
        rows=_execute(con, "SELECT created_at,kind,score,topic,payload_json FROM training ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [{**dict(r), "payload": json.loads(r["payload_json"])} for r in rows]


def profile_from_games():
    games=recent_games(200)
    counts={"games":len(games),"moves":0,"brilliant":0,"good":0,"inaccuracy":0,"mistake":0,"blunder":0}
    losses=[]
    topics={"Opening":0,"Middlegame":0,"Tactics":0,"Endgame":0,"Defense":0,"Calculation":0,
            "Threat Detection":0,"King Safety":0,"Positional Understanding":0,"Conversion":0,
            "Time Management":0,"Piece Activity":0,"Pawn Structure":0,"Attacking":0}
    for g in games:
        report=g.get("report") or {}
        for m in report.get("moves",[]):
            counts["moves"]+=1
            label=str(m.get("label","Good")).lower()
            if label in counts: counts[label]+=1
            if isinstance(m.get("loss_cp"),(int,float)): losses.append(max(0,m["loss_cp"]))
            facts=m.get("facts") or {}
            if facts.get("capture") or facts.get("check"): topics["Tactics"]+=1
            if label=="blunder": topics["Threat Detection"]+=1; topics["Calculation"]+=1
            if label in ("mistake","inaccuracy"): topics["Calculation"]+=1
            if facts.get("check") or facts.get("checkmate"): topics["Attacking"]+=1
        summary=report.get("summary") or {}
        if summary.get("blunders",0): topics["King Safety"]+=summary["blunders"]
    accuracy=max(0,min(100,round(100-(sum(losses)/len(losses) if losses else 0)/8)))
    base=max(400,min(2400,round(700+accuracy*10)))
    skills={}
    for name in topics:
        penalty=counts["blunder"]*18 if name in ("Tactics","Calculation","Threat Detection") else counts["blunder"]*12 if name in ("Defense","King Safety") else counts["mistake"]*5
        skills[name]=max(400,min(2400,base-penalty+min(300,topics[name]*2)))
    profile={"estimated_elo":base,"accuracy":accuracy,"counts":counts,"skills":skills,
             "note":"Estimated coaching indicators only, not official FIDE, Chess.com, or other ratings."}
    save_profile("player",profile)
    return profile


def weakness_report():
    p=profile_from_games(); c=p["counts"]; candidates=[]
    if c["blunder"]: candidates.append(("Threat Detection",c["blunder"]*3,"repeated blunder-level evaluation loss"))
    if c["mistake"]: candidates.append(("Calculation",c["mistake"]*2,"repeated calculation/decision errors"))
    if c["inaccuracy"]: candidates.append(("Precision",c["inaccuracy"],"frequent second-best choices"))
    if not candidates: candidates.append(("Tactical sharpness",1,"not enough serious errors in the stored sample"))
    candidates.sort(key=lambda x:x[1],reverse=True)
    return [{"topic":a,"signal":b,"reason":d} for a,b,d in candidates[:5]]


def validate_puzzle(fen: str, solution_uci: str):
    board=chess.Board(fen); move=chess.Move.from_uci(solution_uci)
    if move not in board.legal_moves: return False, "Solution is illegal."
    return True, "OK"


def generate_puzzle(engine, topic="Tactics"):
    games=recent_games(100)
    for g in games:
        report=g.get("report") or {}
        for m in report.get("moves",[]):
            label=str(m.get("label","")).lower()
            if label in ("blunder","mistake","inaccuracy"):
                fen=m.get("fen_before"); best=m.get("best_move_uci")
                if fen and best and validate_puzzle(fen,best)[0]:
                    source=g["id"]; difficulty=min(2400,max(600,900+(m.get("loss_cp") or 0)))
                    p={"fen":fen,"solution_uci":best,"topic":topic,"source_game":source,"difficulty":difficulty}
                    pid=str(uuid.uuid4())
                    with _db_lock,connect() as con:
                        _execute(con,"INSERT INTO puzzles VALUES(?,?,?,?,?,?,?,?)",(pid,time.time(),fen,best,topic,source,difficulty,json.dumps(p))); con.commit()
                    return {"id":pid,**p}
    board=chess.Board(); info=engine.analyse(board,depth=12,multipv=1,time_limit=.25); move=(info.get("pv") or [None])[0]
    if not move: return None
    pid=str(uuid.uuid4()); p={"fen":board.fen(),"solution_uci":move.uci(),"topic":topic,"source_game":None,"difficulty":1000}
    with _db_lock,connect() as con:
        _execute(con,"INSERT INTO puzzles VALUES(?,?,?,?,?,?,?,?)",(pid,time.time(),p["fen"],p["solution_uci"],topic,None,1000,json.dumps(p))); con.commit()
    return {"id":pid,**p}


init_db()
