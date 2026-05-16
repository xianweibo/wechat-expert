---
name: workflow-runner
description: 在 AI 工具内运行多角色 YAML 工作流编排
---

# 工作流执行器

直接在当前会话中执行 YAML 工作流，无需配置 API key。

## 执行流程（5 步）
1. **解析工作流** — 读取 YAML 文件，提取 steps/inputs/agents_dir
2. **收集输入** — 对必填输入向用户询问
3. **构建执行顺序** — 根据 depends_on 进行拓扑排序
4. **逐层执行** — 预读角色文件 → 渲染 task 模板 → 执行
5. **保存结果** — 输出到 .ao-output/ 目录

## 适用场景
- 用户提供了 `.yaml` 工作流文件
- 要求多个角色协作完成任务
- 安装了 agency-agents-zh 并希望直接编排多角色
