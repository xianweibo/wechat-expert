---
name: "公众号专家-maintainer"
description: "Maintains 公众号专家 project using Session-based Worktree + Branch model. Invoke for bug fixes, feature development, or system maintenance. Each session creates isolated worktree+branch, pushes to remote, user controls merge."
---

# 公众号专家 Maintainer Skill (v1.0)

## 🎯 核心理念

### **Session-Based Development**
- 每个 **Session** = 一个独立的 **Worktree** + **Git Branch**
- Session 之间**完全隔离**，可并行开发
- 每个 Session push 到**独立的远程分支**
- **用户手动控制何时 merge 到 main**

### **优势对比**

| 维度 | 旧流程 (Auto-Merge) | 新流程 (Manual Merge) |
|------|---------------------|----------------------|
| **Branch管理** | 自动合并到main | 保留独立branch |
| **回滚能力** | 需要revert commit | 直接删除/禁用merge |
| **Code Review** | 已合并，难review | branch独立，可PR |
| **并行开发** | 需要频繁处理冲突 | 各自branch，零冲突 |
| **历史清晰度** | 线性历史 | 清晰的feature分支图 |

---

## 📋 Session 命名规范

### **Worktree 命令**: `wt-<session_type>-<short_desc>`

| Session类型 | 前缀 | 示例 | 用途 |
|-----------|------|------|------|
| Bug修复 | `wt-fix-` | `wt-fix-login-error` | 修复问题 |
| 新功能 | `wt-feat-` | `wt-feat-wechat-integration` | 开发新功能 |
| 优化 | `wt-opt-` | `wt-opt-perf` | 性能优化 |
| 实验 | `wt-exp-` | `wt-exp-new-arch` | 尝试性改动 |
| 紧急 | `wt-hot-` | `wt-hot-critical-fix` | 紧急修复 |

### **Branch 命令**: `<type>/<short_desc>`

```
fix/login-error       # 修复类
feat/wechat-api       # 功能类
opt/performance       # 优化类
exp/new-architecture  # 实验类
hot/security-fix      # 紧急类
```

---

## 🔧 工作流程（6步）

### **Step 1: 创建新 Session**

```powershell
cd Z:\代码\养龙虾\公众号专家

# 格式: git worktree add ../wt-<type>-<desc> -b <branch_name>
git worktree add ../wt-fix-login -b fix/login-error
```

**示例**:
```powershell
# Session A: 修复登录问题
git worktree add ../wt-fix-login -b fix/login-error

# Session B: 开发微信集成 (可同时进行)
git worktree add ../wt-feat-wechat -b feat/wechat-integration
```

### **Step 2: 在 Session 中开发**

```powershell
# 进入 worktree 目录
cd ../wt-fix-login

# 正常开发、测试、提交...
# 所有操作都在这个隔离的环境中进行
git add .
git commit -m "fix: 修复登录页面验证问题"
```

**关键点**:
- ✅ 每个Session有独立的文件副本
- ✅ 可以同时编辑同一文件的不同部分（不冲突）
- ✅ 提交只影响当前branch

### **Step 3: Push 到远程分支（不合并）**

```powershell
# 在 worktree 目录中执行
cd ../wt-fix-login

# Push 到同名远程分支
git push origin fix/login-error

# 或者使用 -u 设置upstream
git push -u origin fix/login-error
```

**⚠️ 重要**: 
- ❌ **不要** `git checkout main && git merge`
- ✅ **只需** push 到远程，保留本地branch

### **Step 4: 本地测试验证**

```powershell
# 在每个 worktree 中运行测试
cd ../wt-fix-login
# 运行该Session相关的测试
```

### **Step 5: 用户审查和决策**

当所有 Session 完成开发并push后：

```powershell
# 查看所有远程分支
git branch -r | Select-String -NotMatch "main"

# 或使用GitHub UI查看所有分支
```

**用户决策选项**:

| 决策 | 操作 | 适用场景 |
|------|------|----------|
| ✅ **Merge** | 手动合并到main | 测试通过，准备上线 |
| ⏸️ **Hold** | 暂不合并，继续观察 | 需要更多测试 |
| ❌ **Discard** | 删除分支，不合并 | 方案不好，放弃 |
| 🔄 **Rework** | 在原branch上继续修改 | 需要调整 |

### **Step 6: 手动 Merge（用户控制）**

#### **方式A: 使用 Git 命令行**

