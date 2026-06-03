/**
 * 超8去水印下载 - Cloudflare Worker (API + Download Proxy)
 * 
 * Routes:
 *   /api/video-info?url=...  — 解析影片資訊
 *   /api/dl?url=...          — 代理下載（加 Content-Disposition）
 *   /                         — 靜態檔案（需搭配 Pages）
 */

// ── YouTube oEmbed ──
async function getYouTubeInfo(videoId) {
  // 方法1: oEmbed API (最快，免費，不用金鑰)
  const oembedUrl = `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`;
  const oembedResp = await fetch(oembedUrl);
  if (oembedResp.ok) {
    const data = await oembedResp.json();
    return {
      title: data.title || 'YouTube 影片',
      thumbnail: data.thumbnail_url || `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`,
      uploader: data.author_name || '',
      duration: 0, // oEmbed 不提供時長
    };
  }
  return null;
}

// ── 抖音 tikwm API ──
async function getDouyinInfo(url) {
  const resp = await fetch('https://tikwm.com/api/', {
    method: 'POST',
    headers: {
      'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({ url, hd: '1' }).toString(),
  });
  if (!resp.ok) return null;
  const d = await resp.json();
  if (d.code !== 0 || !d.data) return null;
  const dat = d.data;
  const cdn = dat.hdplay || dat.play || '';
  if (!cdn) return null;
  return {
    title: (dat.title || '抖音影片').slice(0, 80),
    thumbnail: dat.origin_cover || dat.cover || '',
    duration: dat.duration || 0,
    uploader: (dat.author || {}).nickname || '',
    cdn_url: cdn,
  };
}

// ── Invidiοus API（YouTube 替代前端）──
const INVIDIOUS = [
  'https://inv.nadeko.net',
  'https://yewtu.be',
  'https://inv.vern.cc',
];

async function getYouTubeVideoUrl(videoId) {
  for (const instance of INVIDIOUS) {
    try {
      const resp = await fetch(`${instance}/api/v1/videos/${videoId}?fields=formatStreams,adaptiveFormats`, {
        headers: { 'User-Agent': 'Mozilla/5.0' },
      });
      if (!resp.ok) continue;
      const data = await resp.json();
      const fmts = data.formatStreams || [];
      if (fmts.length > 0) {
        // 取最高畫質的單檔
        const sorted = fmts.sort((a, b) => (b.height || 0) - (a.height || 0));
        const best = sorted[0];
        if (best && best.url) {
          return best.url;
        }
      }
    } catch (_) {}
  }
  return null;
}

// ── 解析短網址 ──
async function resolveUrl(url) {
  const shortDomains = ['v.douyin.com', 'youtu.be', 'shorts'];
  if (!shortDomains.some(d => url.includes(d))) return url;
  try {
    const resp = await fetch(url, { method: 'HEAD', redirect: 'follow' });
    return resp.url || url;
  } catch {
    return url;
  }
}

// ── 主路由 ──
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': '*',
    };
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    // ── API: /api/video-info ──
    if (path === '/api/video-info') {
      const videoUrl = url.searchParams.get('url') || '';
      if (!videoUrl) {
        return new Response(JSON.stringify({ error: 'Missing url' }), {
          status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders },
        });
      }

      const resolved = await resolveUrl(videoUrl);

      // 抖音
      if (resolved.includes('douyin.com')) {
        const info = await getDouyinInfo(resolved);
        if (info) {
          return new Response(JSON.stringify({
            title: info.title,
            thumbnail: info.thumbnail,
            duration: info.duration,
            uploader: info.uploader,
            platform: 'Douyin',
            url: resolved,
            has_video: true,
            cdn_url: info.cdn_url,
            formats: [{ id: 'best', label: '原始畫質（無浮水印）', height: 0, cdn_url: info.cdn_url, single: true }],
          }), { headers: { 'Content-Type': 'application/json', ...corsHeaders } });
        }
        return new Response(JSON.stringify({
          title: '抖音影片', thumbnail: '', duration: 0, uploader: '',
          platform: 'Douyin', url: resolved, has_video: false, cdn_url: '', formats: [],
          _note: '解析失敗，請確認連結是否有效',
        }), { headers: { 'Content-Type': 'application/json', ...corsHeaders } });
      }

      // YouTube
      if (resolved.includes('youtube.com') || resolved.includes('youtu.be')) {
        const vidMatch = resolved.match(/(?:v=|youtu\.be\/|shorts\/)([A-Za-z0-9_-]{11})/);
        const videoId = vidMatch ? vidMatch[1] : '';
        if (!videoId) {
          return new Response(JSON.stringify({ error: 'Invalid YouTube URL' }), {
            status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders },
          });
        }

        const info = await getYouTubeInfo(videoId);
        const cdnUrl = await getYouTubeVideoUrl(videoId);

        const formats = [];
        // 如果有 CDN 直連
        if (cdnUrl) {
          formats.push({ id: 'best', label: '720p (直連)', height: 720, cdn_url: cdnUrl, single: true });
        }
        // 預設低畫質選項
        formats.push({ id: '18', label: '360p', height: 360, cdn_url: `https://www.youtube.com/watch?v=${videoId}`, single: false });

        return new Response(JSON.stringify({
          title: info?.title || 'YouTube 影片',
          thumbnail: info?.thumbnail || `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`,
          duration: info?.duration || 0,
          uploader: info?.uploader || '',
          platform: 'YouTube',
          url: resolved,
          has_video: formats.length > 0,
          cdn_url: cdnUrl || '',
          formats,
          _note: cdnUrl ? '' : '高畫質下載請使用桌面版 yt-dlp',
        }), { headers: { 'Content-Type': 'application/json', ...corsHeaders } });
      }

      return new Response(JSON.stringify({
        title: '不支援的平台', thumbnail: '', duration: 0, uploader: '',
        platform: 'Unknown', url: resolved, has_video: false, cdn_url: '', formats: [],
        _note: '目前僅支援抖音（douyin.com）和 YouTube',
      }), { headers: { 'Content-Type': 'application/json', ...corsHeaders } });
    }

    // ── API: /api/dl (代理下載) ──
    if (path === '/api/dl') {
      const targetUrl = url.searchParams.get('url') || '';
      const filename = url.searchParams.get('filename') || 'video.mp4';
      if (!targetUrl) {
        return new Response('Missing url', { status: 400, headers: corsHeaders });
      }

      try {
        const resp = await fetch(targetUrl, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
          },
        });

        if (!resp.ok) {
          return new Response(`CDN error: ${resp.status}`, { status: resp.status, headers: corsHeaders });
        }

        const newHeaders = new Headers(resp.headers);
        newHeaders.set('Content-Disposition', `attachment; filename="${filename}"`);
        newHeaders.set('Access-Control-Allow-Origin', '*');

        return new Response(resp.body, {
          status: resp.status,
          headers: newHeaders,
        });
      } catch (err) {
        return new Response(`Proxy error: ${err.message}`, { status: 502, headers: corsHeaders });
      }
    }

    // ── API: /api/health ──
    if (path === '/api/health') {
      return new Response(JSON.stringify({ status: 'ok', service: '超8去水印下载 API' }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    // ── 404 ──
    return new Response('Not Found', { status: 404, headers: corsHeaders });
  }
};
