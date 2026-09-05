# 修复 yuanbao 调用链路走新流程 Spec

## Why

yuanbao 调用的是阿里云 Node.js 服务的 `/api/bilibili/summary` 端点（`src/index.ts`），但这个端点走的是**最原始的旧流程**：yuanbao 自己生成 summary 传进来，服务只负责建草稿（用硬编码封面 + 极简 HTML）。

之前在 `gzh_v2_server.py`（Python）里做的所有新流程改动（字幕作数据源、LLM 首句加粗、project_rules 草稿结构、MiniMax 封面、删"没想到啊"）**完全不在这条链路上**，所以 yuanbao 调过去依然走旧流程。

真正要修的是 `src/index.ts` 的 `/api/bilibili/summary` 端点本身。

## What Changes

- **重写** `src/index.ts` 的 `POST /api/bilibili/summary` 端点：
  - **新流程（body 带 `bvid`）**：服务端调 mp_proxy 拿视频元数据（含 cid）→ 拿字幕 → 调火山方舟 LLM 生成总结（首句加粗）→ 调 MiniMax 生成封面 → 调 mp_proxy 上传封面 + 建草稿 → 按 `project_rules.md` 第 4 节构造 HTML
  - **降级（body 只有 `title`/`summary`，无 `bvid`）**：保留兼容，但用新 HTML 结构（顶部声明块 + FYI + 底部声明块）包裹传入的 summary，不再输出"由 AI 生成"声明
- **新增** `src/index.ts` 内辅助函数（不新建文件，集中在一个区块）：
  - `fetchBilibiliMeta(bvid)` — 调 `mp_proxy` 的 `/api/admin/bilibili-check-bvids`
  - `fetchBilibiliSubtitle(bvid, cid)` — 调 `mp_proxy` 的 `/api/admin/bilibili-subtitle`
  - `arkChat(prompt)` — 调火山方舟 OpenAI 兼容 chat
  - `generateSummary(title, desc, subtitle)` — 构造 prompt + 调 arkChat，返回总结文本（复刻 `gzh_v2_server.py` 的 `minimax_summary` prompt）
  - `rewriteTitle(title, desc)` — 标题改写
  - `generateCoverPrompt(title, desc)` — LLM 生成封面 prompt
  - `generateCoverImage(prompt)` — 调 MiniMax image-01-live
  - `extractFyi(desc)` — 从 desc 提取参考链接
  - `summaryToHtml(summary)` — `### 标题` → `<h3>`、段落留白、`**xx**` → `<strong>`、无加粗时首句自动加粗（移植 `gzh_v2_server.py` 的 `_summary_to_html`）
  - `buildHtml(summary, fyiLinks, title)` — 按 `project_rules.md` 第 4 节构造完整 HTML（顶部声明块 + 正文 + FYI + 底部声明块）
  - `uploadCover(coverUrl)` — 调 `mp_proxy` 的 `/api/admin/mp-material-image-add`
  - `createDraft(title, html, thumbMediaId, author)` — 调 `mp_proxy` 的 `/api/admin/mp-draft-add`
- **新增** 环境变量（写入阿里云 `.env`，`docker-compose.yml` 已通过 `env_file` 自动加载）：
  - `ARK_BASE_URL`、`ARK_API_KEY`、`ARK_MODEL`
  - `MINIMAX_API_KEY`、`MINIMAX_IMAGE_MODEL`（image-01-live）
  - `GZH_WORKER_SECRET`（mp_proxy 的 `X-Worker-Secret`，值 `（已脱敏：值只存服务器 .env，勿提交到 Git）`）
  - `DEFAULT_AUTHOR`（`小喇叭大只讲`）
  - `STYLE_PATH`（指向 `style_summary.txt` 绝对路径）
- **删除** `src/index.ts` 里旧的 `generateArticleContent` 函数（含"由 AI 生成"声明，违反 `project_rules.md`）
- **删除** `src/index.ts` 里旧的 `uploadCoverImage`（硬编码 COVER_IMAGE_URL）和直接调微信 API 的 `getAccessToken`/`createDraft`（改走 mp_proxy 统一出口）
- **保留** `/api/health`、`/api/info` 端点不动
- **不动** `src/mp_proxy.ts`（已有端点足够复用）
- **不动** `gzh_v2_server.py`（作为本地独立工具保留，不在本 spec 范围）

## Impact

