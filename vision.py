"""Vision/OCR integration point for Chess Coach AI v2.3.

This starter module validates image input and provides a clear place to connect
an actual chessboard-recognition or OCR model later.
"""
from pathlib import Path

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def validate_image(path: str) -> tuple[bool, str]:
    file_path = Path(path)
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False, "Unsupported image type. Use PNG, JPG, JPEG, or WEBP."
    if not file_path.exists():
        return False, "Image file does not exist."
    if file_path.stat().st_size > MAX_IMAGE_BYTES:
        return False, "Image is too large. Maximum size is 5 MB."
    return True, "Image is valid."


def recognize_chess_position(path: str) -> dict:
    """Placeholder for real vision/OCR recognition.

    Return a structured error until a vision model is connected. Do not treat
    this fallback as successful board recognition.
    """
    valid, message = validate_image(path)
    if not valid:
        return {"ok": False, "error": message}
    return {
        "ok": False,
        "error": "Vision/OCR model is not configured yet.",
        "next_step": "Connect a chessboard-recognition and OCR model here.",
    }
