# 🎬 超8 · 去水印下载

> 不做下载站，只做「直通车」— 解析影片连结，回传 CDN 直链
>
> **零流量经过我们** — 用户直接从 CDN 下载，伺服器只做解析

🌐 **线上网址：** https://s8.v8i8.com  
📦 **GitHub：** `a42599-blip/chao8-watermark-free`  
🏷️ **版本标签：** `v1-stable`（原始版）、`version-v2`（当前版）

---

## 功能特色

- ✅ **9 大平台支援** — YouTube、抖音、TikTok、小紅書、蝦皮、Bilibili、Instagram、Twitter/X、Facebook
- ✅ **零伺服器流量** — 只解析回传 CDN 直链，用户端直接下载
- ✅ **三國語言** — 繁中 / 簡中 / English
- ✅ **全端 Cloudflare** — 前端 + API 代理都在边缘节点
- ✅ **高速 Python 后端** — Railway + FastAPI + yt-dlp

---

## 架构

```
用户给连结
      ↓
Cloudflare Worker (s8.v8i8.com)
      ├── 前端 HTML ← GitHub gh-pages（raw.githubusercontent.com）
      └── /api/video-info → API 解析
            ├── YouTube/Douyin/Bilibili/Shopee → 旧站 Railway（v8i8.com）
            └── 其他平台 → 新站 Railway（capable-courage）
      └── /api/dl → CDN 代理下载（补 Referer 标头）
                        ↓
                    回传缩图 + CDN 直链
                        ↓
                  零流量经过我们 ✅
```

---

## 技术栈

| 层 | 技术 | 费用 |
|:----|:------|:----:|
| 前端 | HTML + CSS + JS（Cloudflare Worker 托管） | $0 |
| API 代理 | Cloudflare Worker | $0 |
| API 后端 | Python FastAPI + yt-dlp（Railway） | $5/月 |
| 域名 | s8.v8i8.com | $10.44/年 |

---

## 支援平台（共 9 个）

| 平台 | 支持状态 | 解析方式 |
|:----|:--------:|:---------|
| YouTube | ✅ 正常 | 经 Worker → 旧站 yt-dlp |
| 抖音 Douyin | ✅ 正常 | 经 Worker → 旧站 a_bogus |
| TikTok | ✅ 正常 | 新站 yt-dlp |
| 小紅書 Xiaohongshu | ✅ 正常 | 新站 yt-dlp |
| 蝦皮 Shopee | ✅ 正常 | 经 Worker → 旧站 |
| Bilibili | ✅ 正常 | 经 Worker → 旧站 |
| Instagram | ✅ 正常 | 新站 yt-dlp |
| Twitter / X | ✅ 正常 | 新站 yt-dlp |
| Facebook | ✅ 正常 | 新站 yt-dlp |

---

## 版本历史

| 版本 | Tag | Commit | 日期 | 说明 |
|:----|:---:|:------:|:----:|:-----|
| **v1-stable** | `v1-stable` | `45041ec` | 2026-06-05 | 原始稳定版（9平台可解析，2个按钮，格式选择器可见） |
| **v2-fix** | `version-v2` | `50d871c` | 2026-06-06 | 隐藏格式选择器、blob下载、Railway builder修正 |

---

## 未解决问题

1. **📋 贴上按钮无法自动读剪贴簿（iOS）**
   - `navigator.clipboard.readText()` 在 iOS 上常失败
   - 需用户手动贴上 → 自动触发解析

2. **⬇️ 下载按钮无法储存到相簿（iOS）**
   - blob下载 + `<a download>` 在 iOS 上无法强制储存
   - `navigator.share({ files: [file] })` 可能失败

3. **🚂 Railway 自动部署未启用**
   - 推 main 不会自动部署
   - 需使用 Railway API Token 手动触发

---

## 部署方式

### 前端更新（Worker）
```bash
# 1. 修改 index.html
# 2. 推送到 gh-pages 分支
git push origin gh-pages

# 3. 更新 Worker SHA 后上传
curl -X PUT "https://api.cloudflare.com/client/v4/accounts/ACCOUNT_ID/workers/scripts/chao8-api" \
  -H "Authorization: Bearer TOKEN" \
  -F "worker.js=@worker-fixed.js;type=application/javascript"
```

### 后端更新（Railway）
```bash
# 1. 推送到 main 分支
git push origin main

# 2. 用 API 触发部署
curl -X POST "https://backboard.railway.app/graphql/v2" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { deploymentRestart(id: \"DEPLOYMENT_ID\") } "}'
```

### 必要 Token
（存放於本地文件，不公開上傳 GitHub）
- Cloudflare Worker Token: 存放在 `worker-fixed.js`
- Railway API Token: 存放在本地記錄

---

## 相关专案

- **旧站（去水印）：** https://v8i8.com | `a42599-blip/video-downloader`（已冻结，不可修改）
- **新站（超8）：** https://s8.v8i8.com | `a42599-blip/chao8-watermark-free`（当前专案）
