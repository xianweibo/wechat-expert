# Tasks

- [x] Task 1: 在 src/index.ts 新增风格档案加载 + 环境变量读取
  - [x] SubTask 1.1: 顶部新增环境变量读取：ARK_BASE_URL / ARK_API_KEY / ARK_MODEL / MINIMAX_API_KEY / MINIMAX_IMAGE_MODEL / GZH_WORKER_SECRET / DEFAULT_AUTHOR / STYLE_PATH
  - [x] SubTask 1.2: 新增 `loadStyleSummary()` 函数，读 STYLE_PATH 指向的 style_summary.txt（启动时加载一次）
  - [x] SubTask 1.3: 新增鉴权校验：`X-Worker-Secret` header 对比 GZH_WORKER_SECRET（替换旧的 BILIBILI_WORKER_SECRET）

- [x] Task 2: 在 src/index.ts 新增 mp_proxy 调用辅助函数
  - [x] SubTask 2.1: `mpProxy(endpoint, payload)` — POST 到 `http://localhost:${PORT}/api/admin/${endpoint}`，带 `X-Worker-Secret` header
  - [x] SubTask 2.2: `fetchBilibiliMeta(bvid)` — 调 `bilibili-check-bvids`，返回 `{ title, desc, cid, pubdate }`
  - [x] SubTask 2.3: `fetchBilibiliSubtitle(bvid, cid)` — 调 `bilibili-subtitle`，返回 subtitle_text（空则返回空字符串，不抛异常）
  - [x] SubTask 2.4: `uploadCover(coverUrl)` — 调 `mp-material-image-add`，返回 thumb_media_id
  - [x] SubTask 2.5: `createDraft(title, html, thumbMediaId, author)` — 调 `mp-draft-add`，返回 media_id

- [x] Task 3: 在 src/index.ts 新增 LLM + 封面辅助函数
  - [x] SubTask 3.1: `arkChat(prompt, maxTokens, timeout)` — fetch 火山方舟 OpenAI 兼容 chat
  - [x] SubTask 3.2: `generateSummary(title, desc, subtitle)` — 构造 prompt（字幕为数据源 + 首句加粗），调 arkChat；复刻 gzh_v2_server.py 的 minimax_summary prompt
  - [x] SubTask 3.3: `rewriteTitle(title, desc)` — 标题改写，调 arkChat
  - [x] SubTask 3.4: `generateCoverPrompt(title, desc)` — LLM 生成封面 prompt
  - [x] SubTask 3.5: `generateCoverImage(prompt)` — 调 MiniMax image-01-live，返回图片 URL

- [x] Task 4: 在 src/index.ts 新增 HTML 构造函数（移植自 gzh_v2_server.py）
  - [x] SubTask 4.1: `extractFyi(desc)` — 正则提取参考链接
  - [x] SubTask 4.2: `summaryToHtml(summary)` — `### 标题`→`<h3>`、段落留白、`**xx**`→`<strong>`、无加粗时首句自动加粗
  - [x] SubTask 4.3: `buildHtml(summary, fyiLinks, title)` — 按 project_rules.md 第 4 节构造完整 HTML（顶部声明加粗 + 正文 + FYI + 底部声明）；**不含**"没想到啊"
  - [x] SubTask 4.4: 删除旧的 `generateArticleContent` 函数

- [x] Task 5: 重写 src/index.ts 的 POST /api/bilibili/summary 端点
  - [x] SubTask 5.1: 鉴权改用 GZH_WORKER_SECRET
  - [x] SubTask 5.2: body 含 bvid 时走新流程：fetchBilibiliMeta → fetchBilibiliSubtitle → generateSummary → rewriteTitle → generateCoverPrompt → generateCoverImage → uploadCover → buildHtml → createDraft
  - [x] SubTask 5.3: body 无 bvid 但有 title/summary 时走降级：summaryToHtml + buildHtml 包裹，用默认/固定封面建草稿
  - [x] SubTask 5.4: 删除旧的 getAccessToken / uploadCoverImage / createDraft / DraftParams 接口（直接调微信 API 的逻辑）

- [x] Task 6: 阿里云 .env 新增环境变量
  - [x] SubTask 6.1: SSH 确认 ~/apps/gzh-expert-git/style_summary.txt 存在
  - [x] SubTask 6.2: 在 ~/apps/gzh-expert-git/.env 新增 ARK_BASE_URL / ARK_API_KEY / ARK_MODEL / MINIMAX_API_KEY / MINIMAX_IMAGE_MODEL / GZH_WORKER_SECRET / DEFAULT_AUTHOR / STYLE_PATH
  - [x] SubTask 6.3: 确认 ARK_API_KEY 和 MINIMAX_API_KEY 有效（从本地 build_draft.py / gzh_v2_server.py 已知值）

- [x] Task 7: 部署到阿里云并重建容器
  - [x] SubTask 7.1: SCP src/index.ts 到 ~/apps/gzh-expert-git/src/
  - [x] SubTask 7.2: 在 ~/apps/gzh-expert-git/ 执行 docker compose up -d --build
  - [x] SubTask 7.3: 验证 /api/health 返回 { status: "ok" }

- [x] Task 8: 端到端验证
  - [x] SubTask 8.1: curl 调 /api/bilibili/summary 传 { bvid: "BV1hB3k6qEv7" } + X-Worker-Secret，确认返回 success + media_id
  - [x] SubTask 8.2: 进公众号后台查草稿 HTML：顶部无"没想到啊"、声明加粗、段落留白、首句加粗、FYI 标题为 FYI、底部有 Make you greate again、无"由 AI 生成"

# Task Dependencies
- Task 3 依赖 Task 1（ARK_API_KEY 等环境变量）
- Task 5 依赖 Task 2、3、4（调用各辅助函数）
- Task 6 依赖 Task 1-5 完成（代码改完才部署）
- Task 7 依赖 Task 6（.env 先就位）
- Task 8 依赖 Task 7
- Task 1、2、3、4 之间无强依赖，可并行
