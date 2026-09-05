import { Router, Request, Response } from 'express';
import * as https from 'https';
import * as http from 'http';
import * as zlib from 'zlib';
import { URL } from 'url';
import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';

const router = Router();

const APP_ID = process.env.WECHAT_APP_ID || 'wx567a639466e247cd';
const API_BASE = 'https://api.weixin.qq.com/cgi-bin';

// 注意：本模块在 index.ts 的 dotenv.config() 之前被 import（ESM import 提升），
// 模块顶层读 process.env 会在 .env 加载前取到空值，密钥类配置必须在调用时读取
function getAppSecret(): string {
    return (process.env.WECHAT_APP_SECRET || '').trim();
}

function getWorkerSecret(): string {
    return (process.env.BILIBILI_WORKER_SECRET || '').trim();
}

function getQuerySecret(req: Request): string {
    // GET 请求 Express 已自动解析 req.query
    if (req.query?.secret) return String(req.query.secret);
    if (req.query?.token) return String(req.query.token);
    // 兜底：从原始 URL 解析（POST 请求的 query string）
    try {
        const u = new URL(req.url, 'http://x');
        return u.searchParams.get('secret') || u.searchParams.get('token') || '';
    } catch {
        return '';
    }
}

function checkAuth(req: Request, res: Response): boolean {
    // 优先 header，其次 query string（方便浏览器直接访问）
    const headerSecret = (req.headers['x-worker-secret'] || '').toString().trim();
    const querySecret = getQuerySecret(req).trim();
    const got = headerSecret || querySecret;
    const workerSecret = getWorkerSecret();
    if (!workerSecret || !got || got !== workerSecret) {
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
                try {
                    resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')));
                } catch (e) {
                    reject(e);
                }
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
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json; charset=utf-8',
                    'Content-Length': payload.length,
                    'Accept-Encoding': 'gzip',
                },
            },
            (resp) => {
                const chunks: Buffer[] = [];
                resp.on('data', (c) => chunks.push(c));
                resp.on('end', () => {
                    let buf = Buffer.concat(chunks);
                    if (resp.headers['content-encoding'] === 'gzip') {
                        buf = zlib.gunzipSync(buf);
                    }
                    try {
                        resolve(JSON.parse(buf.toString('utf8')));
                    } catch (e) {
                        reject(e);
                    }
                });
            }
        );
        req.on('error', reject);
        req.setTimeout(30000, () => req.destroy(new Error('wechat api timeout')));
        req.write(payload);
        req.end();
    });
}

// access_token 进程内缓存：微信 token 有效期 7200s，且获取接口有每日配额，
// 之前每次请求都重新取 token，批量操作（如 mp-articles-all）极易打爆配额
let tokenCache: { token: string; expiresAt: number } | null = null;

async function getToken(): Promise<string> {
    if (tokenCache && Date.now() < tokenCache.expiresAt) {
        return tokenCache.token;
    }
    const appSecret = getAppSecret();
    if (!appSecret) throw new Error('WECHAT_APP_SECRET not configured');
    const r = await wechatGet('/token', {
        grant_type: 'client_credential',
        appid: APP_ID,
        secret: appSecret,
    });
    if (r.errcode) throw new Error(`token errcode=${r.errcode} ${r.errmsg}`);
    // 提前 5 分钟过期，避免边界时刻拿到已失效 token
    const expiresIn = (r.expires_in || 7200) - 300;
    tokenCache = { token: r.access_token, expiresAt: Date.now() + expiresIn * 1000 };
    return r.access_token;
}

