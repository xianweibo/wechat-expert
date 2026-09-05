# Tasks

- [x] Task 1: 修改 gzh_v2_server.py 的 bilibili_view，增加返回 cid 字段
  - [x] SubTask 1.1: bilibili_view 返回 dict 新增 `cid: item.get("cid")` 字段

- [x] Task 2: 新增 gzh_v2_server.py 的 bilibili_subtitle 函数
  - [x] SubTask 2.1: 新增 `bilibili_subtitle(bvid, cid)` 函数，调 mp_proxy 的 `/api/admin/bilibili-subtitle` 端点
  - [x] SubTask 2.2: 返回 subtitle_text 字符串；字幕为空时记日志并返回空字符串（不抛异常，让降级逻辑生效）

- [x] Task 3: 修改 gzh_v2_server.py 的 minimax_summary，以字幕为数据源 + 强制首句加粗
  - [x] SubTask 3.1: minimax_summary 函数签名新增 `subtitle=""` 参数
  - [x] SubTask 3.2: prompt 改为：字幕非空时以字幕为唯一数据源（title/desc 仅辅助），字幕为空时用 title+desc（旧行为）
  - [x] SubTask 3.3: prompt 排版规则新增"每个要点的首句必须用 `**加粗**`，作为核心论点/结论"

- [x] Task 4: 修改 gzh_v2_server.py 的 process_draft，插入"拿字幕"步骤
  - [x] SubTask 4.1: 在"LLM 改写标题"之后、"LLM 总结"之前，调用 bilibili_subtitle(bvid, cid) 拿字幕
  - [x] SubTask 4.2: 调 minimax_summary 时传入 subtitle 参数
  - [x] SubTask 4.3: 字幕为空时日志记录"字幕为空，降级用 title+desc"

- [x] Task 5: 修改 gzh_v2_server.py 的 build_html，删除"没想到啊" + FYI 标题改为 FYI
  - [x] SubTask 5.1: top 变量删除"没想到啊，我才没休息几天又可以玩了。"那一行
  - [x] SubTask 5.2: 三行声明加 `<strong>` 加粗
  - [x] SubTask 5.3: FYI 块标题从"参考资料"改为"FYI"

- [x] Task 6: 重写 gzh_v2_server.py 的 _summary_to_html，与 build_draft.py 对齐
  - [x] SubTask 6.1: 每个段落单独一个 `<p>`（不再 3 句合并）
  - [x] SubTask 6.2: 段落之间插入空 `<p></p>` 留白
  - [x] SubTask 6.3: 段落无 `**` 时，自动给首句加 `<strong>`
  - [x] SubTask 6.4: `**xxx**` 转 `<strong>xxx</strong>` 逻辑保留

- [ ] Task 7: 部署到阿里云并重启服务
  - [ ] SubTask 7.1: SCP gzh_v2_server.py 到阿里云 ~/apps/gzh-expert-git/
  - [ ] SubTask 7.2: 重启 gzh-expert 服务（docker compose restart 或 up -d）
  - [ ] SubTask 7.3: 验证 /health 端点返回正常

- [ ] Task 8: 端到端验证
  - [ ] SubTask 8.1: curl 调 /api/gzh/draft 传 bvid=BV1hB3k6qEv7，确认走新流程（字幕+新格式+首句加粗）
  - [ ] SubTask 8.2: 确认新草稿 HTML 顶部无"没想到啊"、段落有留白、首句加粗、FYI 标题为 FYI

# Task Dependencies
- Task 3 依赖 Task 2（minimax_summary 用 subtitle，需先有 bilibili_subtitle 函数）
- Task 4 依赖 Task 1、2、3（process_draft 调 bilibili_subtitle + minimax_summary）
- Task 7 依赖 Task 1-6 全部完成
- Task 8 依赖 Task 7
- Task 1、5、6 之间无依赖，可并行
