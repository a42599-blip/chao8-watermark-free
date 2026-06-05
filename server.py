# -*- coding: utf-8 -*-
"""
超8去水印下载 - 解析 API（精簡版）
只回傳影片資訊 + CDN 直連網址，不下載、不代理、不存檔
"""
import asyncio, re, json, os, sys, time, shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode, quote
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import yt_dlp
import uvicorn

BASE_DIR = Path(__file__).parent
executor = ThreadPoolExecutor(max_workers=4)

app = FastAPI(title="超8去水印下载 API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Helper ────────────────────────────────────────────────

def _is_douyin(url: str) -> bool:
    return "douyin.com" in url or "douyinvod" in url

def _is_youtube(url: str) -> bool:
    return any(d in url for d in ("youtube.com", "youtu.be", "m.youtube.com"))

def _extract_youtube_id(url: str) -> str:
    m = re.search(r'(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})', url)
    return m.group(1) if m else ""

def _parse_aweme_id(url: str) -> str:
    for pat in (r'/video/(\d+)', r'modal_id=(\d+)', r'[?&]vid=(\d+)', r'/note/(\d+)'):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return ""

async def resolve_short_url(url: str) -> str:
    """解析短網址，取得真實 URL"""
    if not any(s in url for s in ("v.douyin.com", "youtu.be", "b23.tv", "xhslink.com", "shp.ee", "sv.shopee")):
        return url
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as c:
            r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
            return str(r.url)
    except Exception:
        return url

# ── 抖音解析 ─────────────────────────────────────────────

async def _get_douyin_fast(url: str) -> dict:
    """取得抖音影片 CDN（tikwm + a_bogus API + yt-dlp）"""
    # 先解析短網址
    real_url = url
    if "v.douyin.com" in url:
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as c:
                r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
                real_url = str(r.url)
        except:
            pass
    # 方法1：tikwm.com
    try:
        await asyncio.sleep(0.3)
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            r = await client.post("https://tikwm.com/api/",
                data={"url": url, "hd": "1"},
                headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"})
            d = r.json()
            if d.get("code") == 0 and d.get("data"):
                dat = d["data"]
                cdn = dat.get("hdplay") or dat.get("play") or ""
                if cdn:
                    return {
                        "title": dat.get("title", "抖音影片")[:80],
                        "thumbnail": dat.get("origin_cover") or dat.get("cover", ""),
                        "duration": dat.get("duration", 0),
                        "uploader": (dat.get("author") or {}).get("nickname", ""),
                        "cdn_url": cdn,
                    }
    except Exception as e:
        print(f"[douyin/tikwm] {e}")

    # 方法2：a_bogus API + 公開 cookies
    try:
        aweme_id = _parse_aweme_id(real_url)
        if aweme_id:
            from crawlers.douyin.web.utils import BogusManager
            import re, yaml
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get("https://www.douyin.com/", headers={"User-Agent": "Mozilla/5.0"})
                fresh = dict(r.cookies)
            cfg_path = BASE_DIR / "crawlers/douyin/web/config.yaml"
            cookie_str = ""
            if cfg_path.exists():
                with open(cfg_path, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                cookie_str = cfg.get("TokenManager", {}).get("douyin", {}).get("headers", {}).get("Cookie", "")
            for k, v in fresh.items():
                old = re.search(f'{k}=[^;]+', cookie_str)
                cookie_str = cookie_str.replace(old.group(), f'{k}={v}') if old else cookie_str + f'; {k}={v}'
            params = {"aweme_id": aweme_id, "msToken": ""}
            ua = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36"
            a_bogus = BogusManager.ab_model_2_endpoint(params, ua)
            api_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?{urlencode(params)}&a_bogus={a_bogus}"
            async with httpx.AsyncClient(timeout=5) as client:
                headers = {"User-Agent": ua, "Referer": "https://www.douyin.com/"}
                if cookie_str:
                    headers["Cookie"] = cookie_str
                resp = await client.get(api_url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if "aweme_detail" in data and data["aweme_detail"]:
                        ad = data["aweme_detail"]
                        video = ad.get("video", {}); play_addr = video.get("play_addr", {}); url_list = play_addr.get("url_list", [])
                        if url_list:
                            dur = ad.get("duration", 0)
                            return {"title": (ad.get("desc") or "抖音影片")[:80], "cdn_url": url_list[0].replace("playwm", "play"), "duration": dur//1000 if dur>1000 else dur, "uploader": ad.get("author",{}).get("nickname","") if ad.get("author") else "", "thumbnail": video.get("cover",{}).get("url_list",[""])[0] if video.get("cover") else ""}
    except ImportError:
        print("[douyin/abogus] module not available")
    except Exception as e:
        print(f"[douyin/abogus] {e}")

    # 方法3：yt-dlp
    try:
        loop = asyncio.get_event_loop()
        def _dy_ytdlp():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {}
                cdn = info.get("url") or ""
                if not cdn:
                    rfs = info.get("requested_formats") or []
                    if rfs:
                        cdn = rfs[0].get("url") or ""
                if not cdn:
                    fmts = info.get("formats") or []
                    for f in reversed(fmts):
                        u = f.get("url") or ""
                        if u:
                            cdn = u
                            break
                return {
                    "title": (info.get("title") or "抖音影片")[:80],
                    "thumbnail": info.get("thumbnail") or "",
                    "duration": info.get("duration") or 0,
                    "uploader": info.get("uploader") or "",
                    "cdn_url": cdn,
                }
        info = await asyncio.wait_for(loop.run_in_executor(executor, _dy_ytdlp), timeout=15)
        if info and info.get("cdn_url"):
            return info
    except Exception as e:
        err_msg = str(e)
        print(f"[douyin/ytdlp] {err_msg[:80]}")
        if "cookies" in err_msg.lower():
            return {"need_cookies": True, "title": "抖音影片", "cdn_url": ""}

    return {}

# ── YouTube 解析 ──────────────────────────────────────────

YT_FORMAT_MAP = [
    {"id": "18",  "label": "360p",  "height": 360,  "single": True},
    {"id": "22",  "label": "720p",  "height": 720,  "single": True},
    {"id": "137", "label": "1080p", "height": 1080, "single": False},
    {"id": "303", "label": "1080p60","height": 1080, "single": False},
    {"id": "299", "label": "1080p60","height": 1080, "single": False},
    {"id": "136", "label": "720p",  "height": 720,  "single": False},
]

async def _get_youtube_info(url: str) -> dict:
    """取得 YouTube 影片資訊"""
    try:
        loop = asyncio.get_event_loop()
        def _yt_ytdlp():
            with yt_dlp.YoutubeDL({
                "quiet": True, "no_warnings": True, "skip_download": True,
            }) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {}
                title = info.get("title", "YouTube影片")[:80]
                thumbnail = info.get("thumbnail", "")
                duration = info.get("duration", 0)
                uploader = info.get("uploader", "") or info.get("channel", "") or ""
                # 收集可用的格式
                formats = info.get("formats", [])
                available = []
                for f in formats:
                    fid = str(f.get("format_id", ""))
                    height = f.get("height", 0) or 0
                    ext = f.get("ext", "")
                    url_cdn = f.get("url", "") or ""
                    has_audio = f.get("acodec", "none") != "none"
                    has_video = f.get("vcodec", "none") != "none"
                    if not url_cdn:
                        continue
                    # 單檔（合併音視頻）：如 format 18, 22
                    if has_video and has_audio:
                        available.append({
                            "id": fid,
                            "label": f"{height}p" if height else ext,
                            "height": height,
                            "cdn_url": url_cdn,
                            "single": True,
                        })
                    # 純視頻（需合併音訊）：如 format 137, 136
                    elif has_video and not has_audio:
                        # 找對應音訊
                        audio_url = ""
                        audio_id = ""
                        for af in formats:
                            if af.get("height") is None and af.get("acodec", "none") != "none" and af.get("vcodec", "none") == "none":
                                a_url = af.get("url", "") or ""
                                if a_url:
                                    audio_url = a_url
                                    audio_id = str(af.get("format_id", ""))
                                    break
                        available.append({
                            "id": fid,
                            "label": f"{height}p (影片)",
                            "height": height,
                            "cdn_url": url_cdn,
                            "audio_url": audio_url,
                            "audio_id": audio_id,
                            "single": False,
                        })
                # 去重、排序
                seen = set()
                unique = []
                for a in sorted(available, key=lambda x: -x["height"]):
                    key = a["id"]
                    if key not in seen:
                        seen.add(key)
                        unique.append(a)
                return {
                    "title": title,
                    "thumbnail": thumbnail,
                    "duration": duration,
                    "uploader": uploader,
                    "formats": unique,
                }
        info = await asyncio.wait_for(loop.run_in_executor(executor, _yt_ytdlp), timeout=20)
        return info
    except Exception as e:
        print(f"[youtube] {e}")
        return {}

# ── API 端點 ──────────────────────────────────────────────

@app.get("/")
def index():
    return FileResponse(str(BASE_DIR / "index.html"),
                        headers={"Cache-Control": "no-store, no-cache, must-revalidate"})

@app.get("/api/video-info")
async def video_info(url: str):
    real_url = await resolve_short_url(url)

    # ── 抖音 ──
    if _is_douyin(real_url):
        fast = await _get_douyin_fast(real_url)
        if fast.get("cdn_url"):
            return JSONResponse({
                "title": fast.get("title", "抖音影片"),
                "thumbnail": fast.get("thumbnail", ""),
                "duration": fast.get("duration", 0),
                "uploader": fast.get("uploader", ""),
                "platform": "Douyin",
                "url": real_url,
                "has_video": True,
                "cdn_url": fast["cdn_url"],
                "formats": [{"id": "best", "label": "原始畫質（無浮水印）", "height": 0, "cdn_url": fast["cdn_url"], "single": True}],
            })
        need_cookies = fast.get("need_cookies", False)
        note = "抖音需要 cookies，請在 cookies.txt 中設定有效的抖音 cookies" if need_cookies else "解析失敗，請確認連結是否有效"
        return JSONResponse({
            "title": "抖音影片", "thumbnail": "", "duration": 0, "uploader": "",
            "platform": "Douyin", "url": real_url, "has_video": False,
            "cdn_url": "", "formats": [],
            "_note": note,
        })

    # ── YouTube ──
    if _is_youtube(real_url):
        info = await _get_youtube_info(real_url)
        if info and info.get("formats"):
            # 找最低可用單檔（360p）做為預設 CDN
            singles = [f for f in info["formats"] if f.get("single")]
            default_cdn = singles[0]["cdn_url"] if singles else (info["formats"][0].get("cdn_url") or "")
            return JSONResponse({
                "title": info.get("title", "YouTube影片"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", ""),
                "platform": "YouTube",
                "url": real_url,
                "has_video": True,
                "cdn_url": default_cdn,
                "formats": info.get("formats", []),
            })
        return JSONResponse({
            "title": "YouTube影片", "thumbnail": "", "duration": 0, "uploader": "",
            "platform": "YouTube", "url": real_url, "has_video": False,
            "cdn_url": "", "formats": [],
            "_note": "解析失敗，請確認連結是否有效",
        })

    # ── 先從網址偵測平台（不依賴 yt-dlp）──
    PLATFORM_RULES = [
        ("bilibili.com", "Bilibili"), ("b23.tv", "Bilibili"),
        ("xiaohongshu.com", "Xiaohongshu"), ("xhslink.com", "Xiaohongshu"),
        ("shopee", "Shopee"), ("shp.ee", "Shopee"), ("sv.shopee", "Shopee"),
        ("tiktok.com", "TikTok"),
        ("instagram.com", "Instagram"),
        ("twitter.com", "Twitter"), ("x.com", "Twitter"),
        ("facebook.com", "Facebook"), ("fb.com", "Facebook"), ("fb.watch", "Facebook"),
    ]
    detected_platform = "Unknown"
    for keyword, name in PLATFORM_RULES:
        if keyword in real_url:
            detected_platform = name
            break

    # ── 其他平台（通用 yt-dlp 解析）──
    try:
        loop = asyncio.get_event_loop()
        def _generic_parse():
            with yt_dlp.YoutubeDL({
                "quiet": True, "no_warnings": True, "skip_download": True,
            }) as ydl:
                info = ydl.extract_info(real_url, download=False)
                if not info:
                    return None
                title = (info.get("title") or "影片")[:80]
                thumbnail = info.get("thumbnail") or ""
                duration = info.get("duration") or 0
                uploader = info.get("uploader") or info.get("channel") or info.get("creator") or ""
                webpage_url = info.get("webpage_url") or real_url
                # 平台偵測（從 yt-dlp 結果補充）
                detected = detected_platform
                # 收集可用格式
                fmts = info.get("formats") or []
                available = []
                seen = set()
                for f in fmts:
                    fid = str(f.get("format_id", ""))
                    height = f.get("height", 0) or 0
                    url_cdn = f.get("url", "") or ""
                    has_audio = f.get("acodec", "none") != "none"
                    has_video = f.get("vcodec", "none") != "none"
                    if not url_cdn or not has_video:
                        continue
                    if has_video and has_audio:
                        key = f"single_{height}"
                        if key not in seen:
                            seen.add(key)
                            available.append({
                                "id": fid,
                                "label": f"{height}p" if height else "Audio",
                                "height": height,
                                "cdn_url": url_cdn,
                                "single": True,
                            })
                available.sort(key=lambda x: -x["height"])
                default_cdn = available[0]["cdn_url"] if available else (info.get("url") or "")
                return {
                    "title": title,
                    "thumbnail": thumbnail,
                    "duration": duration,
                    "uploader": uploader,
                    "platform": detected,
                    "url": webpage_url,
                    "has_video": bool(default_cdn),
                    "cdn_url": default_cdn,
                    "formats": available,
                }
        result = await asyncio.wait_for(
            loop.run_in_executor(executor, _generic_parse), timeout=25
        )
        if result and result.get("has_video"):
            return JSONResponse(result)
        if result:
            return JSONResponse({**result, "_note": "解析失敗，請確認連結是否有效"})
    except Exception as e:
        print(f"[generic] {e}")

    return JSONResponse({
        "title": "不支援的平台", "thumbnail": "", "duration": 0, "uploader": "",
        "platform": detected_platform, "url": real_url, "has_video": False,
        "cdn_url": "", "formats": [],
        "_note": f"無法解析此連結，支援：YouTube、抖音、小紅書、蝦皮短影音、Bilibili、TikTok、Instagram、Twitter/X、Facebook",
    })

@app.get("/api/dl")
async def download_proxy(url: str, filename: str = "video.mp4"):
    """代理下載 CDN 影片，加上 Content-Disposition 強制下載標頭"""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            content = resp.content
            content_type = resp.headers.get("content-type", "video/mp4")
            return Response(
                content=content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Length": str(len(content)),
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache",
                }
            )
    except Exception as e:
        print(f"[dl_proxy] {e}")
        return JSONResponse({"error": "下載失敗"}, status_code=502)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "超8去水印下载 API",
        "platforms": ["YouTube", "抖音 Douyin", "TikTok", "小紅書 Xiaohongshu", "蝦皮短影音 Shopee", "Bilibili", "Instagram", "Twitter/X", "Facebook"]
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7798))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)

