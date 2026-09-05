# 验收清单

## 代码实现检查

- [x] src/index.ts 顶部已读取所有新增环境变量（ARK_BASE_URL / ARK_API_KEY / ARK_MODEL / MINIMAX_API_KEY / MINIMAX_IMAGE_MODEL / GZH_WORKER_SECRET / DEFAULT_AUTHOR / STYLE_PATH）
- [x] loadStyleSummary() 函数存在，且启动时加载 style_summary.txt
- [x] 鉴权改用 GZH_WORKER_SECRET（不再用 BILIBILI_WORKER_SECRET）
- [x] mpProxy(endpoint, payload) 辅助函数存在，POST 到 localhost 的 /api/admin/ 端点
- [x] fetchBilibiliMeta(bvid) 调 bilibili-check-bvids，返回含 cid
- [x] fetchBilibiliSubtitle(bvid, cid) 调 bilibili-subtitle，字幕为空时返回空字符串（不抛异常）
- [x] arkChat(prompt) 调火山方舟 OpenAI 兼容 chat
- [x] generateSummary(title, desc, subtitle) 的 prompt 与 gzh_v2_server.py 的 minimax_summary 一致（字幕为数据源 + 首句加粗 + 6-8 要点 + 1500-2000 字）
- [x] rewriteTitle(title, desc) 标题改写函数存在
- [x] generateCoverPrompt(title, desc) LLM 生成封面 prompt 函数存在
- [x] generateCoverImage(prompt) 调 MiniMax image-01-live 函数存在
- [x] extractFyi(desc) 正则提取链接函数存在
- [x] summaryToHtml(summary) 实现：### → h3、段落留白、**xx** → strong、无加粗时首句自动加粗
- [x] buildHtml(summary, fyiLinks, title) 按 project_rules.md 第 4 节构造完整 HTML
- [x] buildHtml 顶部声明块**不含**"没想到啊，我才没休息几天又可以玩了。"
- [x] buildHtml 顶部三行声明已用 `<strong>` 加粗
- [x] buildHtml FYI 标题为 "FYI"（非"参考资料"）
- [x] buildHtml 底部声明块含 "Make you greate again！"
- [x] buildHtml **不含**"由 AI 生成" / "由 minimax-M3 生成" 等声明
- [x] 作者字段为 DEFAULT_AUTHOR（小喇叭大只讲）
- [x] 旧的 generateArticleContent 函数已删除
- [x] 旧的 getAccessToken / uploadCoverImage / createDraft / DraftParams 已删除（改走 mp_proxy）
- [x] 旧的 COVER_IMAGE_URL 硬编码已删除

## 端点行为检查

- [x] POST /api/bilibili/summary body 含 bvid 时走完整新流程（meta→subtitle→LLM→cover→draft）
- [x] POST /api/bilibili/summary body 无 bvid 但有 title/summary 时走降级（新 HTML 包裹）
- [x] 无 X-Worker-Secret 或 secret 错误时返回 401
- [x] 字幕为空时不抛异常，降级用 title+desc

## 部署检查

- [x] 阿里云 ~/apps/gzh-expert-git/.env 已新增所有环境变量
- [x] 阿里云 ~/apps/gzh-expert-git/style_summary.txt 存在且非空
- [x] src/index.ts 已 SCP 到阿里云 ~/apps/gzh-expert-git/src/
- [x] docker compose up -d --build 成功，容器启动无报错
- [x] /api/health 返回 { status: "ok" }

## 端到端验证

- [x] curl POST /api/bilibili/summary 传 { bvid: "BV1hB3k6qEv7" } + 正确 X-Worker-Secret，返回 { success: true, media_id: "..." }
- [x] 公众号后台查草稿：顶部无"没想到啊"
- [x] 公众号后台查草稿：三行声明已加粗
- [x] 公众号后台查草稿：正文段落间有留白
- [x] 公众号后台查草稿：要点首句已加粗
- [x] 公众号后台查草稿：FYI 标题为 "FYI"
- [x] 公众号后台查草稿：底部含 "Make you greate again！"
- [x] 公众号后台查草稿：无"由 AI 生成"字样
- [x] 公众号后台查草稿：作者为"小喇叭大只讲"
