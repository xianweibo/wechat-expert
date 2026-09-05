# 改进封面 prompt 贴题度 Spec

## Why

当前封面 prompt 生成逻辑（`generate_cover_prompt`）只给 LLM 一个泛泛的"切合标题具体主题"指令，没有强制要求 LLM 拆解标题的所有核心概念并逐一视觉化。实际生成的 prompt 往往只捕捉标题最显眼的一个词（如"按兵不动"→frozen pause），忽略了其他 equally important 的概念（如"两难困境"、"市场观望情绪上升"），导致封面与草稿标题的概念覆盖不全，用户反馈"不贴切该期草稿的概念"。

## What Changes

- **重写 `generate_cover_prompt` 的 system prompt**：要求 LLM 先拆解标题的所有核心概念，再为每个概念设计对应视觉元素，最后组合成完整画面
- **增加"概念覆盖检查"**：prompt 必须显式列出标题中的每个核心概念及其视觉化方式
- **去掉日志截断**：`log.info("[cover] prompt: %s", prompt[:200])` 改为完整打印，便于审计
- **同步修改** `gzh-txh-api/server.py` 和 `src/index.ts`（保持两处一致）

## Impact

- Affected code: `gzh-txh-api/server.py`（`generate_cover_prompt` 函数 + 日志行）、`src/index.ts`（`generateCoverPrompt` 函数 + 日志行）
- Affected flow: 封面生成步骤（Step 5）
- 不影响：字幕获取、LLM 总结、HTML 结构、草稿上传、魔搭/MiniMax 调用逻辑

## ADDED Requirements

### Requirement: 封面 prompt 覆盖标题所有核心概念

封面 prompt SHALL 视觉化标题中的**所有**核心概念，而不是只捕捉最显眼的一个词。

#### Scenario: 多概念标题

- **WHEN** 标题为"美联储连续五次按兵不动，暂停降息背后的两难困境，为何引发市场观望情绪上升？"
- **THEN** prompt 必须包含以下视觉元素：
  - "按兵不动/暂停降息" → frozen pause icon / flatlined interest rate gauge
  - "两难困境" → split visual / dual-pull arrows / dilemma composition
  - "市场观望情绪" → wait-and-see gauge / market sentiment indicator
- **AND** prompt 开头用一句话列出标题的所有核心概念（便于审计）

### Requirement: 完整日志打印

封面 prompt 生成后 SHALL 完整打印到日志（不截断），便于审计概念覆盖情况。

#### Scenario: 日志可审计

- **WHEN** 封面 prompt 生成完成
- **THEN** 日志输出完整的 prompt 内容（不是前 200 字符）
- **AND** 日志含标题原文（便于对照 prompt 是否覆盖所有概念）

## MODIFIED Requirements

### Requirement: generate_cover_prompt 的 system prompt

原 system prompt：
```
- 为一个**具体画面**写 100-150 词英文 prompt，必须切合标题的具体主题（不是泛泛模板）
- 标题关键词视觉化：把标题核心概念转成具体视觉元素
  例：'加息' → upward-spiraling yield curve...
```

改为（强制概念拆解 + 逐个视觉化）：
```
- 先拆解标题中的所有核心概念（通常 2-4 个），在 prompt 开头用 "Concepts:" 列出
- 为每个核心概念设计对应的视觉元素，组合成一个连贯的画面
- prompt 100-200 词，必须覆盖所有概念，不能只画最显眼的一个
- 画面构图：多个视觉元素分层组合（前景/中景/背景），不是孤立罗列
- 例：标题"美联储按兵不动引发市场观望" →
  Concepts: Fed pause (frozen pause icon), market wait-and-see (sideways gauge)
  画面：前景 frozen pause icon overlaying flatlined Fed funds rate，背景 sideways market sentiment gauge with hesitation arrows
```
