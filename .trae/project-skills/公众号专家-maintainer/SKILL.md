---
name: "公众号专家-maintainer"
description: "Maintains 公众号专家 project using Session-based Worktree + Branch model. Invoke for bug fixes, feature development, or system maintenance. Each session creates isolated worktree+branch, pushes to remote, user controls merge."
---

# 公众号专家 Maintainer Skill (v2.0)

> 最后更新：2026-05-16
> **每次开始工作前必须先读此文件**

---

## 🎯 项目速览

| 项目 | 值 |
|------|---|
| 名称 | 公众号专家（GongZhongHao Expert） |
| 定位 | 每日财经观察与量化样本学习工具 |
| 技术栈 | Docker + Node.js 20 + TypeScript + PostgreSQL 16 + Nginx |
| 部署服务器 | CentOS 8 @ `8.134.248.11` |
| 项目用户 | `gongzhonghao` |
| SSH Key | ed25519 (`gzh_expert_ed25519`) |
| 项目目录(本地) | `Z:\代码\养龙虾\公众号专家` |
| 项目目录(服务器) | `/home/gongzhonghao/apps/gzh-expert` |

---

## 🏗️ 产品架构（三层）

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

**关键规则**：
- 财经要点来源：公开财经新闻源，中性表达，不预测涨跌
- 学习笔记：不写"某某视频精华总结"，用自己语言重构
- 禁止词：牛股、妖股、必涨、内幕、推荐买入、目标价等

### 第二层：小程序广告解锁

页面标题：**今日量化样本观察**

```
以下名称由固定历史数据规则生成，仅作为学习样本展示。
- 样本一
- 样本二
- 样本三
[固定免责声明]
```

**关键规则**：
- 只显示股票名称，不解释、不建议、不写理由、不写买卖点
- 解锁方式：微信激励视频广告（或模拟模式）
- 不叫"股票池"，统一叫"量化样本观察"

### 第三层：知识库 / AI 助手（后期）

腾讯 ima 知识库沉淀 + 学习问答助手（只回答方法论问题）

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
- 未授权搬运 B 站付费内容

### ✅ 允许做的事
- 公开信息整理
- 量化筛选样本展示（仅名称）
- 市场结构与数据特征分析
- 风险提示与方法论分享
- AI 生成草稿 + 人工审核后发布
- 激励广告解锁补充内容

### 替代表达对照表

| 高风险 | 安全替代表达 |
|--------|-------------|
| 股票池 | 量化样本观察 |
| 选股 | 数据筛选样本 |
| 牛股 | 学习样本 |
| 推荐买入 | 入选规则说明 |
| 目标价 | 估值区间讨论 |
| 明日机会 | 今日数据特征 |

---

## 🔧 技术架构

### Docker 容器编排

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Nginx      │────▶│    App       │────▶│  PostgreSQL │
│   :80/:443   │     │   :3000      │     │   :5432     │
│  (反向代理)   │     │ (Node.js)    │     │  (数据库)    │
└─────────────┘     └─────────────┘     └─────────────┘
```

| 容器名 | 镜像 | 端口 | 说明 |
|--------|------|------|------|
| gzh-expert-app | node:20-alpine | 3000 | 后端 API 服务 |
| gzh-expert-db | postgres:16-alpine | 5432 | 数据库 |
| gzh-expert-nginx | nginx:alpine | 80, 443 | 反向代理 |

### 关键文件位置

| 文件 | 本地路径 | 说明 |
|------|----------|------|
| 产品方案 | `docs/product-plan.md` | 产品定位、三层架构、风控边界 |
| 部署方案 | `docs/deployment.md` | 服务器信息、Docker 命令、故障排查 |
| Docker 编排 | `docker-compose.yml` | 三容器定义 |
| 环境变量模板 | `.env.example` | 所有可配置项（不含真实值） |
| Nginx 配置 | `nginx/nginx.conf` | 反向代理配置 |
| 入口文件 | `src/index.ts` | Express API 入口 |

---

## 📡 微信接入状态

### 公众号
- 类型：订阅号（未认证）
- AppID：存放在 `.env` 的 `WECHAT_MP_APP_ID`
- AppSecret：存放在 `.env` 的 `WECHAT_MP_APP_SECRET`（**绝不入库**）
- 白名单 IP：需添加 `8.134.248.11`
- 草稿 API：当前 `WECHAT_MP_DRAFT_MODE=manual`（手动复制），认证后切换为 `api`

### 小程序
- 已注册（审核中）
- 类目：待确认（**非游戏类目**）
- 流量主：需上线后有流量才能开通
- 广告位：开通流量主后创建激励视频广告位，填入 `MINIPROGRAM_AD_UNIT_ID`
- 当前模式：`AD_MODE=mock`（模拟），拿到 adUnitId 后切换为 `wechat`

### 绑定关系
- 公众号可绑定小程序（用于引流）
- 但公众号流量主 ≠ 小程序流量主，**不互通**

---

## 🖥️ 服务器操作指南

### 远程命令格式（从本地 PowerShell）

```powershell
ssh -i C:\Users\Administrator\.ssh\gzh_expert_ed25519 -o StrictHostKeyChecking=no gongzhonghao@8.134.248.11 "命令"
```

### 常用操作

```bash
# 进入项目目录
cd ~/apps/gzh-expert

