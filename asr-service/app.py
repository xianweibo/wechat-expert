"""whisper.cpp ASR HTTP 服务 - NAS 字幕兜底入口。
POST /asr  { "audio_path": "/tmp/asr/xxx.m4a" } -> { text, language, duration_s }
要求 audio_path 是容器内已挂载/已存在的文件（由上游 ffprobe 写好）。
为安全起见只接受 /tmp/asr/ 下的路径。
"""
import os
import shutil
import logging
import time
import traceback
from flask import Flask, request, jsonify

from transcribe import transcribe_audio

MODEL_PATH = os.environ.get("MODEL_PATH", "/opt/models/ggml-small.bin")
LANG = os.environ.get("LANG", "zh")
SAFE_DIR = "/tmp/asr"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = app.logger


@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "model": os.path.basename(MODEL_PATH),
        "model_size_mb": round(os.path.getsize(MODEL_PATH) / 1024 / 1024, 1) if os.path.isfile(MODEL_PATH) else None,
    })


@app.post("/asr")
def asr():
    payload = request.get_json(silent=True) or {}
    # 支持两种入参：audio_path(本地已落盘) 或 audio_b64(从上游传来)
    audio_b64 = payload.get("audio_b64", "").strip()
    audio_path = payload.get("audio_path", "").strip()
    bvid = payload.get("bvid", "unknown")

    if audio_b64:
        import base64
        try:
            data = base64.b64decode(audio_b64)
        except Exception as e:
            return jsonify({"ok": False, "error": f"base64 decode: {e}"}), 400
        if not data or len(data) < 1024:
            return jsonify({"ok": False, "error": "audio data too small"}), 400
        # 写到本地临时文件
        audio_abs = os.path.join(SAFE_DIR, f"{bvid}.m4a")
        with open(audio_abs, "wb") as f:
            f.write(data)
    elif audio_path:
        audio_abs = os.path.abspath(audio_path)
        if not audio_abs.startswith(SAFE_DIR + os.sep):
            return jsonify({"ok": False, "error": f"audio_path must be under {SAFE_DIR}"}), 400
        if not os.path.isfile(audio_abs):
            return jsonify({"ok": False, "error": f"audio not found: {audio_abs}"}), 404
    else:
        return jsonify({"ok": False, "error": "audio_b64 or audio_path required"}), 400

    t0 = time.time()
    try:
        result = transcribe_audio(audio_abs, MODEL_PATH, lang=LANG)
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "transcribe timeout (>30min)"}), 504
    except Exception as e:
        log.error(f"transcribe error: {e}\n{traceback.format_exc()}")
        return jsonify({"ok": False, "error": str(e)[:200]}), 500
    finally:
        # 立即删除临时音频（设计要求：算完就删）
        try:
            os.remove(audio_abs)
            for ext in (".json", ".srt", ".txt", ".vtt", ".tsv", ".out"):
                p = audio_abs + ext
                if os.path.isfile(p):
                    os.remove(p)
        except OSError:
            pass

    text = result["text"] or ""
    log.info(f"asr done: chars={len(text)} wall_s={result['duration_s']:.1f} total_s={time.time()-t0:.1f}")
    return jsonify({
        "ok": True,
        "text": text,
        "language": result["language"],
        "transcribe_seconds": round(result["duration_s"], 1),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 41092)))
