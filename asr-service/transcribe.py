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
    # whisper-cli 只支持 wav/flac/mp3/ogg。B站 audio URL 是 m4s(MP4 fMP4), 先转 wav
    wav_path = audio_path + ".wav"
    ext = os.path.splitext(audio_path)[1].lower()
    if ext not in (".wav", ".flac", ".mp3", ".ogg"):
        # ffmpeg 转 16k mono wav (whisper 推荐采样率)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path,
             "-ar", "16000", "-ac", "1", "-f", "wav", wav_path],
            check=True, timeout=600,
        )
        actual_input = wav_path
    else:
        actual_input = audio_path

    cmd = [
        whisper_bin,
        "-m", model_path,
        "-f", actual_input,
        "-l", lang,
        "--output-json",
        "--output-file", out_prefix,
        "--print-progress", "false",
        "--threads", str(min(8, os.cpu_count() or 4)),
        # 关键参数: 解决长音频被静音误判导致提前停止的问题
        "--no-speech-thold", "0.2",  # 默认 0.6 太严, 长音频容易在静音段 stop
        "--max-len", "0",            # 不限制单段长度
        "--audio-ctx", "0",          # 全音频上下文
    ]
    if extra_args:
        cmd.extend(extra_args)

    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        wall_s = time.time() - t0
        if proc.returncode != 0:
            raise RuntimeError(f"whisper-cli exit={proc.returncode} stderr={proc.stderr[-500:]}")
    finally:
        # 转出来的 wav 删掉, 容器只保留原始 m4s/srt/json 让 app.py finally 删
        if actual_input != audio_path:
            try:
                os.remove(actual_input)
            except OSError:
                pass

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
