from __future__ import annotations

import os
import json
import io
from flask import Blueprint, jsonify, request

from v11_system import (
    save_game, save_training, recent_games, training_history, profile_from_games,
    weakness_report, generate_puzzle, validate_puzzle, load_profile
)

v11 = Blueprint("v11", __name__, url_prefix="/api/v11")


def register_v11(app, engine):
    v11.engine = engine
    app.register_blueprint(v11)


@v11.get("/health")
def health():
    return jsonify({"version":"11.0","status":"ok","engine":v11.engine.status()})


@v11.get("/profile")
def get_profile():
    return jsonify(profile_from_games())


@v11.get("/dashboard")
def dashboard():
    profile=profile_from_games()
    games=recent_games(12)
    history=training_history(50)
    weaknesses=weakness_report()
    return jsonify({"profile":profile,"games":games,"training":history,"weaknesses":weaknesses,
                    "loop":["Play","Analyze","Understand","Detect Weaknesses","Targeted Training","Practice","Track Improvement"]})


@v11.post("/game/save")
def game_save():
    data=request.get_json(silent=True) or {}
    pgn=str(data.get("pgn","")).strip()
    report=data.get("report")
    if not pgn: return jsonify({"error":"PGN is required."}),400
    try:
        gid=save_game(pgn,report)
        profile_from_games()
        return jsonify({"id":gid,"saved":True})
    except Exception as exc:
        return jsonify({"error":str(exc)}),400


@v11.get("/games")
def games():
    return jsonify({"games":recent_games(100)})


@v11.get("/training")
def training():
    return jsonify({"training":training_history(200)})


@v11.post("/training/result")
def training_result():
    data=request.get_json(silent=True) or {}
    kind=str(data.get("kind","practice"))
    score=data.get("score")
    topic=data.get("topic")
    save_training(kind,float(score) if score is not None else None,topic,data)
    return jsonify({"saved":True,"profile":profile_from_games()})


@v11.get("/weaknesses")
def weaknesses():
    return jsonify({"weaknesses":weakness_report()})


@v11.post("/fen/validate")
def fen_validate():
    data=request.get_json(silent=True) or {}
    fen=str(data.get("fen","")).strip()
    if not fen: return jsonify({"valid":False,"error":"FEN is required."}),400
    try:
        import chess
        b=chess.Board(fen)
        return jsonify({"valid":True,"fen":b.fen(),"turn":"White" if b.turn else "Black",
                        "is_check":b.is_check(),"is_game_over":b.is_game_over(),
                        "legal_moves":b.legal_moves.count()})
    except Exception as exc:
        return jsonify({"valid":False,"error":str(exc)}),400


@v11.post("/fen/analyze")
def fen_analyze():
    data=request.get_json(silent=True) or {}
    fen=str(data.get("fen","")).strip()
    depth=max(8,min(20,int(data.get("depth",12))))
    try:
        import chess
        b=chess.Board(fen)
        infos=v11.engine.analyse(b,depth=depth,multipv=3,time_limit=.35)
        if not isinstance(infos,list): infos=[infos]
        lines=[]
        for info in infos:
            pv=info.get("pv") or []
            lines.append({"score":str(info.get("score")),"best_move":pv[0].uci() if pv else None,
                          "pv":[m.uci() for m in pv[:10]]})
        return jsonify({"fen":b.fen(),"lines":lines})
    except Exception as exc:
        return jsonify({"error":str(exc)}),400


@v11.post("/puzzle/new")
def puzzle_new():
    data=request.get_json(silent=True) or {}
    topic=str(data.get("topic") or (weakness_report()[0]["topic"] if weakness_report() else "Tactics"))
    try:
        p=generate_puzzle(v11.engine,topic)
        return jsonify(p or {"error":"No verified puzzle available."}),200 if p else 503
    except Exception as exc:
        return jsonify({"error":str(exc)}),400


@v11.post("/puzzle/check")
def puzzle_check():
    data=request.get_json(silent=True) or {}
    fen=str(data.get("fen","")).strip()
    uci=str(data.get("uci","")).strip()
    expected=str(data.get("solution_uci","")).strip()
    try:
        ok,_=validate_puzzle(fen,uci)
        correct=ok and uci==expected
        if ok:
            import chess
            b=chess.Board(fen); san=b.san(chess.Move.from_uci(uci))
        else: san=None
        save_training("puzzle",1 if correct else 0,data.get("topic"),{"fen":fen,"uci":uci,"correct":correct})
        return jsonify({"legal":ok,"correct":correct,"san":san,"message":"Correct! Verified by legal move validation." if correct else "Not the solution. Recalculate checks, captures, and threats."})
    except Exception as exc:
        return jsonify({"error":str(exc)}),400


@v11.post("/practice/move")
def practice_move():
    data=request.get_json(silent=True) or {}
    fen=str(data.get("fen","")).strip()
    try:
        import chess
        b=chess.Board(fen)
        info=v11.engine.analyse(b,depth=12,multipv=1,time_limit=.3)
        pv=info.get("pv") or []
        if not pv: return jsonify({"error":"No engine move."}),503
        move=pv[0]
        return jsonify({"uci":move.uci(),"san":b.san(move),"fen":b.fen(),
                        "training_level":data.get("training_level",1200)})
    except Exception as exc:
        return jsonify({"error":str(exc)}),400


@v11.post("/coach/explain")
def coach_explain():
    data=request.get_json(silent=True) or {}
    prompt=str(data.get("prompt","")).strip()
    context=data.get("context") or {}
    key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return jsonify({"configured":False,"message":"Gemini is not configured. Set GEMINI_API_KEY on the server."})
    try:
        from google import genai
        client=genai.Client(api_key=key)
        model=os.getenv("GEMINI_MODEL","gemini-2.5-flash-lite")
        system=("You are the teaching layer of a chess coach. Stockfish is authoritative for calculation. "
                "Never invent engine evaluations. Explain the supplied chess facts in clear language, "
                "give practical advice, and target the player's recurring weaknesses. "
                "Do not claim an estimated rating is official.")
        text=(system+"\nCONTEXT:\n"+json.dumps(context)[:12000]+"\nQUESTION:\n"+prompt[:4000])
        result=client.models.generate_content(model=model,contents=text)
        return jsonify({"configured":True,"text":getattr(result,"text","")})
    except Exception as exc:
        return jsonify({"configured":True,"error":"Gemini request failed.","detail":str(exc)}),502


@v11.get("/best-move-of-day")
def best_move_of_day():
    games=recent_games(100)
    best=None
    for g in games:
        report=g.get("report") or {}
        for m in report.get("moves",[]):
            if str(m.get("label","")).lower()=="brilliant":
                best=m
                break
        if best: break
    if not best:
        for g in games:
            report=g.get("report") or {}
            for m in report.get("moves",[]):
                if str(m.get("label","")).lower()=="good":
                    best=m; break
            if best: break
    return jsonify({"move":best,"message":"A great move from your stored games." if best else "Analyze more games to unlock this."})


@v11.get("/daily")
def daily():
    w=weakness_report()
    topic=w[0]["topic"] if w else "Tactics"
    puzzle=generate_puzzle(v11.engine,topic)
    return jsonify({"topic":topic,"puzzle":puzzle,
                    "activities":[
                      {"type":"puzzle","title":"Targeted puzzle","topic":topic},
                      {"type":"lesson","title":"Explain one mistake without the engine"},
                      {"type":"review","title":"Replay one turning point"},
                      {"type":"practice","title":"Play one unrated training game"}]})
