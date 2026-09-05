import { chromium, Browser, Page, BrowserContext } from 'playwright';

export interface QrcodeBotResult {
  success: boolean;
  sessdata?: string;
  bili_jct?: string;
  bili_ticket?: string;
  dede_user_id?: string;
  error?: string;
  qrcode_png_base64?: string;
}

export interface QrcodeBotOptions {
  onQrcodeReady?: (pngBase64: string) => Promise<void>;
  onStatusUpdate?: (status: string, detail?: string) => Promise<void>;
  timeout_ms?: number;
}

/**
 * 用 Playwright 跑 B 站扫码登录。
 * 流程：
 *  1. 打开 https://passport.bilibili.com/login
 *  2. 截屏二维码区域 → 调用 onQrcodeReady 回调
 *  3. 轮询 page.url() 检测扫码完成（URL 含 SESSDATA 或页面跳转）
 *  4. 从浏览器 cookie 提取 SESSDATA / bili_jct / bili_ticket / DedeUserID
 *  5. 返回
 */
export async function runBiliQrcodeLogin(
  opts: QrcodeBotOptions = {}
): Promise<QrcodeBotResult> {
  const timeout = opts.timeout_ms || 180_000; // 3 分钟

  let browser: Browser | null = null;
  try {
    console.log('[qrcode-bot] 启动 chromium...');
    browser = await chromium.launch({
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
      ],
    });

    const context: BrowserContext = await browser.newContext({
      viewport: { width: 1280, height: 800 },
      userAgent:
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      locale: 'zh-CN',
    });
    const page: Page = await context.newPage();

    console.log('[qrcode-bot] 打开登录页...');
    // B 站扫码登录页
    await page.goto('https://passport.bilibili.com/login', {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    // 等待扫码二维码出现（多种 selector 兼容）
    console.log('[qrcode-bot] 等待二维码...');
    let qrcodeImg: any = null;
    const selectors = [
      'img.qrcode-img',
      '.login-qrcode img',
      '#qrcode-img',
      '.qrcode img',
      'img[alt*="二维码"]',
      'img[alt*="扫码"]',
    ];
    for (const sel of selectors) {
      try {
        qrcodeImg = await page.waitForSelector(sel, { timeout: 8000 });
        if (qrcodeImg) {
          console.log(`[qrcode-bot] 找到二维码: ${sel}`);
          break;
        }
      } catch {}
    }

    if (!qrcodeImg) {
      console.warn('[qrcode-bot] 找不到二维码元素，截整页');
    }

    // 截屏二维码
    const png = qrcodeImg
      ? await qrcodeImg.screenshot()
      : await page.screenshot({ clip: { x: 0, y: 0, width: 400, height: 400 } });
    const pngBase64 = png.toString('base64');

    if (opts.onQrcodeReady) {
      await opts.onQrcodeReady(pngBase64);
    }
    if (opts.onStatusUpdate) {
      await opts.onStatusUpdate('qrcode_ready', `二维码已生成 (${pngBase64.length} bytes base64)`);
    }

    console.log('[qrcode-bot] 等待扫码完成...');
    const startTime = Date.now();
    let success = false;
    while (Date.now() - startTime < timeout) {
      await page.waitForTimeout(1500);

      // 检查 cookie
      const cookies = await context.cookies('https://www.bilibili.com');
      const sessdata = cookies.find((c) => c.name === 'SESSDATA')?.value;
      if (sessdata) {
        console.log(`[qrcode-bot] ✅ 检测到 SESSDATA cookie (长度 ${sessdata.length})`);
        success = true;
        break;
      }

      // 检查 URL 变化（兜底）
      const url = page.url();
      if (url.includes('bilibili.com') && !url.includes('passport.bilibili.com/login')) {
        console.log(`[qrcode-bot] URL 已跳转: ${url}`);
        await page.waitForTimeout(2000);
        const cookies2 = await context.cookies('https://www.bilibili.com');
        if (cookies2.find((c) => c.name === 'SESSDATA')) {
          success = true;
          break;
        }
      }
    }

    if (!success) {
      if (browser) await browser.close().catch(() => {});
      return { success: false, error: '扫码超时', qrcode_png_base64: pngBase64 };
    }

    // 提取 cookie
    const cookies = await context.cookies('https://www.bilibili.com');
    const sessdata = cookies.find((c) => c.name === 'SESSDATA')?.value || '';
    const biliJct = cookies.find((c) => c.name === 'bili_jct')?.value || '';
    const biliTicket = cookies.find((c) => c.name === 'bili_ticket')?.value || '';
    const dedeUserId = cookies.find((c) => c.name === 'DedeUserID')?.value || '';

    await browser.close();

    return {
      success: true,
      sessdata,
      bili_jct: biliJct,
      bili_ticket: biliTicket,
      dede_user_id: dedeUserId,
      qrcode_png_base64: pngBase64,
    };
  } catch (e: any) {
    if (browser) {
      try {
        await browser.close();
      } catch {}
    }
    return { success: false, error: e.message };
  }
}