---
name: chinese-git-workflow
description: 国内 Git 平台配置参考——Gitee/Coding/极狐 GitLab/CNB 的差异与适配
---

# 国内 Git 工作流规范

## 核心原则
工作流服务于团队效率，选适合团队规模的方案。

## 平台对比
| 特性 | Gitee | Coding | 极狐 GitLab | CNB |
|------|-------|--------|-------------|-----|
| 国内访问 | 快 | 快 | 快 | 快 |
| CI/CD | Gitee Go | Coding CI | 内置 CI | .cnb.yml |
| 免费私有仓库 | 有 | 有 | 有 | 有 |

## 推荐工作流：简化版 Git Flow
```
main ──●──────●────── 生产环境（受保护）
       \    / \    /
dev    ──●──●─●──●─●── 开发/测试环境
        \  /    \  /
feat/x   ●●      ●●  功能分支
```

## 分支命名规范
- `feat/user-login` - 新功能
- `fix/payment-callback` - Bug 修复
- `hotfix/v2.0.1` - 紧急修复
- `release/v2.1.0` - 版本发布

## Commit Message 规范（中文版）
```
<type>(<范围>): <简要描述>

<详细说明>

关联 Issue: #123
```
