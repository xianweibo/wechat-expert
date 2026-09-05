# 验收清单

- [ ] server.py bilibili_view 返回 cid
- [ ] server.py 有 bilibili_subtitle 函数
- [ ] server.py minimax_summary 用火山方舟 ARK API（非 MiniMax anthropic）
- [ ] server.py minimax_summary 支持字幕参数，字幕非空时以字幕为数据源
- [ ] server.py prompt 含首句加粗要求
- [ ] server.py 有 rewrite_title 函数
- [ ] server.py minimax_cover 用 LLM 生成 prompt（非硬编码生活化）
- [ ] server.py 有 _summary_to_html 函数（### → h3、留白、首句加粗）
- [ ] server.py build_html 顶部声明加粗
- [ ] server.py build_html 无"没想到啊"
- [ ] server.py build_html FYI 标题为 FYI
- [ ] server.py process_draft 调 bilibili_subtitle
- [ ] NAS /health 返回正常
- [ ] curl /api/gzh/draft 传 bvid 返回 success
- [ ] 草稿 HTML 无"没想到啊"、声明加粗、段落留白、首句加粗、FYI
