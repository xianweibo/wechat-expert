# 2026-05-20 Superpower框架更新与多session工作配置计划

## 一、本次修改文件清单
| 文件路径 | 操作类型 | 职责说明 |
|---------|---------|---------|
| `README.md` | 修改 | 按照superpower框架更新项目说明 |
| `docs/deployment.md` | 修改 | 更新部署文档，加入FRP端口配置说明 |
| `docs/architecture.md` | 创建 | 新增架构文档，说明项目整体结构 |
| `scripts/frps-gzhworker.ini` | 提交 | 将最新FRP配置纳入版本控制 |
| `scripts/frpc-gzhworker.ini` | 提交 | 将最新FRP配置纳入版本控制 |
| `.trae/skills/公众号专家-maintainer/SKILL.md` | 修改 | 完善项目专属技能文档 |
| `.gitignore` | 修改 | 更新忽略规则，排除敏感文件 |

---

## 二、小步骤任务列表（每步2-5分钟）

### 任务1：更新项目核心文档
**文件：** `README.md`
**步骤：**
```markdown
# 公众号专家
基于Superpowers框架开发的B站字幕提取、AI总结、公众号自动发布系统

## 功能特性
✅ B站视频字幕自动下载（支持大会员视频）
✅ MiniMax大模型内容总结
✅ 公众号草稿自动发布
✅ FRP内网穿透（NAS -> 阿里云）
✅ 多Session Worktree开发模式

## 技术栈
前端：React + TypeScript
后端：Node.js + Express + PostgreSQL
自动化脚本：Python
部署：Docker + FRP内网穿透

## 端口配置
FRP服务端：39801
外部访问端口：39802 -> 映射到NAS本地39800
```
**验证：** 打开文件确认内容正确
---

### 任务2：更新部署文档
**文件：** `docs/deployment.md`
**步骤：** 在文档末尾添加FRP端口配置章节：
```markdown
## 九、FRP内网穿透配置（已验证）
### 端口分配
- 阿里云FRP服务端监听端口：39801
- 外部访问端口：39802
- 映射目标：NAS本地39800端口

### 配置文件位置
- 阿里云服务端配置：`/tmp/frps.ini`
- NAS客户端配置：`/tmp/frpc-gzhworker.ini`

### 重启命令
```bash
# 阿里云端
sudo docker restart frps-gzhworker

# NAS端
sudo docker restart frpc-gzhworker
```
**验证：** 确认配置信息与实际部署一致
---

### 任务3：创建架构文档
**文件：** `docs/architecture.md`
**步骤：**
```markdown
# 系统架构

## 整体结构
┌─────────────────┐    FRP隧道     ┌─────────────────┐    调用    ┌─────────────────┐
│   NAS本地服务   │ -------------- │  阿里云服务端    │ <--------  │   公众号后台     │
│  (39800端口)    │  39801协议端口 │  (39802对外开放) │           │   (微信平台)     │
└─────────────────┘                └─────────────────┘            └─────────────────┘
         ↓                                 ↓
         ▼                                 ▼
┌─────────────────┐                ┌─────────────────┐
│ B站视频爬取服务 │                │  PostgreSQL数据库│
│ MiniMax API调用 │                │  存储内容数据   │
└─────────────────┘                └─────────────────┘

## 模块说明
1. **NAS端模块**：负责B站字幕下载、AI内容总结
2. **阿里云端模块**：负责对外提供API、公众号草稿发布
3. **FRP穿透模块**：实现内网NAS与公网阿里云的通信
```
**验证：** 确认架构图与实际部署匹配
---

### 任务4：更新.gitignore
**文件：** `.gitignore`
**步骤：** 添加以下规则：
```gitignore
# FRP配置包含敏感信息，不提交
scripts/frps*.ini
scripts/frpc*.ini

# 敏感密钥文件
*.key
*.pem
.env
auth.json

# 临时文件
*.tmp
*.log
.DS_Store
node_modules
```
**验证：** 确认敏感文件不会被误提交
---

### 任务5：提交代码到Github
**步骤：**
```bash
# 切换到主分支
git checkout main

# 拉取最新代码
git pull origin main

# 添加修改文件
git add README.md docs/deployment.md docs/architecture.md .gitignore .trae/skills/公众号专家-maintainer/SKILL.md

# 提交
git commit -m "chore: update docs according to superpower framework"

# 推送
git push origin main
```
**验证：** 确认Github上代码已更新
---

### 任务6：配置多Session Worktree开发环境
**步骤：**
```bash
# 创建feature分支worktree
git worktree add ../wt-feature-bilibili-summary -b feature/bilibili-summary

# 创建bugfix分支worktree
git worktree add ../wt-bugfix-frp-connection -b bugfix/frp-connection

# 查看所有worktree
git worktree list
```
**验证：** 确认两个worktree创建成功，可独立工作
---

## 三、执行选项
1. 子代理驱动（推荐）- 使用subagent-driven-development技能并发执行多个任务
2. 内联执行 - 逐个顺序执行任务
