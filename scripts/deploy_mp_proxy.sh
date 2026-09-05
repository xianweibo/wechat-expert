#!/bin/bash
# 部署 mp_proxy 端点到阿里云 gzh-expert-app
# 在阿里云服务器上以 gongzhonghao 用户运行

set -e

APP_DIR="${APP_DIR:-/home/gongzhonghao/apps/gzh-expert-git}"

echo "=== 0. 进入项目目录 ==="
cd "${APP_DIR}" || { echo "!! 找不到 ${APP_DIR}"; exit 1; }

echo "=== 1. 备份现有 src/index.ts ==="
cp -v src/index.ts src/index.ts.bak.$(date +%Y%m%d-%H%M%S)

echo "=== 2. 写入新的 mp_proxy.ts ==="
cat > src/mp_proxy.ts << 'PROXY_EOF'
import { Router, Request, Response } from 'express';
import * as https from 'https';
import * as zlib from 'zlib';

const router = Router();

const APP_ID = process.env.WECHAT_APP_ID || 'wx567a639466e247cd';
const APP_SECRET = process.env.WECHAT_APP_SECRET;
const WORKER_SECRET = process.env.BILIBILI_WORKER_SECRET;
const API_BASE = 'https://api.weixin.qq.com/cgi-bin';

function checkAuth(req: Request, res: Response): boolean {
    const got = req.headers['x-worker-secret'];
    if (!WORKER_SECRET || got !== WORKER_SECRET) {
        res.status(401).json({ ok: false, error: 'unauthorized' });
        return false;
    }
    return true;
}

function wechatGet(path: string, qs: Record<string, string> = {}): Promise<any> {
    const params = new URLSearchParams(qs).toString();
    const url = `${API_BASE}${path}${params ? '?' + params : ''}`;
    return new Promise((resolve, reject) => {
        const req = https.get(url, (resp) => {
            const chunks: Buffer[] = [];
            resp.on('data', (c) => chunks.push(c));
            resp.on('end', () => {
                try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))); }
                catch (e) { reject(e); }
            });
        });
        req.on('error', reject);
        req.setTimeout(20000, () => req.destroy(new Error('wechat api timeout')));
    });
}

function wechatPost(path: string, body: any, qs: Record<string, string> = {}): Promise<any> {
    const params = new URLSearchParams(qs).toString();
    const url = `${API_BASE}${path}${params ? '?' + params : ''}`;
    const payload = Buffer.from(JSON.stringify(body), 'utf8');
    return new Promise((resolve, reject) => {
        const req = https.request(
            url,
            { method: 'POST', headers: { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': payload.length, 'Accept-Encoding': 'gzip' } },
            (resp) => {
                const chunks: Buffer[] = [];
                resp.on('data', (c) => chunks.push(c));
                resp.on('end', () => {
                    let buf = Buffer.concat(chunks);
                    if (resp.headers['content-encoding'] === 'gzip') buf = zlib.gunzipSync(buf);
                    try { resolve(JSON.parse(buf.toString('utf8'))); }
                    catch (e) { reject(e); }
                });
            }
        );
        req.on('error', reject);
        req.setTimeout(30000, () => req.destroy(new Error('wechat api timeout')));
        req.write(payload);
        req.end();
    });
}

async function getToken(): Promise<string> {
    if (!APP_SECRET) throw new Error('WECHAT_APP_SECRET not configured');
    const r = await wechatGet('/token', { grant_type: 'client_credential', appid: APP_ID, secret: APP_SECRET });
    if (r.errcode) throw new Error(`token errcode=${r.errcode} ${r.errmsg}`);
    return r.access_token;
}

router.post('/mp-published', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    try {
        const token = await getToken();
        const list = await wechatPost('/freepublish/list', { offset: 0, count: 20, no_content: 1 }, { access_token: token });
        if (list.errcode) return res.status(502).json({ ok: false, error: list.errmsg, errcode: list.errcode });
        res.json({ ok: true, total: list.total_count || (list.news_item || []).length, items: list.news_item || [] });
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

router.post('/mp-article-content', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    const { article_id } = req.body || {};
    if (!article_id) return res.status(400).json({ ok: false, error: 'article_id required' });
    try {
        const token = await getToken();
        const r = await wechatPost('/freepublish/getarticle', { article_id }, { access_token: token });
        if (r.errcode) return res.status(502).json({ ok: false, error: r.errmsg, errcode: r.errcode });
        const news = (r.news_item || [])[0] || {};
        res.json({ ok: true, title: news.title || '', content: news.content || '', url: news.url || '', publish_time: news.update_time || news.create_time || 0 });
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

router.post('/mp-appmsg-list', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    try {
        const token = await getToken();
        const begin = req.body?.begin ?? 0;
        const count = req.body?.count ?? 20;
        const r = await wechatGet('/appmsg/list', { access_token: token, begin: String(begin), count: String(count), type: '1' });
        if (r.errcode) return res.status(502).json({ ok: false, error: r.errmsg, errcode: r.errcode });
        res.json({ ok: true, total: r.total || 0, items: r.appmsg_list || [] });
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

export default router;
PROXY_EOF
echo "    写入 src/mp_proxy.ts 完成"

echo "=== 3. 修改 src/index.ts 挂载 mp_proxy 路由 ==="
# 删除旧 import 行（如果存在）
grep -v "import mpProxy from './mp_proxy';" src/index.ts > src/index.ts.tmp || true
mv src/index.ts.tmp src/index.ts
# 在 import dotenv 后插入
sed -i "/^import dotenv from 'dotenv';/a import mpProxy from './mp_proxy';" src/index.ts
# 在 app.listen 前插入 mount
grep -v "app.use('/api/admin', mpProxy);" src/index.ts > src/index.ts.tmp || true
mv src/index.ts.tmp src/index.ts
sed -i '/^app.listen(/i app.use('"'"'/api/admin'"'"', mpProxy);\n' src/index.ts
echo "    修改 src/index.ts 完成"

echo "=== 4. 重建并重启容器 ==="
docker compose up -d --build app

echo "=== 5. 等待启动 ==="
sleep 8

echo "=== 6. 验证新端点 ==="
SECRET=$(grep '^BILIBILI_WORKER_SECRET=' .env | cut -d'=' -f2- | tr -d '"' || true)
if [ -z "${SECRET}" ]; then
    SECRET=$(sudo grep '^BILIBILI_WORKER_SECRET=' /home/gongzhonghao/apps/gzh-expert-git/.env 2>/dev/null | cut -d'=' -f2- | tr -d '"' || true)
fi
echo "Worker Secret: ${SECRET:0:8}..."

echo
echo "  -> 测试 mp-published 端点："
curl -s -X POST http://127.0.0.1:39800/api/admin/mp-published \
    -H "X-Worker-Secret: ${SECRET}" \
    -H "Content-Type: application/json" \
    -d '{}' | head -c 500
echo
echo
echo "🎉 部署完成。新端点："
echo "   POST http://8.134.248.11:39800/api/admin/mp-published"
echo "   POST http://8.134.248.11:39800/api/admin/mp-article-content"
echo "   POST http://8.134.248.11:39800/api/admin/mp-appmsg-list"
echo "   鉴权 header: X-Worker-Secret: \${BILIBILI_WORKER_SECRET}"