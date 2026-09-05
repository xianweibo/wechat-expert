# Checklist

- [x] build_draft.py 顶部声明 `top` 变量已删除"没想到啊，我才没休息几天又可以玩了。"
- [x] build_draft.py 顶部声明渲染后只有三行加粗声明 + `---` 分隔符，无多余内容
- [x] `_summary_to_html` 每个段落单独一个 `<p>` 标签（不再 3 句合并）
- [x] `_summary_to_html` 段落之间有空 `<p></p>` 增加留白
- [x] `_summary_to_html` 段落无 `**` 时，首句自动加 `<strong>`
- [x] `_summary_to_html` 段落已有 `**` 时，保持原样不重复加粗
- [x] `_summary_to_html` `### 标题` 仍正确转为 `<h3>`
- [x] gen_summary_remote.py prompt 要求每个要点首句必须加粗
- [x] 新生成的 summary_text.txt 每个要点首句有 `**加粗**`
- [x] 新草稿创建成功，返回 media_id=bRcX-a6nPWS8NtJrTuhJbHpfChPWx0K-zOBaiC_cHnILEdTmu09m974l_Ap1K-Lp
- [x] 上一版草稿（media_id=bRcX-...AzHe）已删除
- [x] 阿里云 /tmp 临时文件已清理
- [x] 生成的 HTML 肉眼阅读层次清晰：标题 → 加粗首句 → 展开内容，段落间有留白