router.post('/mp-published', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    try {
        const token = await getToken();
        const list = await wechatPost(
            '/draft/batchget',
            { offset: 0, count: 20, no_content: 1 },
            { access_token: token }
        );
        if (list.errcode) {
            return res.status(502).json({ ok: false, error: list.errmsg, errcode: list.errcode });
        }
        const items = (list.item || []).map((it: any) => {
            const ni = ((it.content || {}).news_item || [])[0] || {};
            return {
                media_id: it.media_id,
                title: ni.title || '',
                author: ni.author || '',
                digest: ni.digest || '',
                url: ni.url || '',
                publish_time: ni.update_time || it.update_time || 0,
            };
        });
        res.json({
            ok: true,
            total: list.total_count || items.length,
            items,
            token_expires_in: 7200,
        });
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

router.post('/mp-draft-add', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    const { title, content, author, digest, content_source_url, thumb_media_id } =
        req.body || {};
    if (!title || !content) {
        return res.status(400).json({ ok: false, error: 'title and content required' });
    }
    try {
        const token = await getToken();
        const article: any = { title, content };
        if (author) article.author = author;
        if (digest) article.digest = digest;
        if (content_source_url) article.content_source_url = content_source_url;
        if (thumb_media_id) article.thumb_media_id = thumb_media_id;
        const r = await wechatPost(
            '/draft/add',
            { articles: [article] },
            { access_token: token }
        );
        if (r.errcode) {
            return res.status(502).json({ ok: false, error: r.errmsg, errcode: r.errcode });
        }
        res.json({ ok: true, media_id: r.media_id });
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

router.post('/mp-draft-delete', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    const { media_id } = req.body || {};
    if (!media_id) {
        return res.status(400).json({ ok: false, error: 'media_id required' });
    }
    try {
        const token = await getToken();
        const r = await wechatPost(
            '/draft/delete',
            { media_id },
            { access_token: token }
        );
        if (r.errcode) {
            return res.status(502).json({ ok: false, error: r.errmsg, errcode: r.errcode });
        }
        res.json({ ok: true });
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

router.post('/mp-material-image-add', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    const { image_url } = req.body || {};
    if (!image_url) {
        return res.status(400).json({ ok: false, error: 'image_url required' });
    }
    try {
        const token = await getToken();
        const fetched = await fetchRemote(image_url);
        const boundary = '----mpproxy' + crypto.randomBytes(12).toString('hex');
        const ext = (fetched.type.split('/')[1] || 'jpg').replace(/[^a-z0-9]/gi, '');
        const filename = 'cover.' + ext;
        const head1 = Buffer.from(
            `--${boundary}\r\n` +
            `Content-Disposition: form-data; name="media"; filename="${filename}"\r\n` +
            `Content-Type: ${fetched.type}\r\n\r\n`
        );
        const head2 = Buffer.from(
            `\r\n--${boundary}\r\n` +
            `Content-Disposition: form-data; name="type"\r\n\r\n` +
            `image\r\n--${boundary}--\r\n`
        );
        const body = Buffer.concat([head1, fetched.buf, head2]);
        const url = `https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=${token}&type=image`;
        const uploadRes: any = await new Promise((resolve, reject) => {
            const u = new URL(url);
            const req2 = https.request(
                {
                    method: 'POST',
                    hostname: u.hostname,
                    path: u.pathname + u.search,
                    headers: {
                        'Content-Type': 'multipart/form-data; boundary=' + boundary,
                        'Content-Length': String(body.length),
                    },
                },
                (resp: any) => {
                    const chunks: Buffer[] = [];
                    resp.on('data', (c: Buffer) => chunks.push(c));
                    resp.on('end', () => {
                        try {
                            resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')));
                        } catch (e) {
                            reject(e);
                        }
                    });
                }
            );
            req2.on('error', reject);
            req2.write(body);
            req2.end();
        });
        if (uploadRes.errcode) {
            return res.status(502).json({ ok: false, error: uploadRes.errmsg, errcode: uploadRes.errcode });
        }
        res.json({ ok: true, media_id: uploadRes.media_id, url: uploadRes.url });
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

function fetchRemote(url: string, redirectsLeft = 3): Promise<{ buf: Buffer; type: string }> {
    return new Promise((resolve, reject) => {
        const full = url.startsWith('http') ? url : 'https:' + url;
        const mod = full.startsWith('https') ? https : http;
        mod.get(full, (r: any) => {
            if (r.statusCode && r.statusCode >= 300 && r.statusCode < 400 && r.headers.location) {
                if (redirectsLeft <= 0) return reject(new Error('too many redirects'));
                r.resume();
                return resolve(fetchRemote(r.headers.location, redirectsLeft - 1));
            }
            const chunks: Buffer[] = [];
            r.on('data', (c: Buffer) => chunks.push(c));
            r.on('end', () =>
                resolve({ buf: Buffer.concat(chunks), type: r.headers['content-type'] || 'image/jpeg' })
            );
        }).on('error', reject);
    });
}

router.post('/mp-articles-all', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    try {
        const token = await getToken();
        const all: any[] = [];
        let offset = 0;
        const count = 20;
        let total = 0;
        while (true) {
            const r = await wechatPost(
                '/draft/batchget',
                { offset, count, no_content: 0 },
                { access_token: token }
            );
            if (r.errcode) {
                return res.status(502).json({ ok: false, error: r.errmsg, errcode: r.errcode });
            }
            total = r.total_count || total;
            const items = r.item || [];
            all.push(...items);
            offset += items.length;
            if (!items.length || items.length < count || offset >= total) break;
        }
        const flat: any[] = [];
        for (const it of all) {
            for (const ni of ((it.content || {}).news_item || [])) {
                flat.push({
                    media_id: it.media_id,
                    title: ni.title || '',
                    author: ni.author || '',
                    digest: ni.digest || '',
                    content: ni.content || '',
                    content_source_url: ni.content_source_url || '',
                    url: ni.url || '',
                    thumb_url: ni.thumb_url || '',
                    publish_time: ni.update_time || it.update_time || 0,
                });
            }
        }
        res.json({ ok: true, total, articles: flat });
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

router.post('/mp-article-content', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    const { article_id } = req.body || {};
    if (!article_id) {
        return res.status(400).json({ ok: false, error: 'article_id required' });
    }
    try {
        const token = await getToken();
        const r = await wechatPost(
            '/draft/get',
            { media_id: article_id },
            { access_token: token }
        );
        if (r.errcode) {
            return res.status(502).json({ ok: false, error: r.errmsg, errcode: r.errcode });
        }
        const ni = ((r.news_item || [])[0]) || {};
        res.json({
            ok: true,
            title: ni.title || '',
            content: ni.content || '',
            url: ni.url || '',
            publish_time: ni.update_time || r.update_time || 0,
            digest: ni.digest || '',
        });
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
        const r = await wechatGet('/appmsg/list', {
            access_token: token,
            begin: String(begin),
            count: String(count),
            type: '1',
        });
        if (r.errcode) {
            return res.status(502).json({ ok: false, error: r.errmsg, errcode: r.errcode });
        }
        res.json({ ok: true, total: r.total || 0, items: r.appmsg_list || [] });
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

const BILI_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

function biliGetJson(url: string, cookie: string): Promise<any> {
    return new Promise((resolve, reject) => {
        const u = new URL(url);
        const mod = u.protocol === 'https:' ? https : http;
        const req = mod.get(
            url,
            {
                headers: {
                    'Cookie': cookie,
                    'User-Agent': BILI_UA,
                    'Referer': 'https://space.bilibili.com/',
                    'Accept-Encoding': 'gzip',
                },
            },
            (resp: any) => {
                const chunks: Buffer[] = [];
                resp.on('data', (c: Buffer) => chunks.push(c));
                resp.on('end', () => {
                    let buf = Buffer.concat(chunks);
                    if (resp.headers['content-encoding'] === 'gzip') buf = zlib.gunzipSync(buf);
                    try {
                        resolve(JSON.parse(buf.toString('utf8')));
                    } catch (e) {
                        reject(new Error('bili json parse fail: ' + (e as Error).message + ' body=' + buf.toString('utf8').substring(0, 200)));
                    }
                });
            }
        );
        req.on('error', reject);
        req.setTimeout(20000, () => req.destroy(new Error('bili api timeout')));
    });
}

function sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function biliDynamicVideos(upUid: number, sessdata: string, biliJct: string): Promise<any[]> {
    const cookie = `SESSDATA=${sessdata}; bili_jct=${biliJct}`;
    const urls = [
        `https://api.bilibili.com/x/space/wbi/arc/search?mid=${upUid}&pn=1&ps=20&order=pubdate&jsonp=jsonp`,
        `https://api.bilibili.com/x/space/arc/search?mid=${upUid}&pn=1&ps=20&order=pubdate&jsonp=jsonp`,
    ];
    let lastErr = '';
    for (const url of urls) {
        try {
            const r = await biliGetJson(url, cookie);
            if (r.code === 0 && r.data && r.data.list && r.data.list.vlist) {
                const vlist: any[] = r.data.list.vlist;
                return vlist.map((v: any) => ({
                    bvid: v.bvid,
                    title: v.title,
                    cover: v.pic || '',
                    duration: v.length || '',
                    pub_ts: v.created || 0,
                }));
            }
            lastErr = 'code=' + r.code + ' msg=' + r.message;
        } catch (e: any) {
            lastErr = e.message;
        }
        await sleep(2000);
    }
    throw new Error('bili search fail: ' + lastErr);
}

async function biliVideoDetail(bvid: string, sessdata: string, biliJct: string): Promise<any> {
    const cookie = `SESSDATA=${sessdata}; bili_jct=${biliJct}`;
    const url = `https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`;
    const r = await biliGetJson(url, cookie);
    if (r.code !== 0) {
        throw new Error('bili view fail code=' + r.code + ' msg=' + r.message);
    }
    return r.data;
}

router.post('/bilibili-check-bvids', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    console.log('[bilibili-check-bvids] content-type:', req.headers['content-type'], 'body keys:', req.body ? Object.keys(req.body) : 'none', 'rawBody:', JSON.stringify(req.body).substring(0, 200));
    const bvids: string[] = Array.isArray(req.body?.bvids) ? req.body.bvids : [];
    if (bvids.length === 0) {
        return res.status(400).json({ ok: false, error: 'bvids array required' });
    }
    if (bvids.length > 20) {
        return res.status(400).json({ ok: false, error: 'bvids length must be <= 20' });
    }
    const sessdata = process.env.BILIBILI_SESSDATA;
    const biliJct = process.env.BILIBILI_BILI_JCT;
    if (!sessdata || !biliJct) {
        return res.status(500).json({ ok: false, error: 'BILIBILI_SESSDATA / BILIBILI_BILI_JCT not set in env' });
    }
    try {
        const results: any[] = [];
        for (const bvid of bvids) {
            await sleep(2500);
            try {
                const detail = await biliVideoDetail(bvid, sessdata, biliJct);
                const rights = (detail && detail.rights) || {};
                const isCharged = rights.is_charging_arc === 1 || rights.ugc_pay === 1;
                results.push({
                    bvid,
                    title: detail ? detail.title : null,
                    pubdate: detail ? detail.pubdate : null,
                    duration: detail ? detail.duration : null,
                    desc: detail ? detail.desc : null,
                    pic: detail ? detail.pic : null,
                    cid: detail ? detail.cid : null,
                    is_charged: isCharged,
                    is_charging_arc: rights.is_charging_arc || 0,
                    ugc_pay: rights.ugc_pay || 0,
                    owner: detail ? detail.owner : null,
                });
            } catch (e: any) {
                results.push({ bvid, error: e.message });
            }
        }
        res.json({ ok: true, results });
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

router.post('/bilibili-latest-charged', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    const upUid = Number(req.body?.up_uid) || 290663424;
    const limit = Math.min(Number(req.body?.limit) || 10, 30);
    const sessdata = process.env.BILIBILI_SESSDATA;
    const biliJct = process.env.BILIBILI_BILI_JCT;
    if (!sessdata || !biliJct) {
        return res.status(500).json({ ok: false, error: 'BILIBILI_SESSDATA / BILIBILI_BILI_JCT not set in env' });
    }
    try {
        const videos = await biliDynamicVideos(upUid, sessdata, biliJct);
        const scanned: any[] = [];
        for (let i = 0; i < Math.min(videos.length, limit); i++) {
            const v = videos[i];
            await sleep(2000);
            const detail = await biliVideoDetail(v.bvid, sessdata, biliJct);
            const rights = (detail && detail.rights) || {};
            const isCharged = rights.is_charging_arc === 1 || rights.ugc_pay === 1;
            scanned.push({
                bvid: v.bvid,
                title: v.title,
                duration: v.duration,
                pub_ts: v.pub_ts,
                is_charged: isCharged,
                is_charging_arc: rights.is_charging_arc || 0,
                ugc_pay: rights.ugc_pay || 0,
                detail_title: detail ? detail.title : null,
                stat: detail ? detail.stat : null,
            });
            if (isCharged) {
                return res.json({
                    ok: true,
                    target: {
                        bvid: v.bvid,
                        title: detail ? detail.title : v.title,
                        description: detail ? detail.desc : '',
                        pubdate: v.pub_ts,
                        duration: v.duration,
                        cover: v.cover,
                        url: `https://www.bilibili.com/video/${v.bvid}`,
                    },
                    scanned,
                    scanned_count: scanned.length,
                });
            }
        }
        res.json({ ok: true, target: null, scanned, scanned_count: scanned.length });
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

async function biliSubtitle(bvid: string, cid: number, sessdata: string, biliJct: string): Promise<{
    subtitleText: string;
    subtitles: any[];
    needLoginSubtitle: boolean;
    isUpowerExclusive: boolean;
    isUgcPayPreview: boolean;
    loginMid: number;
}> {
    const cookie = `SESSDATA=${sessdata}; bili_jct=${biliJct}`;
    const url = `https://api.bilibili.com/x/player/v2?bvid=${bvid}&cid=${cid}`;
    const r = await biliGetJson(url, cookie);
    if (r.code !== 0) {
        throw new Error('bili player/v2 fail code=' + r.code + ' msg=' + r.message);
    }
    const data = r.data || {};
    const subtitleInfo = data.subtitle || {};
    const subtitles = subtitleInfo.subtitles || [];
    const needLoginSubtitle = !!data.need_login_subtitle;
    const isUpowerExclusive = !!data.is_upower_exclusive;
    const isUgcPayPreview = !!data.is_ugc_pay_preview;
    const loginMid = data.login_mid || 0;

    if (subtitles.length === 0) {
        return { subtitleText: '', subtitles: [], needLoginSubtitle, isUpowerExclusive, isUgcPayPreview, loginMid };
    }

    // 优先选 AI 字幕（ai_type=1），否则选第一个
    const subInfo = subtitles.find((s: any) => s.ai_type === 1) || subtitles[0];
    let subUrl: string = subInfo.subtitle_url || '';
    if (!subUrl) {
        return { subtitleText: '', subtitles, needLoginSubtitle, isUpowerExclusive, isUgcPayPreview, loginMid };
    }

    // 补全协议（B 站字幕 URL 常是 //aisubtitle.hdslb.com/...）
    if (subUrl.startsWith('//')) subUrl = 'https:' + subUrl;

    // 下载字幕 JSON
    const subData = await biliGetJson(subUrl, cookie);
    const body = subData.body || [];
    const lines: string[] = [];
    for (const item of body) {
        const text = (item.content || item.i || '').trim();
        if (text) lines.push(text);
    }
    return { subtitleText: lines.join('\n'), subtitles, needLoginSubtitle, isUpowerExclusive, isUgcPayPreview, loginMid };
}

router.post('/bilibili-subtitle', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    const bvid: string = req.body?.bvid;
    const cid: number = Number(req.body?.cid);
    if (!bvid || !cid) {
        return res.status(400).json({ ok: false, error: 'bvid and cid required' });
    }
    const sessdata = process.env.BILIBILI_SESSDATA;
    const biliJct = process.env.BILIBILI_BILI_JCT;
    if (!sessdata || !biliJct) {
        return res.status(500).json({ ok: false, error: 'BILIBILI_SESSDATA / BILIBILI_BILI_JCT not set in env' });
    }
    try {
        await sleep(2500); // 风控间隔 ≥ 2s
        const result = await biliSubtitle(bvid, cid, sessdata, biliJct);
        res.json({
            ok: true,
            bvid,
            cid,
            subtitle_text: result.subtitleText,
            subtitle_count: result.subtitles.length,
            need_login_subtitle: result.needLoginSubtitle,
            is_upower_exclusive: result.isUpowerExclusive,
            is_ugc_pay_preview: result.isUgcPayPreview,
            login_mid: result.loginMid,
            subtitles: result.subtitles,
        });
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

// ============================================================
// B 站二维码登录 (供 NAS 管理面板调用)
// ============================================================

const BILI_PASS_API = 'https://passport.bilibili.com/x/passport-login/web/qrcode';
const BILI_UA2 = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

interface BiliQrcodeGenerateResp {
    ok: boolean;
    qrcode_key?: string;
    qrcode_url?: string;
    error?: string;
}

router.post('/bilibili-qrcode-generate', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    try {
        const r = await fetch(`${BILI_PASS_API}/generate`, {
            headers: { 'User-Agent': BILI_UA2 },
        });
        const data: any = await r.json();
        if (data.code !== 0) {
            res.status(500).json({ ok: false, error: `generate fail code=${data.code} msg=${data.message}` });
            return;
        }
        const qrcode_key = data.data.qrcode_key;
        const qrcode_url = data.data.url; // https://passport.bilibili.com/h5-app/passport/login/scan?qrcode_key=...
        res.json({ ok: true, qrcode_key, qrcode_url });
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

// [fix-2026-09-03] 提取 poll 逻辑为共享函数：避免 body parser SyntaxError 时返回 HTML 错误页
async function handleQrcodePoll(qrcodeKey: string, res: Response): Promise<void> {
    if (!qrcodeKey) {
        res.status(400).json({ ok: false, error: 'qrcode_key required' });
        return;
    }
    try {
        const r = await fetch(`${BILI_PASS_API}/poll?qrcode_key=${encodeURIComponent(qrcodeKey)}`, {
            headers: { 'User-Agent': BILI_UA2 },
        });
        const data: any = await r.json();
        const code = data.data?.code;

        // code 状态：
        // 0: 登录成功 (data.refresh_token, data.timestamp, data.url 含 SESSDATA)
        // 86101: 未扫码
        // 86090: 已扫码未确认
        // 86038: 二维码已过期
        // 86100: 其他错误

        if (code === 0) {
            // 登录成功，从 data.url 提取 cookie
            const loginUrl = data.data.url || '';
            console.log(`[qrcode-poll] ✅ 登录成功 code=0`);
            console.log(`[qrcode-poll] loginUrl 长度: ${loginUrl.length}`);
            console.log(`[qrcode-poll] loginUrl 前 100 字符: ${loginUrl.substring(0, 100)}`);
            console.log(`[qrcode-poll] loginUrl 后 100 字符: ${loginUrl.substring(Math.max(0, loginUrl.length - 100))}`);

            // 打印 B 站返回的完整 data.data（看 url 是什么字段、嵌套几层）
            console.log(`[qrcode-poll] data.data keys: ${Object.keys(data.data || {}).join(',')}`);
            console.log(`[qrcode-poll] data.data.url 类型: ${typeof loginUrl}, 是否字符串: ${typeof loginUrl === 'string'}`);

            let sessdata = '';
            let biliJct = '';
            let biliTicket = '';
            let dedeUserId = '';

            try {
                const u = new URL(loginUrl);
                sessdata = u.searchParams.get('SESSDATA') || '';
                biliJct = u.searchParams.get('bili_jct') || '';
                biliTicket = u.searchParams.get('bili_ticket') || '';
                dedeUserId = u.searchParams.get('DedeUserID') || '';
                console.log(`[qrcode-poll] URL 解析成功`);
            } catch (parseErr: any) {
                console.log(`[qrcode-poll] URL 解析失败: ${parseErr.message}，用正则 fallback`);
                // fallback: 正则提取
                const sessMatch = loginUrl.match(/[?&]SESSDATA=([^&]+)/);
                const jctMatch = loginUrl.match(/[?&]bili_jct=([^&]+)/);
                const ticketMatch = loginUrl.match(/[?&]bili_ticket=([^&]+)/);
                const dedeMatch = loginUrl.match(/[?&]DedeUserID=([^&]+)/);
                if (sessMatch) sessdata = decodeURIComponent(sessMatch[1]);
                if (jctMatch) biliJct = jctMatch[1];
                if (ticketMatch) biliTicket = decodeURIComponent(ticketMatch[1]);
                if (dedeMatch) dedeUserId = dedeMatch[1];
            }

            console.log(`[qrcode-poll] 解析结果: sessdata.length=${sessdata.length}, biliJct.length=${biliJct.length}, biliTicket.length=${biliTicket.length}, dedeUserId='${dedeUserId}'`);
            console.log(`[qrcode-poll] sessdata 前 30: ${sessdata.substring(0, 30)}`);

            if (!sessdata || !biliJct) {
                console.error(`[qrcode-poll] ❌ 解析失败：sessdata 或 bili_jct 为空！原始 url: ${loginUrl}`);
                console.error(`[qrcode-poll] 完整 data.data: ${JSON.stringify(data.data).substring(0, 500)}`);
            }

            res.json({
                ok: true,
                status: 'success',
                message: '登录成功',
                sessdata,
                bili_jct: biliJct,
                bili_ticket: biliTicket,
                dede_user_id: dedeUserId,
            });
        } else if (code === 86101) {
            res.json({ ok: true, status: 'waiting', message: '等待扫码' });
        } else if (code === 86090) {
            res.json({ ok: true, status: 'scanned', message: '已扫码，请在手机上确认' });
        } else if (code === 86038) {
            res.json({ ok: true, status: 'expired', message: '二维码已过期，请重新生成' });
        } else {
            res.json({ ok: true, status: 'unknown', code, message: data.data?.message || '未知状态' });
        }
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
}

// 原端点保留：依赖 req.body.qrcode_key。NAS 调用方应改用 path 参数版本避免 body-parser SyntaxError
router.post('/bilibili-qrcode-poll', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    return handleQrcodePoll(req.body?.qrcode_key, res);
});

// [fix-2026-09-03] 新端点：path 参数版，完全绕过 body-parser（避免 NAS 端 urllib 触发 SyntaxError）
router.post('/bilibili-qrcode-poll/:qrcode_key', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    return handleQrcodePoll(req.params.qrcode_key, res);
});

interface WriteEnvResult {
  ok: boolean;
  env_path?: string;
  backup?: string;
  error?: string;
}

async function writeBiliEnv(
  sessdata: string,
  biliJct: string,
  biliTicket: string
): Promise<WriteEnvResult> {
    if (!sessdata || !biliJct) {
        return { ok: false, error: 'sessdata and bili_jct required' };
    }
    try {
        // 找到 .env 路径
        const envPaths = [
            '/home/gongzhonghao/apps/gzh-expert-git/.env',
            '/app/.env',
            path.join(process.cwd(), '.env'),
        ];
        let envPath = '';
        for (const p of envPaths) {
            if (fs.existsSync(p)) {
                envPath = p;
                break;
            }
        }
        if (!envPath) {
            return { ok: false, error: '.env not found in known locations' };
        }

        // 备份
        const bakPath = envPath + '.bak.' + new Date().toISOString().replace(/[-:T]/g, '').substring(0, 15);
        fs.copyFileSync(envPath, bakPath);

        // 替换（逐键统计：.env 里不存在的键追加到文件尾，避免静默无操作）
        let content = fs.readFileSync(envPath, 'utf8');
        const values: Record<string, string> = {
            BILIBILI_SESSDATA: sessdata,
            BILIBILI_BILI_JCT: biliJct,
        };
        if (biliTicket) values.BILIBILI_BILITICKET = biliTicket;

        const appended: string[] = [];
        for (const [key, val] of Object.entries(values)) {
            const re = new RegExp(`^${key}=.*$`, 'm');
            if (re.test(content)) {
                content = content.replace(re, `${key}=${val}`);
            } else {
                appended.push(`${key}=${val}`);
            }
        }
        if (appended.length) {
            if (!content.endsWith('\n')) content += '\n';
            content += '\n# 由 bilibili-qrcode 扫码登录自动追加\n' + appended.join('\n') + '\n';
            console.log(`[qrcode-write-env] .env 缺少 ${appended.length} 个键，已追加: ${appended.map((l) => l.split('=')[0]).join(',')}`);
        }
        fs.writeFileSync(envPath, content, 'utf8');

        console.log(`[qrcode-write-env] .env 已更新: ${envPath} (备份 ${bakPath})`);
        return { ok: true, env_path: envPath, backup: bakPath };
    } catch (e: any) {
        return { ok: false, error: e.message };
    }
}

router.post('/bilibili-qrcode-write-env', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    const sessdata: string = req.body?.sessdata || '';
    const biliJct: string = req.body?.bili_jct || '';
    const biliTicket: string = req.body?.bili_ticket || '';

    console.log(`[qrcode-write-env] 收到请求: sessdata.length=${sessdata.length}, bili_jct.length=${biliJct.length}, bili_ticket.length=${biliTicket.length}`);
    console.log(`[qrcode-write-env] req.body keys: ${req.body ? Object.keys(req.body).join(',') : 'undefined'}`);

    const result = await writeBiliEnv(sessdata, biliJct, biliTicket);
    if (!result.ok) {
        const status = result.error?.includes('not found') ? 500 : 400;
        return res.status(status).json({ ok: false, error: result.error });
    }

    res.json({
        ok: true,
        message: '.env 已更新，请重启容器加载新 cookie',
        env_path: result.env_path,
        backup: result.backup,
        next_step: 'docker compose restart gzh-expert-app',
    });
});

// ============================================================
// B 站无头扫码登录 (Playwright 容器内运行, 按需启动)
// ============================================================

// 进程内状态：扫码会话最近结果
interface QrcodeSessionState {
    status: 'idle' | 'starting' | 'waiting_scan' | 'success' | 'failed';
    started_at?: number;
    finished_at?: number;
    error?: string;
    sessdata?: string;
    bili_jct?: string;
    bili_ticket?: string;
    dede_user_id?: string;
    qrcode_png_base64?: string;
}

let qrcodeSessionState: QrcodeSessionState = { status: 'idle' };

router.post('/bilibili-qrcode-headless-start', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;

    if (qrcodeSessionState.status === 'starting' || qrcodeSessionState.status === 'waiting_scan') {
        return res.json({
            ok: true,
            status: qrcodeSessionState.status,
            message: '已有扫码会话在运行中，请等待当前会话结束',
            started_at: qrcodeSessionState.started_at,
            has_qrcode: !!qrcodeSessionState.qrcode_png_base64,
        });
    }

    console.log('[qrcode-bot] 收到扫码请求，启动无头浏览器...');
    qrcodeSessionState = { status: 'starting', started_at: Date.now() };

    // 异步执行，不等完成
    (async () => {
        try {
            const { runBiliQrcodeLogin } = await import('./bilibili_qrcode_bot');
            const result = await runBiliQrcodeLogin({
                onQrcodeReady: async (pngBase64) => {
                    console.log(`[qrcode-bot] 二维码已生成 (${pngBase64.length} bytes base64)`);
                    qrcodeSessionState.status = 'waiting_scan';
                    qrcodeSessionState.qrcode_png_base64 = pngBase64;
                },
            });

            console.log(`[qrcode-bot] 完成: success=${result.success}`);
            qrcodeSessionState.finished_at = Date.now();
            qrcodeSessionState.qrcode_png_base64 = result.qrcode_png_base64 || qrcodeSessionState.qrcode_png_base64;

            if (result.success && result.sessdata && result.bili_jct) {
                qrcodeSessionState.status = 'success';
                qrcodeSessionState.sessdata = result.sessdata;
                qrcodeSessionState.bili_jct = result.bili_jct;
                qrcodeSessionState.bili_ticket = result.bili_ticket || '';
                qrcodeSessionState.dede_user_id = result.dede_user_id || '';

                // 自动写 .env
                const writeResult = await writeBiliEnv(result.sessdata, result.bili_jct, result.bili_ticket || '');
                if (writeResult.ok) {
                    console.log(`[qrcode-bot] ✅ .env 已自动更新 (${writeResult.env_path})`);
                    console.log(`[qrcode-bot] ⚠️ 请执行: docker compose restart gzh-expert-app`);
                } else {
                    console.error(`[qrcode-bot] ❌ 写 .env 失败: ${writeResult.error}`);
                }
            } else {
                qrcodeSessionState.status = 'failed';
                qrcodeSessionState.error = result.error || '未知错误';
                console.error(`[qrcode-bot] ❌ 失败: ${result.error}`);
            }
        } catch (e: any) {
            console.error(`[qrcode-bot] 异常: ${e.message}`);
            qrcodeSessionState.status = 'failed';
            qrcodeSessionState.error = e.message;
            qrcodeSessionState.finished_at = Date.now();
        }
    })();

    res.json({ ok: true, status: 'starting', message: '扫码会话启动中，请稍候...' });
});

router.get('/bilibili-qrcode-headless-status', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    res.json({
        ok: true,
        status: qrcodeSessionState.status,
        started_at: qrcodeSessionState.started_at,
        finished_at: qrcodeSessionState.finished_at,
        has_qrcode: !!qrcodeSessionState.qrcode_png_base64,
        qrcode_png_base64: qrcodeSessionState.qrcode_png_base64,
        // 成功时不暴露完整 cookie，只返回长度 + 是否成功
        success: qrcodeSessionState.status === 'success' ? {
            sessdata_length: (qrcodeSessionState.sessdata || '').length,
            bili_jct_length: (qrcodeSessionState.bili_jct || '').length,
            bili_ticket_length: (qrcodeSessionState.bili_ticket || '').length,
            dede_user_id: qrcodeSessionState.dede_user_id,
        } : null,
        error: qrcodeSessionState.error,
    });
});

const resetQrcodeSession = async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    qrcodeSessionState = {
        status: 'idle',
        started_at: 0,
    };
    console.log('[qrcode-headless-reset] 扫码会话状态已重置');
    res.json({ ...qrcodeSessionState, message: '扫码会话已重置（idle）' });
};

router.post('/bilibili-qrcode-headless-reset', resetQrcodeSession);
router.get('/bilibili-qrcode-headless-reset', resetQrcodeSession);

router.get('/bilibili-session-status', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;
    const sessdata = (process.env.BILIBILI_SESSDATA || '').trim();
    const biliJct = (process.env.BILIBILI_BILI_JCT || '').trim();

    if (!sessdata || !biliJct) {
        return res.json({
            ok: false,
            status: 'no_config',
            message: 'SESSDATA 或 bili_jct 未配置',
        });
    }

    try {
        const r = await fetch('https://api.bilibili.com/x/web-interface/nav', {
            headers: {
                'User-Agent': BILI_UA2,
                'Referer': 'https://www.bilibili.com/',
                'Cookie': `SESSDATA=${sessdata}; bili_jct=${biliJct}`,
            },
        });
        const data: any = await r.json();

        if (data.code === 0 && data.data?.isLogin) {
            // 计算 SESSDATA 过期时间（从内嵌 expire 字段）
            let expiresAt = '';
            const parts = sessdata.split(',');
            if (parts.length >= 2) {
                const ts = parseInt(parts[1], 10);
                if (!isNaN(ts)) {
                    expiresAt = new Date(ts * 1000).toISOString().substring(0, 10);
                }
            }

            res.json({
                ok: true,
                status: 'logged_in',
                mid: data.data.mid,
                uname: data.data.uname,
                level: data.data.level_info?.current_level,
                vip_status: data.data.vipStatus,
                vip_type: data.data.vipType,
                sessdata_expires_at: expiresAt,
                sessdata_length: sessdata.length,
            });
        } else {
            res.json({
                ok: false,
                status: 'unlogin',
                code: data.code,
                message: data.message,
            });
        }
    } catch (e: any) {
        res.status(500).json({ ok: false, error: e.message });
    }
});

router.post('/bilibili-qrcode-restart-container', async (req: Request, res: Response) => {
    if (!checkAuth(req, res)) return;

    console.log('[restart-container] 收到重启请求');

    // 异步重启（不等完成，立即返回 200）
    setTimeout(async () => {
        try {
            console.log('[restart-container] 准备重启 gzh-expert-app 容器...');
            const { exec } = require('child_process');

            // 用 docker 命令重启（容器内部能直接调 host docker，因为装了 docker-cli）
            // 如果容器内没 docker daemon，先 exec host 上的 docker
            exec('docker restart gzh-expert-app', { timeout: 30000 }, (err: any, stdout: string, stderr: string) => {
                if (err) {
                    console.error(`[restart-container] 重启失败: ${err.message}`);
                    // 备用方案：自己自杀，让 docker compose restart
                    process.exit(0);
                } else {
                    console.log(`[restart-container] 重启成功: ${stdout}`);
                }
            });
        } catch (e: any) {
            console.error(`[restart-container] 异常: ${e.message}`);
            process.exit(0);
        }
    }, 2000); // 等 2 秒让 .env 写入完成

    res.json({ ok: true, message: '容器重启指令已发出，5-10 秒后恢复' });
});

export default router;