```powershell
# 回到主目录
cd Z:\代码\养龙虾\公众号专家

# 切换到main
git checkout main

# Pull最新
git pull origin main

# 合并指定分支（按顺序）
git merge fix/login-error --no-edit
git merge feat/wechat-integration --no-edit

# 推送更新后的main
git push origin main
```

#### **方式B: 使用 GitHub/GitLab UI** (推荐)

1. 打开仓库页面
2. 点击 "Pull requests" → "New pull request"
3. 选择 branch: `fix/login-error` → `main`
4. 添加标题、描述
5. 点击 "Create PR"

**优点**:
- 👀️ 可视化查看变更
- 💬 可在线 Code Review
- 🔒 保护 main 分支（需PR才能合并）
- 📊 自动运行 CI/CD 测试

---

## 🗑️ Session 生命周期

```
创建 Session → 开发 → Commit → Push → [Review] → [Merge/Discard] → Cleanup
    ↓           ↓        ↓       ↓         ↓            ↓           ↓
  wt-fix-xxx  编辑文件  git commit  git push   用户检查    用户操作    删除worktree
              测试验证             远程branch  PR/Merge    更新main
```

### **Cleanup: 清理已合并的 Session**

```powershell
# 方法1: 删除 worktree（推荐在merge后做）
git worktree remove ../wt-fix-login

# 方法2: 删除远程分支（merge后可选）
git push origin --delete fix/login-error

# 方法3: 删除本地分支
git branch -d fix/login-error
```

---

## 📍 文件位置参考

### **Local (本地)**
| 文件 | 本地路径 | 用途 |
|------|----------|------|
| .trae/skills/ | `.trae/skills/` | AI Skills (通用+项目专属) |
| sync-skills.ps1 | `./` | Superpowers 同步脚本 |

---

## ⚠️ 最佳实践

### **✅ DO (推荐做法)**

1. **每个独立任务创建新Session**
   - 即使是小修复也用独立worktree
   
2. **Push前必须本地测试**
   - 确保测试通过再push
   
3. **写清晰的commit message**
   ```
   type(scope): subject
   body (optional)
   
   示例:
   fix(login): 修复登录页面密码验证不生效问题
   
   - 添加表单验证逻辑
   - 改进错误提示
   ```

4. **定期清理已完成的Session**
   - merge后删除worktree
   - 定期清理远程分支

### **❌ DON'T (避免做法)**

1. **不要在main上直接开发**
   - 始终在worktree/branch中工作
   
2. **不要自动merge到main**
   - 让用户控制何时合并
   
3. **不要忘记push到远程**
   - local-only的branch无法fallback

---

## 🔐 凭据配置（永久记住，无需每次提醒）

### **SSH 密钥**
```bash
# SSH 私钥路径 (本地 Windows)
C:/Users/Administrator/.ssh/id_ed25519
```

### **沙箱 SSH 连接（AI 助手专用）**

> **关键规则**：
> 1. 沙箱无法直连外网，必须通过 HTTP 代理 `127.0.0.1:18080` 转发 SSH
> 2. 所有 NAS 操作必须 `sudo su -` 提权到 root
> 3. SSH config 已配置，直接用别名 `ssh nas` / `ssh aliyun`

```bash
ssh nas       # → paulproject@8.134.248.11:39022 (frp隧道→NAS)
ssh aliyun    # → gongzhonghao@8.134.248.11:22  (直连阿里云)
```

**SSH config**（`~/.ssh/config`）：
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
ssh nas "sudo su - -c 'docker ps'"
ssh nas "sudo su - -c 'docker logs frpc-gzhworker --tail 20'"
ssh nas "sudo su - -c 'df -h'"
```

**阿里云操作模板**：
```bash
ssh aliyun "docker ps"
ssh aliyun "cd /home/gongzhonghao/apps/gzh-expert-git && git pull && docker compose up -d --build"
```

### **frp 隧道架构**

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

**注意**：每次新会话沙箱环境是全新的，SSH 密钥和 config 需要重新配置。可在会话开始时执行以下初始化：

```bash
# 1. 生成密钥
ssh-keygen -t ed25519 -C "solo-sandbox-gzh" -f ~/.ssh/id_ed25519 -N ""

# 2. 写入 SSH config
cat > ~/.ssh/config << 'EOF'
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
EOF
chmod 600 ~/.ssh/config

# 3. 公钥已添加到 NAS 和阿里云的 authorized_keys，无需再次添加
# 公钥指纹: solo-sandbox-gzh
```

---

*最后更新: 2026-05-20*
*版本: v1.1 - 新增沙箱 SSH 连接配置*
