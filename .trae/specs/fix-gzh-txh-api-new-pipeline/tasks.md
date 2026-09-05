# Tasks

- [ ] Task 1: 改 gzh-txh-api/server.py 走新流程
  - [ ] 1.1 bilibili_view 返回增加 cid
  - [ ] 1.2 新增 bilibili_subtitle(bvid, cid)
  - [ ] 1.3 minimax_summary 改用火山方舟 ARK API + 字幕数据源 + 首句加粗
  - [ ] 1.4 新增 rewrite_title
  - [ ] 1.5 minimax_cover 改为 LLM 生成 prompt + 金融终端质感
  - [ ] 1.6 新增 _summary_to_html
  - [ ] 1.7 build_html 顶部加粗 + 删"没想到啊" + FYI + 段落留白 + 首句加粗
  - [ ] 1.8 process_draft 插入拿字幕步骤
  - [ ] 1.9 新增环境变量 ARK_API_KEY/ARK_BASE_URL/ARK_MODEL/STYLE_PATH

- [ ] Task 2: 部署到 NAS
  - [ ] 2.1 SCP server.py 到 NAS /vol2/1000/docker_related/gzh-txh-api/
  - [ ] 2.2 重启 docker 容器
  - [ ] 2.3 验证 /health

- [ ] Task 3: 端到端验证
  - [ ] 3.1 curl 调 /api/gzh/draft 传 bvid，确认走新流程
  - [ ] 3.2 查草稿 HTML：无"没想到啊"、加粗、留白、FYI

# Dependencies
- Task 2 依赖 Task 1
- Task 3 依赖 Task 2
