---
name: mcp-builder
description: MCP 服务器构建方法论——系统化构建生产级 MCP 工具
---

# MCP 服务器构建

系统化设计、实现、测试和部署 Model Context Protocol 服务器的方法论。

## 三种原语
- **Tools（工具）**：AI 助手主动调用的函数，有副作用
- **Resources（资源）**：AI 助手只读访问的数据源
- **Prompts（提示词模板）**：预定义交互模板

## Tool 设计原则
- 命名：`snake_case`，动词开头
- 参数：每个参数有类型约束和 `.describe()` 描述
- 描述：说明用途 + 返回内容 + 限制

## 错误处理四原则
1. 永远不让服务器崩溃 — try/catch 包裹所有外部调用
2. 返回可操作的错误信息
3. 使用 `isError: true`
4. 区分错误类型

## 测试策略
- 单元测试：业务逻辑与 MCP 注册分离
- 集成测试：用 SDK Client 做端到端验证
- MCP Inspector：交互式调试
