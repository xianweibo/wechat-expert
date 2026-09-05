# 阿里云上粘贴运行这条命令：
# (从 ssh gongzhonghao@8.134.248.11 进入后)

cat > /tmp/deploy_mp_proxy.sh << 'OUTER_EOF'
#!/bin/bash
set -e
APP_DIR="${APP_DIR:-/home/gongzhonghao/apps/gzh-expert-git}"
cd "${APP_DIR}" || { echo "!! 找不到 ${APP_DIR}"; exit 1; }
echo "[1/6] 备份 src/index.ts"
cp -v src/index.ts src/index.ts.bak.$(date +%Y%m%d-%H%M%S)
echo "[2/6] 写 src/mp_proxy.ts"
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
echo "    -> $(wc -l < src/mp_proxy.ts) lines"
echo "[3/6] 改 src/index.ts 挂载路由"
grep -v "import mpProxy from './mp_proxy';" src/index.ts > src/index.ts.tmp && mv src/index.ts.tmp src/index.ts || true
sed -i "/^import dotenv from 'dotenv';/a import mpProxy from './mp_proxy';" src/index.ts
grep -v "app.use('/api/admin', mpProxy);" src/index.ts > src/index.ts.tmp && mv src/index.ts.tmp src/index.ts || true
sed -i '0,/^app.listen(/s//app.use('"'"'\/api\/admin'"'"', mpProxy);\n\napp.listen(/' src/index.ts
echo "    -> diff:"
diff -u src/index.ts.bak.* src/index.ts 2>&1 | tail -20 || true
echo "[4/6] 重建并重启 app 容器"
docker compose up -d --build app
echo "[5/6] 等待启动"
sleep 10
echo "[6/6] 验证新端点"
SECRET=$(grep '^BILIBILI_WORKER_SECRET=' .env | cut -d'=' -f2- | sed 's/^"//;s/"$//' | tr -d ' ')
echo "  Worker Secret: ${SECRET:0:8}..."
echo "  -> mp-published:"
curl -s -X POST http://127.0.0.1:39800/api/admin/mp-published -H "X-Worker-Secret: ${SECRET}" -H "Content-Type: application/json" -d '{}' | head -c 400
echo ""
echo "🎉 部署完成！"
OUTER_EOF
chmod +x /tmp/deploy_mp_proxy.sh
echo "脚本已写入 /tmp/deploy_mp_proxy.sh ($(wc -l < /tmp/deploy_mp_proxy.sh) 行)"
echo "现在执行："
bash /tmp/deploy_mp_proxy.sh