# Docker 操作
docker compose up -d --build        # 构建并启动
docker compose ps                    # 查看状态
docker compose logs -f app           # 查看日志
docker compose restart app           # 重启应用
docker compose down                  # 停止所有容器

# 数据库备份
docker compose exec postgres pg_dump -U gzh_expert gzh_expert > backup.sql

# 更新部署
git pull && docker compose up -d --build
```

### 已完成的服务器配置
- [x] 项目用户 `gongzhonghao` + sudo 免密
- [x] SSH Key 登录（ed25519）
- [x] Docker 用户组权限
- [x] Docker Compose v2.27.0
- [x] 项目目录 `~/apps/gzh-expert/`
- [x] `.env` 开发环境已创建

### 待完成的安全配置
- [ ] 防火墙规则（仅开放 80/443/22）
- [ ] 禁用密码登录（确认 SSH Key 可用后）
- [ ] SSL 证书配置
- [ ] Nginx 安全头
- [ ] 数据库定期自动备份

---

## 🔄 内容生成流程

```
公开财经信息源
    ↓
AI 整理生成 10 条财经要点（方案 A：联网检索）
    ↓
用户输入学习笔记 / 视频参考
    ↓
AI 生成公众号文章草稿（含风控检查）
    ↓
人工审核修改（必须！）
    ↓
创建公众号草稿（API 或手动复制）
    ↓
文末引导小程序（克制文案）
    ↓
用户观看激励广告（模拟/正式）
    ↓
解锁今日量化样本观察
    ↓
内容沉淀到知识库（后续）
```

---

## 📋 Session 工作流（Git Worktree）

### Session 类型

| 类型 | 前缀 | 示例 | 用途 |
|------|------|------|------|
| Bug修复 | `wt-fix-` | `wt-fix-ad-mock` | 修复问题 |
| 新功能 | `wt-feat-` | `wt-feat-daily-article` | 开发新功能 |
| 优化 | `wt-opt-` | `wt-opt-ai-prompt` | 性能优化 |
| 基础设施 | `wt-infra-` | `wt-infra-docker-setup` | 环境/部署 |

### 创建 Session

```powershell
cd Z:\代码\养龙虾\公众号专家
git worktree add ../wt-feat-daily-article -b feat/daily-article
cd ../wt-feat-daily-article
# 开发...
git add . && git commit -m "feat(article): 每日文章生成模块"
git push origin feat/daily-article
# 用户审查后手动 merge
```

---

## 🔐 凭据安全规则（永久记住）

1. **绝不**在聊天中接收 AppSecret、密码、API Key
2. **绝不**将密钥写入代码或提交到 Git
3. 密钥只存放于服务器 `.env` 文件
4. `.env` 已加入 `.gitignore`
5. 用户泄露密钥时立即提醒重置

---

## 📚 关键文档索引

| 文档 | 路径 | 用途 |
|------|------|------|
| 产品方案 | `docs/product-plan.md` | 产品定位、三层架构、风控边界 |
| 部署方案 | `docs/deployment.md` | 服务器信息、Docker 命令、故障排查 |
| 环境变量模板 | `.env.example` | 所有可配置项说明 |
| Docker 编排 | `docker-compose.yml` | 容器定义和依赖关系 |

**新会话开始时优先读这 4 个文件，避免重复询问用户已确定的内容。**
