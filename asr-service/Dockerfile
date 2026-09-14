# NAS 字幕兜底 ASR 服务
# whisper-cli + ggml-small 模型 + Flask 都从挂载卷(/opt/whisper, /opt/models)来
# 镜像只装运行时: ffmpeg(转码) + python(web 服务) + flask
# 不消耗项目 token, 完全本地推理

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir flask==3.0.3 gunicorn==23.0.0

WORKDIR /app
COPY app.py /app/app.py
COPY transcribe.py /app/transcribe.py

# 临时音频目录（容器内，调用完立即删除）
RUN mkdir -p /tmp/asr && chmod 777 /tmp/asr

ENV MODEL_PATH=/opt/models/ggml-small.bin
ENV WHISPER_BIN=/opt/whisper/whisper-cli
ENV PORT=41092
ENV LANG=zh

EXPOSE 41092

CMD ["gunicorn", "-b", "0.0.0.0:41092", "-w", "1", "--timeout", "1500", "--access-logfile", "-", "app:app"]
