# 草稿阅读体验优化 Spec

## Why
当前生成的公众号草稿存在两个阅读体验问题：
1. 顶部声明块包含一句无关内容（"没想到啊，我才没休息几天又可以玩了。"），跟投资学习声明无关，需要删除。
2. 正文 HTML 把 3 句话挤在同一个 `<p>` 标签里，段落过长过密，缺少视觉层次；LLM 生成的加粗关键句不够多，肉眼阅读吃力。

## What Changes
- **build_draft.py** 顶部声明块 `top` 变量：删除 "没想到啊，我才没休息几天又可以玩了。<br/>" 这一行
- **build_draft.py** `_summary_to_html` 函数：每个段落（空行分隔的文本块）单独输出一个 `<p>` 标签，不再把 3 句合并到一个 `<p>`
- **build_draft.py** `_summary_to_html` 函数：段落内如果 LLM 没加粗任何内容，自动给段落首句加 `<strong>`（作为视觉钩子）
- **build_draft.py** `_summary_to_html` 函数：段落之间额外加一个空 `<p></p>` 增加垂直留白
- **gen_summary_remote.py** LLM prompt：明确要求每个要点的**首句必须加粗**（作为该要点的核心论点/结论）

## Impact
- Affected code:
  - `z:\代码\养龙虾\公众号专家\build_draft.py` — 顶部声明 + `_summary_to_html` 函数
  - `z:\代码\养龙虾\公众号专家\gen_summary_remote.py` — LLM prompt 加粗要求
- 不影响 mp_proxy、不影响字幕端点、不影响封面生成
- 旧草稿已删除，新草稿需重建（含新格式）

## ADDED Requirements

### Requirement: 顶部声明块只保留必要声明
顶部声明块（紧跟封面之下、LLM 总结之上）只保留四行内容：
1. `<strong>内容不作为投资建议，注意风险。</strong>`
2. `<strong>都是历史数据，仅作为学习。</strong>`
3. `<strong>独立学者：</strong>`
4. `---` 分隔符（前后各 1 行空行，3 行空行在声明之上）

**删除**："没想到啊，我才没休息几天又可以玩了。"

#### Scenario: 顶部声明块渲染
- **WHEN** build_draft.py 生成 HTML
- **THEN** top 变量输出为：
  ```
  <p><strong>内容不作为投资建议，注意风险。</strong><br/>
  <strong>都是历史数据，仅作为学习。</strong><br/>
  <strong>独立学者：</strong></p>
  <p></p><p></p><p></p>
  <p>---</p>
  <p></p>
  ```

### Requirement: 正文段落一了一段，每段单独成块
`_summary_to_html` 函数处理 LLM 总结文本时：
- 每个 `### 标题` 输出 `<h3>` 标签
- 每个段落（空行分隔的文本块）**单独**输出一个 `<p>` 标签，段落内所有句子保持在一起
- 段落之间**不再合并 3 句**为一个 `<p>`
- 段落之间插入一个空 `<p></p>` 增加垂直留白

#### Scenario: 段落处理
- **WHEN** 输入 LLM 总结：
  ```
  ### 标题
  
  段落1句子1。句子2。句子3。
  
  段落2句子1。句子2。
  ```
- **THEN** HTML 输出：
  ```html
  <h3>标题</h3>
  <p>段落1句子1。句子2。句子3。</p>
  <p></p>
  <p>段落2句子1。句子2。</p>
  ```

### Requirement: 自动加粗段落首句作为视觉钩子
当某个段落 LLM 没有输出 `**加粗**` 时，`_summary_to_html` 自动给段落首句（到第一个句号/问号/感叹号为止）加 `<strong>`，让肉眼扫读时能快速抓到重点。

#### Scenario: 段落已有加粗
- **WHEN** 段落是 "**这是重点**。后面是展开内容。"
- **THEN** 保持原样输出 `<p><strong>这是重点</strong>。后面是展开内容。</p>`，不额外加粗

#### Scenario: 段落无加粗
- **WHEN** 段落是 "这是一段普通的开头。后面是展开内容。再继续。"
- **THEN** 首句加粗输出 `<p><strong>这是一段普通的开头。</strong>后面是展开内容。再继续。</p>`

### Requirement: LLM prompt 强制首句加粗
`gen_summary_remote.py` 的 LLM prompt 排版规则里新增一条：每个要点的**首句必须用 `**加粗**`**，作为该要点的核心论点/结论，方便读者扫读。

#### Scenario: LLM 生成总结
- **WHEN** 调火山方舟 LLM 生成总结
- **THEN** 每个要点的 `### 标题` 下方第一段第一句必须有 `**加粗**`
