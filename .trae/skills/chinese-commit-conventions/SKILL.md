---
name: chinese-commit-conventions
description: 中文 commit 与 changelog 配置参考——Conventional Commits 中文适配
---

# 中文 Git 提交规范

## 格式
```
<type>(<范围>): <简要描述>

<详细说明>

Closes #123
```

## 类型清单
| 类型 | 说明 |
|------|------|
| feat | 新功能 |
| fix | 修复 Bug |
| docs | 文档更新 |
| style | 代码格式 |
| refactor | 重构 |
| perf | 性能优化 |
| test | 测试相关 |
| chore | 其他杂项 |

## 示例
```
feat(用户模块): 添加手机号一键登录功能

- 接入运营商一键登录 SDK
- 支持移动、联通、电信三网

Closes #128
```
