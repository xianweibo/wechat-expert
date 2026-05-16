# 公众号专家 - 部署方案

> 最后更新：2026-05-16

---

## 一、服务器信息

| 项目 | 值 |
|------|---|
| IP | 8.134.248.11 |
| 系统 | CentOS 8 |
| 项目用户 | gongzhonghao |
| 项目目录 | /home/gongzhonghao/apps/gzh-expert |
| SSH Key | ed25519 (gzh_expert_ed25519) |

---

## 二、目录结构

```
/home/gongzhonghao/apps/gzh-expert/
├── docker-compose.yml      # 容器编排
├── Dockerfile              # 应用镜像
├── .env                    # 环境变量（不提交 Git）
├── .env.example            # 环境变量模板（提交 Git）
├── .gitignore
├── nginx/
│   ├── nginx.conf          # Nginx 配置
│   └── ssl/                # SSL 证书（后续）
├── src/                    # 源代码
├── data/
│   └── uploads/            # 上传文件
├── logs/                   # 日志
├── docs/                   # 文档
│   ├── product-plan.md     # 产品方案
│   └── deployment.md       # 本文件
└── scripts/                # 脚本
```

---

## 三、Docker 容器架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Nginx      │────▶│    App       │────▶│  PostgreSQL │
│   :80/:443   │     │   :3000      │     │   :5432     │
│  (反向代理)   │     │ (Node.js)    │     │  (数据库)    │
└─────────────┘     └─────────────┘     └─────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
   外部访问           API + 定时任务         数据持久化
```

### 容器说明

| 容器名 | 镜像 | 端口 | 说明 |
|--------|------|------|------|
| gzh-expert-app | node:20-alpine | 3000 | 后端 API 服务 |
| gzh-expert-db | postgres:16-alpine | 5432 | 数据库 |
| gzh-expert-nginx | nginx:alpine | 80, 443 | 反向代理 |

---

## 四、部署命令

### 首次部署

```bash
# 1. 进入项目目录
cd ~/apps/gzh-expert

# 2. 复制环境变量模板并填写
cp .env.example .env
nano .env  # 填入真实值

# 3. 构建并启动所有容器
docker compose up -d --build

# 4. 查看容器状态
docker compose ps

# 5. 查看日志
docker compose logs -f app
```

### 日常操作

```bash
# 启动
docker compose up -d

# 停止
docker compose down

# 重启某个服务
docker compose restart app

# 查看日志
docker compose logs -f app

# 进入容器调试
docker compose exec app sh

# 数据库备份
docker compose exec postgres pg_dump -U gzh_expert gzh_expert > backup_$(date +%Y%m%d).sql

# 更新代码后重新构建
git pull
docker compose up -d --build
```

---

## 五、安全配置清单

### 已完成
- [x] 创建专用项目用户（非 root）
- [x] SSH Key 登录（ed25519）
- [x] 免密 sudo 配置
- [x] Docker 用户组权限
- [x] .env 文件加入 .gitignore

### 待完成
- [ ] 配置防火墙规则（仅开放 80/443/22）
- [ ] 禁用密码登录（确认 SSH Key 可用后）
- [ ] SSL 证书配置（Let's Encrypt 或自有证书）
- [ ] Nginx 安全头配置
- [ ] 数据库定期自动备份
- [ ] Docker 日志轮转配置

---

## 六、微信公众号接入

### 当前状态
- 类型：订阅号（未认证）
- AppID：已获取（存放在 .env）
- AppSecret：已重置（存放于服务器 .env，不入库）
- 白名单 IP：需添加 8.134.248.11
- 草稿 API：当前使用 manual 模式（手动复制）

### 接入条件满足后切换为 api 模式
```env
WECHAT_MP_DRAFT_MODE=api
```

---

## 七、微信小程序接入

### 当前状态
- 已注册（审核中）
- 类目：待确认（建议非游戏类目）
- 流量主：需上线后有流量才能开通
- 广告位：开通流量主后创建激励视频广告位

### 开发阶段先用模拟模式
```env
AD_MODE=mock
```

拿到 adUnitId 后切换：
```env
AD_MODE=wechat
MINIPROGRAM_AD_UNIT_ID=你的广告位ID
```

---

## 八、故障排查

```bash
# 容器没启动？
docker compose ps

# 端口被占用？
sudo lsof -i :3000
sudo lsof -i :80
sudo lsof -i :5432

# 数据库连不上？
docker compose exec postgres psql -U gzh_expert -d gzh_expert

# Nginx 报错？
docker compose logs nginx

# 磁盘空间？
df -h
docker system df
docker system prune -f  # 清理无用镜像（谨慎）
```
