# gzh_v2_server 集成字幕 + 新格式 Spec

## Why
yuanbao 调用的 gzh-expert 服务入口是部署在阿里云的 `gzh_v2_server.py`，但之前所有字幕/格式优化改动只改了沙箱独立脚本 `build_draft.py` 和 `gen_summary_remote.py`，从未集成进 `gzh_v2_server.py`。导致 yuanbao call gzh-expert 时仍走老流程：只用 title+desc 生成总结（不拿字幕）、顶部声明还有"没想到啊"、段落 3 句合并无留白、FYI 标题还是"参考资料"、LLM prompt 不强制首句加粗。

## What Changes
- **gzh_v2_server.py** `bilibili_view` 函数：增加返回 `cid` 字段（mp_proxy 的 `bilibili-check-bvids` 已返回 cid，当前被丢弃了）
- **gzh_v2_server.py** 新增 `bilibili_subtitle(bvid, cid)` 函数：调 mp_proxy 的 `/api/admin/bilibili-subtitle` 端点拿字幕
- **gzh_v2_server.py** `minimax_summary` 函数：新增 `subtitle` 参数，prompt 改为**以字幕为唯一数据源**（title/desc 仅作辅助），并强制每个要点首句加粗
- **gzh_v2_server.py** `process_draft` 流程：在"LLM 总结"步骤前插入"拿字幕"步骤；字幕为空时降级用 title+desc（保证非充电视频也能跑）
- **gzh_v2_server.py** `build_html` 的 `top` 变量：删除"没想到啊，我才没休息几天又可以玩了。"那一行
- **gzh_v2_server.py** `build_html` 的 FYI 标题：从"参考资料"改为"FYI"
- **gzh_v2_server.py** `_summary_to_html` 函数：重写为每段单独 `<p>`、段落间 `<p></p>` 留白、无加粗时自动给首句加 `<strong>`（与 build_draft.py 对齐）
- 部署到阿里云并重启服务

## Impact
- Affected specs: `improve-draft-readability`（将其成果集成到服务端）
- Affected code:
  - `z:\代码\养龙虾\公众号专家\gzh_v2_server.py` — bilibili_view / minimax_summary / process_draft / build_html / _summary_to_html
  - 阿里云 `~/apps/gzh-expert-git/gzh_v2_server.py` — 部署更新
- 不影响 mp_proxy（bilibili-subtitle 端点已部署且可用）
- 不影响 build_draft.py（沙箱脚本保持独立）
- **BREAKING**：yuanbao 后续调用 gzh-expert 会自动拿字幕 + 新格式，总结质量显著提升

## ADDED Requirements

### Requirement: gzh_v2_server 拿字幕作为总结数据源
`process_draft` 在生成总结前，必须先通过 mp_proxy 的 `bilibili-subtitle` 端点拿视频字幕。字幕作为 LLM 总结的**唯一数据源**（title/desc 仅辅助上下文）。字幕为空时降级用 title+desc（保证非充电视频或无字幕视频也能跑）。

#### Scenario: 充电视频有字幕
- **WHEN** yuanbao 调 `/api/gzh/draft` 传 bvid=BV1hB3k6qEv7
- **THEN** process_draft 先调 bilibili_view 拿 title/desc/cid，再调 bilibili-subtitle 拿字幕，用字幕调 LLM 生成总结

#### Scenario: 普通视频无字幕（降级）
- **WHEN** 字幕端点返回 subtitle_text 为空
- **THEN** 用 title+desc 调 LLM 生成总结（与旧行为一致），日志记录 "字幕为空，降级用 title+desc"

### Requirement: bilibili_view 返回 cid
`bilibili_view` 函数返回的 dict 必须包含 `cid` 字段（从 mp_proxy 的 `bilibili-check-bvids` 响应里取 `cid`）。

#### Scenario: view 返回 cid
- **WHEN** 调 bilibili_view("BV1hB3k6qEv7")
- **THEN** 返回 dict 包含 `cid: 40392132706`

### Requirement: 顶部声明块删除"没想到啊"
`build_html` 的 `top` 变量删除"没想到啊，我才没休息几天又可以玩了。"那一行，只保留三行加粗声明 + `---` 分隔符。三行声明用 `<strong>` 加粗。

#### Scenario: top 渲染
- **WHEN** build_html 生成 HTML
- **THEN** top 输出：
  ```
  <p><strong>内容不作为投资建议，注意风险。</strong><br/>
  <strong>都是历史数据，仅作为学习。</strong><br/>
  <strong>独立学者：</strong></p>
  <p></p><p></p><p></p>
  <p>---</p>
  <p></p>
  ```

### Requirement: FYI 标题改为 FYI
`build_html` 的 FYI 块标题从"参考资料"改为"FYI"。

#### Scenario: FYI 渲染
- **WHEN** desc 含 https 链接
- **THEN** FYI 块标题为 `<p><strong>FYI</strong></p>`

### Requirement: _summary_to_html 段落单独成块 + 首句自动加粗
`_summary_to_html` 重写为：
- 每个段落（空行分隔的文本块）单独输出一个 `<p>`
- 段落之间插入空 `<p></p>` 增加留白
- `**xxx**` → `<strong>xxx</strong>`
- 段落没有 `**` 时，自动给首句（到第一个 。！？? 为止）加 `<strong>`
- `### 标题` → `<h3>`

#### Scenario: 段落无加粗
- **WHEN** 段落是 "这是一段普通的开头。后面是展开内容。"
- **THEN** 输出 `<p><strong>这是一段普通的开头。</strong>后面是展开内容。</p>`

#### Scenario: 段落已有加粗
- **WHEN** 段落是 "**这是重点**。后面是展开内容。"
- **THEN** 输出 `<p><strong>这是重点</strong>。后面是展开内容。</p>`，不重复加粗

### Requirement: LLM prompt 强制首句加粗 + 字幕作数据源
`minimax_summary` 的 prompt 必须包含两条规则：
1. 总结完全基于字幕内容，不用外部论据来源
2. 每个要点的首句必须用 `**加粗**`，作为核心论点/结论

## MODIFIED Requirements

### Requirement: process_draft 主流程
原 5 步流程改为 6 步：
1. B 站元数据（含 cid）
2. LLM 改写标题
3. **拿字幕**（新增）
4. LLM 总结（用字幕作数据源，字幕为空降级用 title+desc）
5. 封面
6. FYI + HTML + 上传封面 + 建草稿 + 删旧草稿
