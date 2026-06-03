# 🎬 超8去水印下载

> 不做下载站，只做「直通车」— 解析影片连结，回传 CDN 直链

## 架构

```
用户给连结 → 我们解析 → 回传缩图+格式选单
                             ↓
              缩图是超连结 → 点图直下 CDN
                             ↓
                    零流量经过我们 ✅
```

## 技术栈

| 层 | 技术 | 费用 |
|----|------|------|
| 前端 | HTML + CSS + JS (Cloudflare Pages) | $0 |
| API | Python FastAPI (Railway) | $5/月 |
| 下载代理 | Cloudflare Worker | $0 |
| 域名 | v8i8.com → s8.v8i8.com | $10.44/年 |

## 支援平台

- ✅ 抖音（无水印 CDN）
- ✅ YouTube（360p / 720p 直链，1080p+ 需合并）

## 本地开发

```bash
cd D:/超8去水印下载
pip install -r requirements.txt
python server.py
# → http://localhost:7798
```

## 部署

1. Push 到 GitHub
2. Railway 自动部署
3. Cloudflare DNS: s8.v8i8.com → Railway
4. Cloudflare Worker: 部署 worker.js