- **Affected specs**: `integrate-subtitle-into-gzh-server`（方向调整为 Node.js，Task 7-8 标记为不再适用；Task 1-6 的 Python 逻辑作为 prompt/HTML 移植参考保留）
- **Affected code**:
  - `src/index.ts`（主要改动文件）
  - 阿里云 `~/apps/gzh-expert-git/.env`（新增环境变量）
  - 阿里云 `~/apps/gzh-expert-git/style_summary.txt`（确认存在，供 LLM 风格档案读取）
- **yuanbao 侧影响**: yuanbao 调用参数从 `{title, summary, source}` 改为 `{bvid}`（推荐）；降级模式仍兼容旧参数
- **部署**: 改完 `src/index.ts` 后，SCP 到阿里云 `~/apps/gzh-expert-git/src/`，`docker compose up -d --build` 重建容器

## ADDED Requirements

### Requirement: 新流程端点（bvid 驱动）

`POST /api/bilibili/summary` 当 body 包含 `bvid` 时，系统 SHALL 在服务端完整执行新流程：

#### Scenario: yuanbao 传 bvid 走完整新流程
- **WHEN** 客户端 POST `/api/bilibili/summary`，body 含 `{ "bvid": "BV1hB3k6qEv7" }`，header 带 `X-Worker-Secret`
- **THEN** 服务端依次执行：
  1. 调 mp_proxy `bilibili-check-bvids` 拿 title/desc/cid
  2. 调 mp_proxy `bilibili-subtitle` 拿字幕（空则降级用 title+desc）
  3. 调火山方舟 LLM 生成总结（字幕为数据源，首句加粗，6-8 要点，1500-2000 字）
  4. 调火山方舟 LLM 改写标题
  5. 调火山方舟 LLM 生成封面 prompt
  6. 调 MiniMax image-01-live 生成封面图 URL
  7. 调 mp_proxy `mp-material-image-add` 上传封面拿 thumb_media_id
  8. 按 `project_rules.md` 第 4 节构造 HTML（顶部声明块加粗 + 正文留白首句加粗 + FYI + 底部声明块）
  9. 调 mp_proxy `mp-draft-add` 建草稿
- **AND** 返回 `{ "success": true, "media_id": "<草稿 media_id>" }`

#### Scenario: 字幕为空降级
- **WHEN** bvid 对应视频无字幕（或充电专属未充电）
- **THEN** 日志记录"字幕为空，降级用 title+desc"，LLM prompt 切换到降级模式（5-7 要点，1000-1500 字），其余流程不变

### Requirement: 降级兼容旧调用

`POST /api/bilibili/summary` 当 body 不含 `bvid` 但含 `title`/`summary` 时，系统 SHALL 用新 HTML 结构包裹传入的 summary：

#### Scenario: 旧调用兼容
- **WHEN** 客户端 POST body 含 `{ "title": "...", "summary": "..." }`，无 `bvid`
- **THEN** 服务端用 `summaryToHtml` 转换 summary，套上顶部/底部声明块，用固定/默认封面建草稿
- **AND** 不输出"由 AI 生成"声明（违反 `project_rules.md`）

## MODIFIED Requirements

### Requirement: 草稿 HTML 结构

`generateArticleContent` 函数 SHALL 被替换为 `buildHtml`，严格按 `project_rules.md` 第 4 节构造：

- 顶部声明块：3 行加粗声明 + 3 行空行 + `---` + 1 行空行（**删除**"没想到啊，我才没休息几天又可以玩了。"）
- 正文：`### 标题` → `<h3>`，段落间 `<p></p>` 留白，`**xx**` → `<strong>`，无加粗时首句自动 `<strong>`
- FYI 列表：标题为 `FYI`（非"参考资料"），`<标题> — <URL>` 格式
- 底部声明块：`Make you greate again！` + 量化回测声明 + PS 声明
- 作者字段：`小喇叭大只讲`
- **不包含** BVID、UP 主名、发布日期、"由 AI 生成"等声明

## REMOVED Requirements

### Requirement: 旧的 generateArticleContent + 硬编码封面

**Reason**: 输出 `<h2>📝 内容精华</h2>` + 一行"本内容由 AI 根据视频字幕自动生成"，违反 `project_rules.md`（不要写"由 AI 生成"）；封面用硬编码 `COVER_IMAGE_URL`，不符合 MiniMax 生成要求。

**Migration**: 替换为 `buildHtml`（新 HTML 结构）+ MiniMax 生成封面。旧的 `getAccessToken`/`uploadCoverImage`/`createDraft` 直接调微信 API 的逻辑也移除，统一走 mp_proxy 出口（mp_proxy 已封装微信 token 刷新和素材上传）。
