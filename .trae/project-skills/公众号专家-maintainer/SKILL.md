---
name: "公众号专家-maintainer"
description: "Maintains 公众号专家 project using Session-based Worktree + Branch model. Invoke for bug fixes, feature development, or system maintenance. Each session creates isolated worktree+branch, pushes to remote, user controls merge."
---

# 公众号专家 Maintainer Skill (v4.0)

> 最后更新：2026-05-19
> **每次开始工作前必须先读此文件**

---

## 🎯 项目速览

| 项目 | 值 |
|------|---|
| 名称 | 公众号专家（GongZhongHao Expert） |
| 定位 | 每日财经观察与量化样本学习工具 |
| 技术栈 | Docker + Node.js 20 + TypeScript + PostgreSQL 16 |
| 部署服务器 | 阿里云 CentOS 8 @ `8.134.248.11` |
| NAS 服务器 | 飞牛OS @ `192.168.9.3` (paulproject) |
| 项目用户 | `gongzhonghao` / `paulproject` |
| SSH Key | ed25519 (`gzh_expert_ed25519` / `gzh_nas_ed25519`) |
| 项目目录(本地) | `Z:\代码\养龙虾\公众号专家` |
| 项目目录(阿里云) | `/home/gongzhonghao/apps/gzh-expert-git/` |
| 项目目录(NAS) | `/vol2/1000/docker_related/gzh-worker/` |
| GitHub | https://github.com/xianweibo/wechat-expert |
| API 地址 | http://gzh.relexplace.com |
| 数据库 | PostgreSQL 16 (Docker) |

---

## 🔐 关键凭据（已配置，勿在聊天中明文提及）

### 微信公众号
- AppID: `wx567a639466e247cd`
- AppSecret: 存放于阿里云 `/tmp/.mp_app_secret`，`.env` 中引用

### B站 Worker
- SESSDATA + bili_jct: 存放于 NAS `/tmp/auth.txt`
- MiniMax API Key: `sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo`
- MiniMax Endpoint: `https://api.minimaxi.com/anthropic/v1/messages`
- MiniMax Model: `MiniMax-M2.7`

### B站目标UP主
- UID: `290663424`（有何高见9527）
- 我的UID: `144796213`

### API 认证
- BILIBILI_WORKER_SECRET: `gzh_worker_secret_2026`
- 位置：阿里云 `.env` + NAS 推送时用 `X-Worker-Secret` header

---

## 🏗️ 产品架构（四层）

### 第一层：公众号免费文章

每天一篇，固定结构：

```
标题：今日财经观察｜YYYY-MM-DD

一、今日财经要点 10 条    ← AI 从公开信息生成
二、今日市场观察           ← 宏观/板块/政策/海外/资金面
三、今日学习笔记          ← 用户输入 + AI 整理（原创表达）
四、风险提示             ← 固定模板
五、小程序入口            → 引导查看量化样本观察
```

### 第二层：B站视频总结（新增）

NAS 上的 gzh-worker 每日自动：
1. 用 yutto 下载 B站 UP 主视频字幕
2. 调用 MiniMax M2.7 总结
3. 推送摘要到阿里云 API
4. 阿里云自动创建公众号草稿

### 第三层：小程序广告解锁

页面标题：**今日量化样本观察**

### 第四层：知识库 / AI 助手（后期）

---

## ⚠️ 风控边界（绝对不能违反）

### ❌ 禁止做的事
- 推荐具体股票买入/卖出
- 给出目标价/收益预期
- 加群/收徒/带单
- 一对一投资建议
- 承诺收益/稳赚/必涨
- 使用"牛股""妖股""内幕"等词
- 自动发布公众号文章（必须人工审核）
- 未授权搬运 B 站付费内容（已充电的可整理）

### ✅ 允许做的事
- 公开信息整理
- 量化筛选样本展示（仅名称）
- 市场结构与数据特征分析
- B站充电视频字幕总结（已充电UP主）
- 风险提示与方法论分享
- AI 生成草稿 + 人工审核后发布

---

## 🔧 技术架构

### 阿里云服务器架构

```
┌──────────────────────────────────────────────────────┐
│          宝塔 Nginx (80) - 共用端口                │
│   gzh.relexplace.com → 反向代理 127.0.0.1:39800    │
└──────────────────────────────────────────────────────┘
                        ↓ (39800)
┌─────────────┐     ┌─────────────┐
│  App       │────▶│  PostgreSQL │
│  :3000     │     │   :5432     │
│ (Node.js)   │     │ (Docker内)  │
└─────────────┘     └─────────────┘
```

### NAS B站 Worker 架构

```
NAS (192.168.9.3)
  │
  ├─ yutto (Docker) → 下载B站字幕
  │
  ├─ MiniMax API → AI总结
  │
  └─ curl POST → 阿里云 API
                    │
                    ↓
              /api/bilibili/summary
                    │
                    ↓
              微信公众号草稿
```

### API 端点（已验证）

| 端点 | 状态 | 说明 |
|------|------|------|
| GET /api/health | ✅ 正常 | 健康检查 |
| GET /api/info | ✅ 正常 | 服务信息 |
| POST /api/bilibili/summary | ✅ 已通 | 接收NAS推送，创建公众号草稿 |

---

## 📡 微信接入状态（已验证）

