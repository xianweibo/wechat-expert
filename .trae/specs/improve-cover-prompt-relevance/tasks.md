# Tasks

- [ ] Task 1: 重写 `gzh-txh-api/server.py` 的 `generate_cover_prompt`
  - [ ] 1.1 改 system prompt：强制 LLM 先拆解标题所有核心概念（Concepts: 列出），再逐个视觉化组合成画面
  - [ ] 1.2 改 prompt 长度要求：100-200 词（从 100-150 词增加，给多概念留空间）
  - [ ] 1.3 改日志行：`log.info("[cover] prompt: %s", prompt[:200])` → `log.info("[cover] prompt: %s", prompt)`（完整打印）
  - [ ] 1.4 改兜底 prompt：加多概念视觉化示例（不只是单一 candlestick chart）

- [ ] Task 2: 同步修改 `src/index.ts` 的 `generateCoverPrompt`（保持与 server.py 一致）
  - [ ] 2.1 改 system prompt（与 server.py 文本一致）
  - [ ] 2.2 改日志行：`console.log(...prompt.substring(0, 80))` → 完整打印
  - [ ] 2.3 改兜底 prompt（与 server.py 一致）

- [ ] Task 3: 部署到 NAS
  - [ ] 3.1 SCP server.py 到 NAS（通过阿里云 STCP visitor）
  - [ ] 3.2 `docker compose up -d --force-recreate` 重建容器
  - [ ] 3.3 验证 /health 返回正常

- [ ] Task 4: 端到端验证
  - [ ] 4.1 用测试 BVID 调 NAS 41090，检查日志中的完整 prompt
  - [ ] 4.2 确认 prompt 含 "Concepts:" 行，列出标题所有核心概念
  - [ ] 4.3 确认 prompt 视觉化了每个概念（不只是最显眼的一个）
  - [ ] 4.4 检查生成的封面图是否比之前更贴题

# Task Dependencies

- Task 2 与 Task 1 并行（两处代码同步修改）
- Task 3 依赖 Task 1
- Task 4 依赖 Task 3
