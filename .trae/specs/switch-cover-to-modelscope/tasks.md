# Tasks

- [x] Task 1: 调研并沉淀财经封面风格 prompt 模板
  - [x] SubTask 1.1: 整理联网调研结论（高阅读量财经封面共性：深色+数据图+红绿涨跌+标题视觉化）
  - [x] SubTask 1.2: 写出新的 `generate_cover_prompt` system prompt（中文标题→魔搭 FLUX 友好的英文 prompt，100-150 词，含具体画面指令）

- [x] Task 2: 修改 `gzh-txh-api/server.py` 接入魔搭
  - [x] SubTask 2.1: 加环境变量 `MOTASCOPE_API_KEY`（读 `MoTa_API_KEY`）和 `MOTASCOPE_MODEL`（默认 FLUX）
  - [x] SubTask 2.2: 新增 `modelscope_cover_image(prompt)` 函数：POST `/v1/images/generations` 异步模式 → 轮询 `/v1/tasks/{task_id}` → 返回 `output_images[0]`
  - [x] SubTask 2.3: 重写 `generate_cover_prompt` system prompt 为财经媒体风格
  - [x] SubTask 2.4: 改 `minimax_cover` → `generate_cover`：先魔搭，失败回退 MiniMax
  - [x] SubTask 2.5: 更新日志输出（`[5/8] modelscope cover (model=FLUX)...`）

- [x] Task 3: 修改 `src/index.ts` 接入魔搭（保持与 server.py 一致）
  - [x] SubTask 3.1: 加环境变量 `MOTASCOPE_API_KEY` / `MOTASCOPE_MODEL`
  - [x] SubTask 3.2: 新增 `generateCoverImageModelScope(prompt)` 函数（异步轮询）
  - [x] SubTask 3.3: 重写 `generateCoverPrompt` system prompt 为财经媒体风格
  - [x] SubTask 3.4: 改 `generateCoverImage` 调用链：先魔搭，失败回退 MiniMax

- [x] Task 4: 部署到 NAS
  - [x] SubTask 4.1: scp `server.py` 到 `paulproject@192.168.9.3:/vol2/1000/docker_related/gzh-txh-api/`
  - [x] SubTask 4.2: 在 NAS `.env` 加 `MoTa_API_KEY=ms-afb56c75-90a2-4585-b04f-0e77ee379fff`
  - [x] SubTask 4.3: `docker restart gzh-txh-api`，验证 `/health` 返回正常

- [x] Task 5: 部署到阿里云
  - [x] SubTask 5.1: scp `src/index.ts` 到阿里云 app 目录
  - [x] SubTask 5.2: 在阿里云容器环境变量加 `MoTa_API_KEY`
  - [x] SubTask 5.3: 重新构建并启动 `gzh-expert-app` 容器，验证 `/api/health`

- [x] Task 6: 端到端验证
  - [x] SubTask 6.1: 用真实 BVID 调 NAS `/api/gzh/draft`，确认封面走魔搭
  - [x] SubTask 6.2: 检查生成的封面是否贴题（标题相关性）
  - [x] SubTask 6.3: 模拟魔搭失败（临时改错 key），确认回退 MiniMax 成功

# Task Dependencies

- Task 2、Task 3 依赖 Task 1（共用 prompt 模板）
- Task 4、Task 5 依赖 Task 2、Task 3
- Task 6 依赖 Task 4、Task 5