### 公众号
- 类型：订阅号
- AppID：`wx567a639466e247cd`
- AppSecret：已配置
- 草稿 API：✅ **已验证可用**
  - 流程：获取 Token → 调用 draft/add 创建草稿
  - 新增：NAS Worker 可通过 `/api/bilibili/summary` 自动推送

### 小程序
- 已注册（审核中）
- 流量主：需上线后有流量才能开通

---

## 🖥️ 服务器操作指南

### ⚡ 沙箱 SSH 连接（AI 助手专用）

> **重要**：沙箱无法直连外网，必须通过 HTTP 代理 `127.0.0.1:18080` 转发 SSH 连接。
> 所有 NAS 操作必须 `sudo su -` 提权到 root。

```bash
# SSH config 已配置，直接使用别名即可
ssh nas       # → paulproject@8.134.248.11:39022 (frp隧道→NAS)
ssh aliyun    # → gongzhonghao@8.134.248.11:22  (直连阿里云)
```

**SSH config 内容**（`~/.ssh/config`）：
```
Host nas
    HostName 8.134.248.11
    Port 39022
    User paulproject
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking accept-new
    ProxyCommand nc -X connect -x 127.0.0.1:18080 %h %p

Host aliyun
    HostName 8.134.248.11
    Port 22
    User gongzhonghao
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking accept-new
    ProxyCommand nc -X connect -x 127.0.0.1:18080 %h %p
```

**NAS 操作模板**（必须 sudo su -）：
```bash
# 查看容器状态
ssh nas "sudo su - -c 'docker ps'"

# 查看日志
ssh nas "sudo su - -c 'docker logs frpc-gzhworker --tail 20'"

# 编辑配置后重启
ssh nas "sudo su - -c 'docker restart frpc-gzhworker'"

# 检查磁盘
ssh nas "sudo su - -c 'df -h'"
```

**阿里云操作模板**：
```bash
# 查看容器状态
ssh aliyun "docker ps"

# 查看日志
ssh aliyun "docker compose -f /home/gongzhonghao/apps/gzh-expert-git/docker-compose.yml logs -f app"

# 部署
ssh aliyun "cd /home/gongzhonghao/apps/gzh-expert-git && git pull && docker compose up -d --build"
```

### frp 隧道架构

```
[沙箱] ──ProxyCommand(nc)──▶ [8.134.248.11:39022] ──frp隧道──▶ [NAS:22]
[沙箱] ──ProxyCommand(nc)──▶ [8.134.248.11:22]    ──────────▶ [阿里云SSH]

frps 容器: frps-gzhworker (阿里云, 监听 39801)
frpc 容器: frpc-gzhworker (NAS, 连接阿里云 39801)
配置文件:
  - 阿里云: /tmp/frps.ini → 映射到容器 /etc/frp/frps.toml
  - NAS:    /tmp/frpc-gzhworker.ini → 映射到容器 /etc/frp/frpc.toml

当前 frp 转发规则:
  - 39802 → NAS 39800 (阿里云API TCP)
  - 39022 → NAS 22   (SSH, 沙箱专用)
```

### 本地操作（用户 Windows 电脑）

### 阿里云服务器（公众号专家）

```powershell
ssh -i C:\Users\Administrator\.ssh\gzh_expert_ed25519 -o StrictHostKeyChecking=no gongzhonghao@8.134.248.11 "命令"
```

### NAS 服务器（gzh-worker）

```powershell
ssh -i $env:USERPROFILE\.ssh\gzh_nas_ed25519 -o StrictHostKeyChecking=no paulproject@192.168.9.3 "命令"
```

---

## 🔄 内容生成流程（B站视频）

```
NAS (每日)
  │
  ├─ yutto 下载字幕 (BV号由用户手动提供)
  │     ↓
  ├─ MiniMax M2.7 总结
  │     ↓
  └─ POST /api/bilibili/summary
              │
              ↓
        阿里云服务器
              │
  ┌──────────┴──────────┐
  │  获取 access_token  │
  │         ↓          │
  │  创建公众号草稿    │
  └────────────────────┘
              │
              ↓
        人工审核发布
```

---

## 📋 Session 工作流（Git Worktree）

### Session 类型

| 类型 | 前缀 | 示例 | 用途 |
|------|------|------|------|
| Bug修复 | `wt-fix-` | `wt-fix-ad-mock` | 修复问题 |
| 新功能 | `wt-feat-` | `wt-feat-daily-article` | 开发新功能 |
| B站 Worker | `wt-bilibili-` | `wt-bilibili-api` | B站相关开发 |

### 已创建的 Worktree

- `wt-bilibili-api` - feat/bilibili-api
- `wt-minimax-summary` - feat/minimax-summary
- `wt-poster` - feat/poster
- `wt-cron-setup` - feat/cron-setup
- `wt-docker` - feat/docker

---

## 📚 关键文档索引

| 文档 | 路径 | 用途 |
|------|------|------|
| README | `README.md` | 项目介绍和使用指南 |
| 产品方案 | `docs/product-plan.md` | 产品定位、风控边界 |
| 部署方案 | `docs/deployment.md` | 服务器信息、Docker 命令 |
| B站Worker设计 | `docs/superpowers/specs/2026-05-19-bilibili-worker-design.md` | 架构设计 |
| B站Worker实现 | `docs/superpowers/plans/2026-05-19-bilibili-worker-implementation.md` | 实现计划 |
| Skill | `.trae/project-skills/公众号专家-maintainer/SKILL.md` | 项目知识上下文 |

**新会话开始时优先读 SKILL.md 和关键文档。**