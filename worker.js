/**
 * 超8去水印下载 - Cloudflare Worker
 * 用途：代理 CDN 下載，加上 Content-Disposition 強制下載標頭
 * 部署：到 Cloudflare Dashboard → Workers & Pages → 新增 Worker
 *       將此檔案內容貼入，部署後綁定到 s8.v8i8.com/worker
 *
 * 或作為 Route 綁定：s8.v8i8.com/dl/*
 */

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url);
  const targetUrl = url.searchParams.get('url');
  const filename = url.searchParams.get('filename') || 'video.mp4';

  if (!targetUrl) {
    return new Response('Missing "url" parameter', { status: 400 });
  }

  try {
    // 轉發請求到 CDN
    const response = await fetch(targetUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Accept-Language': 'zh-TW,zh;q=0.9',
        'Range': request.headers.get('Range') || '',
      },
    });

    if (!response.ok && response.status !== 206) {
      return new Response(`CDN error: ${response.status}`, { status: response.status });
    }

    // 複製回應並加上下載標頭
    const newHeaders = new Headers(response.headers);
    newHeaders.set('Content-Disposition', `attachment; filename="${filename}"`);
    newHeaders.set('Access-Control-Allow-Origin', '*');
    newHeaders.set('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS');
    newHeaders.set('Access-Control-Allow-Headers', '*');

    // 移除可能造成問題的標頭
    newHeaders.delete('Content-Security-Policy');
    newHeaders.delete('X-Content-Type-Options');

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders,
    });
  } catch (err) {
    return new Response(`Proxy error: ${err.message}`, { status: 502 });
  }
}
