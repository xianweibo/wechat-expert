---
name: team-workflow-session
description: 当开发大型功能需要多 Session 并行、使用 Git Worktree 隔离开发时触发
---

# 团队工作流：Worktree 并行开发模式

## 核心原则
1. **隔离性** — 每个功能/任务在独立 Worktree 中开发
2. **并行性** — 多个开发者或 AI Session 可同时工作不冲突
3. **可追溯** — 每个 Worktree 对应明确的 Issue/Ticket

## 触发条件
- "这个功能比较大，想并行开发"
- "需要多人同时改不同的模块"
- "用 worktree 分几个 session 做"

## 工作流程

### Phase 1: 任务拆解
评估维度：
- 影响范围（多少个文件/模块）
- 依赖关系（是否有先后顺序）
- 预估工时（>4小时建议拆分）

输出任务分解表：
| Task ID | 任务名称 | 负责人/Session | 依赖 | 预估时间 |

### Phase 2: Worktree 创建
```bash
# 命名规范：feature/<ticket-id>-<short-description>
git worktree add ../project-T001 -b feature/T001-stock-alert-model
git worktree add ../project-T002 -b feature/T002-alert-api

# 验证
git worktree list
```

### Phase 3: Session 分配策略
| Session 类型 | 用途 | 典型任务 |
|------------|------|---------|
| **Session-Core** | 核心架构/数据层 | 数据库迁移、Model 设计 |
| **Session-API** | 接口层开发 | REST API、业务逻辑 |
| **Session-Frontend** | 前端实现 | 页面组件、交互逻辑 |
| **Session-Test** | 测试验证 | 单元测试、集成测试 |

### Phase 4: 进度同步机制
每完成一个 Task 后：
```bash
# 在当前 Worktree 中提交
git add .
git commit -m "feat(T001): complete stock alert data model"

# 同步回主仓库
cd ../main-project
git fetch ../project-T001 feature/T001:feature/T001
```

### Phase 5: 合并策略
按拓扑排序合并：
```
T-001 (数据模型)
   ↓
T-002 (API) ← T-003 (前端) [可并行]
   ↓              ↓
   └──────┬──────┘
          ↓
      T-004 (测试)
```

## 清理命令
```bash
# 删除 Worktree
git worktree remove ../project-T001

# 清理已合并的分支
git branch -d feature/T001-stock-alert-model
```
