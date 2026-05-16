---
name: using-git-worktrees
description: 当需要开始与当前工作区隔离的功能开发，或在执行实现计划之前使用
---

# 使用 Git 工作树

确保工作发生在隔离的工作区中。优先使用平台的原生 worktree 工具。

**核心原则：** 先检测现有隔离。然后用原生工具。再回退到 git。

## 步骤 0：检测现有隔离

创建任何东西之前，先检查你是否已经在一个隔离的工作区里。

如果 `GIT_DIR != GIT_COMMON`（且不是 submodule）：你已经在 linked worktree 内。跳过创建。

## 步骤 1：创建隔离工作区

### 1a. 原生 Worktree 工具（首选）

如果有原生工具（如 `EnterWorktree`），用它。

### 1b. Git Worktree 回退

```bash
git worktree add "$path" -b "$BRANCH_NAME"
cd "$path"
```

## 步骤 3：项目设置

自动检测并运行依赖安装命令（npm install / pip install 等）。

## 步骤 4：验证基线干净

运行测试确保初始状态干净。
