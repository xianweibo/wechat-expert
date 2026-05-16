---
name: team-git-branch-policy
description: 强制 Git 分支管理规范——Feature Branch → Code Review → Manual Merge 流程
---

# 团队 Git 分支管理规范

## 核心原则
所有代码变更必须经过：Feature Branch → Code Review → Manual Merge

## 分支结构
```
main (生产就绪)
  ↑ manual merge (only by lead/maintainer)
  │
  ├─ develop (集成测试通过)
  │    ↑ auto-merge from feature branches
  │    │
  │    ├─ feature/TICKET-ID-description
  │    ├─ bugfix/TICKET-ID-description
  │    └─ hotfix/TICKET-ID-description → 直接到 main
```

## 强制工作流

### 1. 开始新任务前
```bash
git checkout develop
git pull origin develop
git checkout -b feature/JIRA-123-add-stock-alert
```

### 2. Commit 规范（中文版）
```
<type>(<ticket-id>): <中文标题>

<空行>
<正文：做了什么，为什么>

<空行>
- 要点列表

Closes #ticket-id
```

类型：feat / fix / docs / style / refactor / perf / test / chore / hotfix

### 3. 代码审查
Push 后自动触发 CI：
- 运行自动化测试
- 代码质量检查
- 安全扫描

### 4. 人工 Merge 权限控制
| 目标分支 | 允许 Merge 的人 | 要求 |
|---------|----------------|------|
| `develop` | 任何团队成员 | ≥1 人 Review 通过 |
| `release/*` | Tech Lead | 全部测试通过 |
| `main` | Maintainer | 生产部署准备就绪 |

Merge 使用 `--no-ff` 保留历史：
```bash
git merge --no-ff feature/JIRA-123 -m "merge(JIRA-123): reviewed by @reviewer"
```

## 禁止事项 ❌
- ❌ 直接推送到 main/develop/master
- ❌ 在 main 上直接 commit
- ❌ 跳过 Code Review 直接 Merge
- ❌ Force Push 到公共分支
- ❌ 超过 500 行的单次 Commit
