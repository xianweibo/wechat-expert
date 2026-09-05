# Tasks

- [x] Task 1: 修改 build_draft.py 顶部声明块，删除"没想到啊"那一句
  - [x] SubTask 1.1: 修改 `top` 变量，去掉 `<br/>` 后的"没想到啊，我才没休息几天又可以玩了。"这一行
  - [x] SubTask 1.2: 确认 `独立学者：<br/>` 后直接接 `</p>`，不留空的 `<br/>`

- [x] Task 2: 重写 build_draft.py 的 `_summary_to_html` 函数
  - [x] SubTask 2.1: 每个段落（空行分隔的文本块）单独输出一个 `<p>`，不再按 3 句合并
  - [x] SubTask 2.2: 段落之间插入一个空 `<p></p>` 作为垂直留白
  - [x] SubTask 2.3: 段落内没有 `**加粗**` 时，自动给首句加 `<strong>`（首句 = 到第一个 。！？? 为止）
  - [x] SubTask 2.4: `**xxx**` 转 `<strong>xxx</strong>` 的逻辑保留

- [x] Task 3: 修改 gen_summary_remote.py 的 LLM prompt，强制首句加粗
  - [x] SubTask 3.1: 在 prompt 排版规则里新增"每个要点的首句必须用 `**加粗**`，作为该要点的核心论点/结论"

- [x] Task 4: 重新生成总结 + 重建草稿
  - [x] SubTask 4.1: SCP gen_summary_remote.py 到阿里云，重新跑 LLM 生成新 summary_text.txt
  - [x] SubTask 4.2: SCP build_draft.py 和新 summary_text.txt 到阿里云，跑 build_draft.py 建新草稿
  - [x] SubTask 4.3: 删除上一版草稿 media_id=bRcX-a6nPWS8NtJrTuhJbM4zi8rNtt6oP4NvqsUVpFAVujH-keiM3ktBWdaZAzHe
  - [x] SubTask 4.4: 清理阿里云 /tmp 临时文件

# Task Dependencies
- Task 4 依赖 Task 1、2、3 全部完成
- Task 1、2、3 之间无依赖，可并行修改（都在本地文件）
