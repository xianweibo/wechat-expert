#!/bin/bash
# ============================================
# 公众号专家 - 一键刷新"语言风格"档案
# ============================================
# 跑在 NAS 上（paulproject 用户，需要 sudo 拿 docker 权限）。
#
# 流程：
#   1. 健康检查 chromadb；挂了自动拉起来
#   2. 拉公众号发表记录 -> markdown
#   3. 入库 chromadb (gzh_articles collection)
#   4. RAG 检索 + MiniMax-M3 生成风格总结
#   5. 落到 /vol2/1000/docker_related/gzh-chroma/style_summary.txt
#
# 用法：
#   chmod +x scripts/refresh_style.sh
#   sudo bash scripts/refresh_style.sh
#
# 依赖： /tmp/.mp_app_secret 已存在且非空
#        /vol2/1000/docker_related/gzh-chroma 目录存在
# ============================================

set -euo pipefail

# ---------- 路径 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
CHROMA_DATA="/vol2/1000/docker_related/gzh-chroma"
ARTICLES_DIR="${CHROMA_DATA}/articles"
CHROMA_BASE="${CHROMA_BASE:-http://127.0.0.1:8100}"
COLLECTION="${CHROMA_COLLECTION:-gzh_articles}"

# MiniMax 配置 (从环境变量或 .env 读)
MINIMAX_KEY="${MINIMAX_KEY:-}"
MINIMAX_HOST="${MINIMAX_HOST:-api.minimaxi.com}"
MINIMAX_MODEL="${MINIMAX_MODEL:-MiniMax-M3}"
if [ -z "${MINIMAX_KEY}" ] && [ -f "${PROJECT_DIR}/gzh-worker/.env" ]; then
    MINIMAX_KEY=$(grep -E '^MINIMAX_API_KEY=' "${PROJECT_DIR}/gzh-worker/.env" | cut -d'=' -f2- | tr -d '"' || true)
fi
if [ -z "${MINIMAX_KEY}" ]; then
    MINIMAX_KEY=$(ls /tmp/.minimax_key 2>/dev/null && cat /tmp/.minimax_key || true)
fi

# ---------- 颜色 ----------
RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'; CYN='\033[0;36m'; NC='\033[0m'
step()  { echo -e "${CYN}==> $*${NC}"; }
ok()    { echo -e "    ${GRN}[OK]${NC} $*"; }
warn()  { echo -e "    ${YEL}[!]${NC} $*"; }
fail()  { echo -e "    ${RED}[X]${NC} $*"; exit 1; }

# ---------- 0. 前置检查 ----------
step "0/6 前置检查"

# AppSecret
if [ ! -s /tmp/.mp_app_secret ]; then
    fail "缺少 /tmp/.mp_app_secret。请先 echo '你的AppSecret' > /tmp/.mp_app_secret && chmod 600 /tmp/.mp_app_secret"
fi
ok "AppSecret 已就位"

# 数据目录
mkdir -p "${ARTICLES_DIR}"
ok "articles 目录: ${ARTICLES_DIR}"

# MiniMax key
if [ -z "${MINIMAX_KEY}" ]; then
    warn "找不到 MINIMAX_API_KEY，分析风格时会失败。可 export MINIMAX_KEY=sk-... 或放到 /tmp/.minimax_key"
fi

# ---------- 1. Chroma 健康检查 / 拉起 ----------
step "1/6 检查 Chroma 容器"

if ! command -v docker >/dev/null 2>&1; then
    fail "docker 命令找不到，请先安装 docker"
fi

CHROMA_RUNNING=$(docker ps --format '{{.Names}}' | grep -c '^gzh-chroma$' || true)
if [ "${CHROMA_RUNNING}" -eq 0 ]; then
    warn "Chroma 没在跑，尝试启动"
    if [ -f "${SCRIPT_DIR}/deploy_gzh_chroma.sh" ]; then
        bash "${SCRIPT_DIR}/deploy_gzh_chroma.sh" || warn "deploy 脚本失败，继续往下走（手动启动也行）"
    else
        docker rm -f gzh-chroma 2>/dev/null || true
        docker run -d --name gzh-chroma --restart unless-stopped \
            -p 8100:8000 \
            -v "${CHROMA_DATA}:/chroma/chroma" \
            -e IS_PERSISTED=TRUE \
            -e PERSIST_DIRECTORY=/chroma/chroma \
            -e ANONYMIZED_TELEMETRY=False \
            chromadb/chroma:latest
    fi
    sleep 4
fi

# heartbeat
for i in 1 2 3 4 5; do
    if curl -sS --max-time 3 "${CHROMA_BASE}/api/v2/heartbeat" >/dev/null; then
        ok "Chroma 心跳正常 (${CHROMA_BASE})"
        break
    fi
    warn "等待 Chroma 就绪... ($i/5)"
    sleep 2
done
curl -sS --max-time 3 "${CHROMA_BASE}/api/v2/heartbeat" >/dev/null \
    || fail "Chroma 不可达，请检查 docker ps / 端口映射"

# ---------- 2. 拉公众号发表记录 ----------
step "2/6 拉公众号发表记录"

cd "${PROJECT_DIR}"
python3 "${SCRIPT_DIR}/fetch_mp_via_proxy.py"
ART_COUNT=$(ls "${ARTICLES_DIR}"/*.md 2>/dev/null | wc -l | tr -d ' ')
if [ "${ART_COUNT}" -eq 0 ]; then
    warn "目录下没有任何 markdown，停止"
    exit 1
fi
ok "共 ${ART_COUNT} 篇 markdown"

# ---------- 3. 入库 Chroma ----------
step "3/6 入库 Chroma (collection=${COLLECTION})"

CHROMA_BASE="${CHROMA_BASE}" CHROMA_COLLECTION="${COLLECTION}" \
    ARTICLES_DIR="${ARTICLES_DIR}" \
    python3 "${SCRIPT_DIR}/ingest_to_chroma.py"
ok "入库完成"

# ---------- 4. RAG 检索 + MiniMax-M3 总结风格 ----------
step "4/6 风格分析 (RAG + MiniMax-M3)"

if [ -z "${MINIMAX_KEY}" ]; then
    fail "无 MINIMAX_KEY，跳过风格分析。请 export MINIMAX_KEY=... 后重跑这一步"
fi

CHROMA_BASE="${CHROMA_BASE}" CHROMA_COLLECTION="${COLLECTION}" \
    MINIMAX_KEY="${MINIMAX_KEY}" MINIMAX_HOST="${MINIMAX_HOST}" \
    MINIMAX_MODEL="${MINIMAX_MODEL}" \
    python3 "${SCRIPT_DIR}/analyze_style.py"

# ---------- 5. 输出 ----------
step "5/6 输出"
STYLE_FILE="${CHROMA_DATA}/style_summary.txt"
if [ -f "${STYLE_FILE}" ]; then
    ok "风格总结已保存: ${STYLE_FILE}"
    echo "------------------------------------------------------------"
    head -40 "${STYLE_FILE}"
    echo "------------------------------------------------------------"
else
    warn "未找到 ${STYLE_FILE}"
fi

step "6/6 全部完成"
echo -e "${GRN}Chroma 现有 collection: ${COLLECTION} @ ${CHROMA_BASE}${NC}"
echo -e "${GRN}下次生成文章时会自动检索这套风格${NC}"