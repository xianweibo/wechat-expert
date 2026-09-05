# 修复 NAS 魔搭封面环境变量 Spec

## Why

yuanbao 通过腾讯云 STCP visitor → NAS 41090 → `gzh-txh-api/server.py` 调用服务。虽然 `server.py` 已含魔搭集成代码，但 NAS 的 `.env` 缺少 `MoTa_API_KEY`，导致 `modelscope_cover_image()` 抛 `RuntimeError("MOTASCOPE_API_KEY not set")`，封面回退到 MiniMax `image-01-live`（anime 卡通风格），用户反馈"封面生成太差"。

阿里云 `gzh-expert-app` 容器**已正确配置** `MoTa_API_KEY`，但 yuanbao 不走阿里云路径，所以阿里云配置无效。

## What Changes

- **在 NAS `.env` 中追加** `MoTa_API_KEY=ms-afb56c75-90a2-4585-b04f-0e77ee379fff` 和 `MOTASCOPE_MODEL=Tongyi-MAI/Z-Image-Turbo`
- **确认 NAS `server.py` 是最新版**（含 `modelscope_cover_image` 函数），如不是则 SCP 最新版
- **重新创建 NAS 容器**（`docker compose up -d --force-recreate`）让新环境变量生效
- **验证封面走魔搭**（日志显示 `[cover] modelscope ok`，封面为财经媒体风格非 anime）

## Impact

- Affected code: NAS `/vol2/1000/docker_related/gzh-txh-api/.env`、NAS `/vol2/1000/docker_related/gzh-txh-api/server.py`
- Affected flow: yuanbao → NAS 41090 → 封面生成步骤
- 不影响：阿里云 `gzh-expert-app`（已正确配置）、字幕获取、LLM 总结、HTML 结构、草稿上传

## 访问 NAS 的方式

NAS 通过 STCP 暴露到腾讯云 frps（`159.75.44.211:37000`），不直接暴露到阿里云或沙箱。需要在阿里云上启动 STCP visitor 访问 NAS SSH：

```
# STCP visitor 配置（在阿里云上运行）
serverAddr = "159.75.44.211"
serverPort = 37000
auth.token = "StockAgent_2025_Token"

[[visitors]]
name = "nas-ssh-visitor"
type = "stcp"
serverName = "gzh-txh-ssh"
secretKey = "gzh-txh-ssh-sk-2026"
localIP = "127.0.0.1"
localPort = 41022
```

阿里云上已有 `snowdreamtech/frpc:latest` 镜像（frpc-stcp-server 容器在用），可复用。

## ADDED Requirements

### Requirement: NAS 环境变量配置

NAS `gzh-txh-api` 容器 SHALL 通过 `.env` 文件配置以下环境变量：

- `MoTa_API_KEY=ms-afb56c75-90a2-4585-b04f-0e77ee379fff`（魔搭 API key）
- `MOTASCOPE_MODEL=Tongyi-MAI/Z-Image-Turbo`（魔搭模型，默认即可）

#### Scenario: 环境变量生效

- **WHEN** NAS 容器启动
- **THEN** `os.environ.get("MoTa_API_KEY")` 返回 `ms-afb56c75-...`
- **AND** `modelscope_cover_image()` 不再抛 `MOTASCOPE_API_KEY not set` 错误
- **AND** 封面生成走魔搭 FLUX/Z-Image-Turbo，不再回退 MiniMax

### Requirement: NAS server.py 版本

NAS `server.py` SHALL 包含 `modelscope_cover_image(prompt)` 函数和 `generate_cover(title, desc)` 函数（含魔搭优先 + MiniMax 回退逻辑）。

#### Scenario: 代码最新

- **WHEN** 检查 NAS 上的 `server.py`
- **THEN** 文件包含 `def modelscope_cover_image`
- **AND** 文件包含 `def generate_cover`
- **AND** `generate_cover` 先调 `modelscope_cover_image`，失败才调 `minimax_cover_image`

## MODIFIED Requirements

### Requirement: NAS 容器重启方式

原方式：`docker restart gzh-txh-api`（不重新加载 .env）

改为：`docker compose up -d --force-recreate`（重新加载 .env 环境变量）
