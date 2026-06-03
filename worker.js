// 超8去水印下载 - Cloudflare Worker (完整 API)

async function getYTVideoUrl(videoId) {
  const instances = ['https://inv.nadeko.net', 'https://yewtu.be'];
  for (const inst of instances) {
    try {
      const r = await fetch(`${inst}/api/v1/videos/${videoId}?fields=formatStreams,adaptiveFormats`, {
        headers: { 'User-Agent': 'Mozilla/5.0' },
      });
      if (!r.ok) continue;
      const d = await r.json();
      const fmts = d.formatStreams || [];
      if (fmts.length > 0) {
        fmts.sort((a, b) => (b.height || 0) - (a.height || 0));
        if (fmts[0].url) return fmts[0].url;
      }
    } catch (_) {}
  }
  return null;
}

async function getYTInfo(videoId) {
  try {
    const r = await fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`);
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

async function getDouyin(url) {
  const r = await fetch('https://tikwm.com/api/', {
    method: 'POST',
    headers: {
      'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) AppleWebKit/605.1.15',
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({ url, hd: '1' }),
  });
  if (!r.ok) return null;
  const d = await r.json();
  if (d.code !== 0 || !d.data) return null;
  const dat = d.data;
  const cdn = dat.hdplay || dat.play || '';
  if (!cdn) return null;
  return {
    title: (dat.title || '').slice(0, 80),
    thumbnail: dat.origin_cover || dat.cover || '',
    duration: dat.duration || 0,
    uploader: (dat.author || {}).nickname || '',
    cdn_url: cdn,
  };
}

async function resolveUrl(url) {
  const short = ['v.douyin.com', 'youtu.be'];
  if (!short.some(d => url.includes(d))) return url;
  try {
    const r = await fetch(url, { method: 'HEAD', redirect: 'follow' });
    return r.url || url;
  } catch { return url; }
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;
    const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET,OPTIONS', 'Access-Control-Allow-Headers': '*' };

    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });

    // Health
    if (path === '/api/health') {
      return new Response(JSON.stringify({ status: 'ok' }), { headers: { 'Content-Type': 'application/json', ...cors } });
    }

    // Video Info
    if (path === '/api/video-info') {
      const videoUrl = url.searchParams.get('url') || '';
      if (!videoUrl) return new Response(JSON.stringify({ error: 'Missing url' }), { status: 400, headers: { 'Content-Type': 'application/json', ...cors } });

      const resolved = await resolveUrl(videoUrl);

      // Douyin
      if (resolved.includes('douyin.com')) {
        const info = await getDouyin(resolved);
        if (info) {
          return new Response(JSON.stringify({
            title: info.title, thumbnail: info.thumbnail, duration: info.duration,
            uploader: info.uploader, platform: 'Douyin', url: resolved, has_video: true,
            cdn_url: info.cdn_url,
            formats: [{ id: 'best', label: '原始畫質（無浮水印）', height: 0, cdn_url: info.cdn_url, single: true }],
          }), { headers: { 'Content-Type': 'application/json', ...cors } });
        }
        return new Response(JSON.stringify({ title: '抖音影片', platform: 'Douyin', has_video: false, formats: [], _note: '解析失敗' }),
          { headers: { 'Content-Type': 'application/json', ...cors } });
      }

      // YouTube
      if (resolved.includes('youtube.com') || resolved.includes('youtu.be')) {
        const m = resolved.match(/(?:v=|youtu\.be\/|shorts\/)([A-Za-z0-9_-]{11})/);
        const vid = m ? m[1] : '';
        if (!vid) return new Response(JSON.stringify({ error: 'Invalid URL' }), { status: 400, headers: { 'Content-Type': 'application/json', ...cors } });

        const [info, cdnUrl] = await Promise.all([getYTInfo(vid), getYTVideoUrl(vid)]);
        const formats = [];
        if (cdnUrl) formats.push({ id: 'best', label: '720p', height: 720, cdn_url: cdnUrl, single: true });
        formats.push({ id: '18', label: '360p', height: 360, single: false });

        return new Response(JSON.stringify({
          title: info?.title || 'YouTube 影片',
          thumbnail: info?.thumbnail_url || `https://i.ytimg.com/vi/${vid}/hqdefault.jpg`,
          duration: 0, uploader: info?.author_name || '',
          platform: 'YouTube', url: resolved, has_video: formats.length > 0,
          cdn_url: cdnUrl || '', formats,
        }), { headers: { 'Content-Type': 'application/json', ...cors } });
      }

      return new Response(JSON.stringify({ title: '不支援的平台', platform: 'Unknown', has_video: false, formats: [], _note: '僅支援抖音和 YouTube' }),
        { headers: { 'Content-Type': 'application/json', ...cors } });
    }

    // Download Proxy
    if (path === '/api/dl') {
      const target = url.searchParams.get('url');
      const name = url.searchParams.get('filename') || 'video.mp4';
      if (!target) return new Response('Missing url', { status: 400, headers: cors });
      try {
        const r = await fetch(target, { headers: { 'User-Agent': 'Mozilla/5.0' } });
        if (!r.ok) return new Response(`CDN error: ${r.status}`, { status: r.status, headers: cors });
        const h = new Headers(r.headers);
        h.set('Content-Disposition', `attachment; filename="${name}"`);
        h.set('Access-Control-Allow-Origin', '*');
        return new Response(r.body, { headers: h });
      } catch (e) {
        return new Response(`Error: ${e.message}`, { status: 502, headers: cors });
      }
    }

    return new Response('Not Found', { status: 404, headers: cors });
  }
};
