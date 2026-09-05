# 封面切换到魔搭 API Spec

## Why

当前封面用 MiniMax `image-01-live` 生成 anime 风格"金融终端"图，老板反馈"封面生成太差"，不贴题、不专业、缺乏财经媒体质感。需要换成魔搭（ModelScope）API-Inference 的文生图模型（FLUX / Qwen-Image），并按高阅读量财经封面的真实风格出图，让封面与草稿标题强相关、有媒体感。

## What Changes

- 接入魔搭 `https://api-inference.modelscope.cn/v1/images/generations`（异步任务模式），替换 MiniMax `image_generation`
- 魔搭 key 从 `.env` 的 `MoTa_API_KEY` 读取（`ms-afb56c75-...`）
- 封面 prompt 风格从"anime 金融终端"重构为"高阅读量财经媒体封面"风格（基于联网调研结论）
- 模型默认用 FLUX（真实感强、文字渲染好）；size 用 `1024x576`（16:9，公众号首图比例）
- `generate_cover_prompt` 的 system prompt 重写：要求画面**切合标题具体内容**，并落地财经媒体封面风格（深色背景 + 数据图表 + 红绿涨跌色 + 标题关键词视觉化）
- 失败降级：魔搭失败 → 回退 MiniMax（key 仍在 .env）→ 再失败用硬编码兜底 URL
- **同步修改两处**：
  - `gzh-txh-api/server.py`（NAS 主服务，yuanbao 实际调用路径）
  - `src/index.ts`（阿里云 app `/api/bilibili/summary` 端点，保持两条路径行为一致）
- 部署：server.py scp 到 NAS + 重启容器；src/index.ts 重新构建阿里云容器

## Impact

- 受影响代码：
  - `gzh-txh-api/server.py`（`minimax_cover_image` / `minimax_cover` / `generate_cover_prompt`）
  - `src/index.ts`（`generateCoverImage` / `generateCoverPrompt`）
  - `.env`（`MoTa_API_KEY` 已存在，无需新增；部署到 NAS 时需加入 `.env`）
- 受影响流程：`/api/gzh/draft`（NAS）、`/api/bilibili/summary`（阿里云）的 Step 5 封面生成
- 不影响：字幕获取、LLM 总结、HTML 结构、草稿上传逻辑

## ADDED Requirements

### Requirement: 魔搭文生图封面生成

系统 SHALL 通过魔搭 API-Inference 的 `/v1/images/generations` 端点生成公众号封面图，使用 FLUX 模型，16:9 比例。

#### Scenario: 正常生成

- **WHEN** 调用封面生成，传入草稿标题和简介
- **THEN** 系统先调 ARK LLM 生成魔搭友好的封面 prompt（财经媒体风格、切合标题）
- **AND** 用该 prompt 调魔搭 `/v1/images/generations`（异步模式，带 `X-ModelScope-Async-Mode: true`）
- **AND** 拿到 `task_id` 后轮询 `/v1/tasks/{task_id}` 直到 `SUCCEED`
- **AND** 返回 `output_images[0]` 作为封面 URL

#### Scenario: 魔搭失败降级

- **WHEN** 魔搭 API 返回非 200，或轮询超时（>120s），或 task_status 为 `FAILED`
- **THEN** 回退到 MiniMax `image-01-live`（用同一个 prompt）
- **WHEN** MiniMax 也失败
- **THEN** 抛错（不再用硬编码 COVER_IMAGE_URL，避免不贴题）

### Requirement: 财经媒体封面风格

封面 prompt SHALL 体现高阅读量财经公众号封面的视觉特征（基于联网调研）：

- 深色背景（深蓝/炭黑）+ 高对比数据可视化（K 线、汇率、利率曲线）
- 红绿涨跌色（A 股配色：红涨绿跌）
- 标题关键词视觉化（如"加息"→利率曲线飙升、"按兵不动"→暂停符号 + 静止指针）
- 16:9 构图，留出标题区域（不画文字，但构图上预留）
- 避免：anime 卡通、金色 candlestick + 上升箭头模板、城市天际线、自然风景、生活化物件

#### Scenario: 标题相关性

- **WHEN** 标题为"美联储连续五次按息"
- **THEN** prompt 包含"美联储大楼剪影 + 暂停按钮 + 利率期货曲线走平"等具体画面元素
- **NOT** 泛泛的"金融图表"模板

## MODIFIED Requirements

### Requirement: 封面生成流程（server.py + index.ts）

原流程：`ARK 生成 anime prompt → MiniMax image-01-live 出图`

改为：`ARK 生成财经媒体 prompt → 魔搭 FLUX 出图 →（失败）MiniMax 兜底`

两处实现（server.py Python + index.ts TypeScript）保持风格 prompt 和降级链一致。
