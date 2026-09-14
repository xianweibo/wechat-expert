"""调用 whisper.cpp (whisper-cli) 跑转写，输出 SRT + 纯文本。
whisper.cpp 中文 small 模型在 CPU 28 核机器上约 0.3-0.5x 实时率。
"""
import json
import subprocess
import os
import time


def transcribe_audio(audio_path: str, model_path: str, lang: str = "zh",
                     extra_args: list | None = None) -> dict:
    """返回 { text, language, duration_s, segments }。"""
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(audio_path)
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"model not found: {model_path}")

    whisper_bin = os.environ.get("WHISPER_BIN", "whisper-cli")
    if not os.path.isabs(whisper_bin) and not os.path.isfile(whisper_bin):
        # PATH 找不到，尝试在常见位置
        for cand in ["/usr/local/bin/whisper-cli", "/usr/bin/whisper-cli"]:
            if os.path.isfile(cand):
                whisper_bin = cand
                break
    if not os.path.isfile(whisper_bin):
        raise FileNotFoundError(f"whisper binary not found (WHISPER_BIN={whisper_bin})")

    out_prefix = audio_path + ".out"
    cmd = [
        whisper_bin,
        "-m", model_path,
        "-f", audio_path,
        "-l", lang,
        "--output-json",
        "--output-file", out_prefix,
        "--print-progress", "false",
        "--threads", str(min(8, os.cpu_count() or 4)),
    ]
    if extra_args:
        cmd.extend(extra_args)

    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    wall_s = time.time() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"whisper-cli exit={proc.returncode} stderr={proc.stderr[-500:]}")

    json_path = out_prefix + ".json"
    if not os.path.isfile(json_path):
        # fallback: 从 stdout 解析
        text = (proc.stdout or "").strip()
        return {"text": text, "language": lang, "duration_s": wall_s, "segments": []}

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    text = (data.get("text") or "").strip()
    return {
        "text": text,
        "language": data.get("language") or lang,
        "duration_s": wall_s,
        "segments": data.get("segments") or [],
    }
