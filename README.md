# 公众号专家

> 每日财经观察与量化样本学习工具

## 🎯 项目简介

公众号专家是一个结合公众号内容运营、小程序广告解锁和 AI 辅助的财经学习工具。

- **公众号**：每天发布财经观察与学习笔记
- **小程序**：激励视频广告解锁量化样本
- **AI**：辅助生成内容草稿，人工审核后发布

## ⚠️ 合规声明

本项目严格遵守内容风控边界：

- ❌ 禁止推荐具体股票买入/卖出
- ❌ 禁止承诺收益/稳赚/必涨
- ❌ 禁止加群/带单/一对一投资建议
- ✅ 允许公开信息整理与市场结构分析
- ✅ 允许量化样本展示（仅名称）
- ✅ 允许 AI 生成草稿 + 人工审核后发布

详细内容见 [产品方案](./docs/product-plan.md)。

## 🏗️ 技术架构

```
宝塔 Nginx (80) - 共用端口
    ↓ (反向代理 gzh.relexplace.com → 127.0.0.1:8080)
┌─────────────┐     ┌─────────────┐
│  App       │────▶│  PostgreSQL │
│  :3000     │     │   :5432     │
│ (tsx 运行)  │     │ (Docker内)   │
└─────────────┘     └─────────────┘
```

| 技术 | 说明 |
|------|------|
| 容器 | Docker + Docker Compose |
| 后端 | Node.js 20 + TypeScript + Express |
| 数据库 | PostgreSQL 16 |
| 运行时 | tsx（直接运行 TS，无需编译） |
| 部署 | CentOS 8 @ 8.134.248.11 |

## 🚀 快速开始

### 环境要求

- Docker & Docker Compose
- Git
- Node.js 20（本地开发）

### 本地开发

```bash
# 克隆
git clone https://github.com/xianweibo/wechat-expert.git
cd wechat-expert

# 复制环境变量
cp .env.example .env
# 编辑 .env 填入真实值

# 安装依赖
npm install

# 开发模式
npm run dev

# 或用 Docker
docker compose up -d --build
```

### 部署到服务器

```bash
# 服务器上
cd ~/apps/gzh-expert-git
git clone https://github.com/xianweibo/wechat-expert.git .
cp .env.example .env
# 编辑 .env
docker compose up -d --build
```

详细部署步骤见 [部署方案](./docs/deployment.md)。

## 📁 项目结构

```
wechat-expert/
├── src/                    # 源代码
│   └── index.ts            # 入口
├── docs/                   # 文档
│   ├── product-plan.md     # 产品方案
│   └── deployment.md       # 部署方案
├── scripts/                # 脚本
├── docker-compose.yml      # 容器编排
├── Dockerfile              # 应用镜像
├── package.json
├── tsconfig.json
├── .env.example           # 环境变量模板
└── .gitignore
```

## 🔑 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/info` | GET | 服务信息 |

## 🖥️ 服务器信息

| 项目 | 值 |
|------|---|
| IP | `8.134.248.11` |
| 项目用户 | `gongzhonghao` |
| SSH Key | `gzh_expert_ed25519` |
| API 地址 | http://gzh.relexplace.com |
| 项目目录 | `/home/gongzhonghao/apps/gzh-expert-git/` |

## 🔐 凭据安全

- **绝不**将密钥提交到 Git（`.env` 已在 `.gitignore`）
- 密钥只存放于服务器 `.env` 文件
- 公众号 AppSecret 等敏感信息不存入代码仓库

## 📄 许可证

MIT