# 🎬 超8 · 去水印下载

> 不做下载站，只做「直通车」— 解析影片连结，回传 CDN 直链
>
> **零流量经过我们** — 用户直接从 CDN 下载，伺服器只做解析

## 功能特色

- ✅ **9 大平台支援** — YouTube、抖音、TikTok、小紅書、蝦皮短影音、Bilibili、Instagram、Twitter/X、Facebook
- ✅ **零伺服器流量** — 只解析回传 CDN 直链，用户端直接下载
- ✅ **多画质选择** — YouTube 支援 360p ~ 1080p 多格式
- ✅ **全端 Cloudflare** — 前端 + API 代理都在边缘节点
- ✅ **高速 Python 后端** — Railway + FastAPI + yt-dlp

## 架构

```
用户给连结
      ↓
Cloudflare Worker (s8.v8i8.com)
      ├── 前端 HTML ← GitHub gh-pages
      └── API 代理 → Railway (Python FastAPI + yt-dlp)
                        ↓
                    回传缩图 + CDN 直链
                        ↓
              缩图是超连结 → 点图直下 CDN
                        ↓
                  零流量经过我们 ✅
```

## 技术栈

| 层 | 技术 | 费用 |
|:----|:------|:----:|
| 前端 | HTML + CSS + JS（Cloudflare Worker 托管） | $0 |
| API 代理 | Cloudflare Worker | $0 |
| API 后端 | Python FastAPI + yt-dlp（Railway） | $5/月 |
| 域名 | s8.v8i8.com | $10.44/年 |

## 支援平台（共 9 个）

| 平台 | 支持状态 |
|:----|:--------:|
| YouTube | ✅ 360p ~ 1080p + CDN 直链 |
| 抖音 Douyin | ⚠️ 需 cookies（見下方說明） |
| TikTok | ✅ 通用 yt-dlp 解析 |
| 小紅書 Xiaohongshu | ✅ 通用 yt-dlp 解析 |
| 蝦皮短影音 Shopee | ✅ 通用 yt-dlp 解析 |
| Bilibili | ✅ 通用 yt-dlp 解析 |
| Instagram | ✅ 通用 yt-dlp 解析 |
| Twitter / X | ✅ 通用 yt-dlp 解析 |
| Facebook | ✅ 通用 yt-dlp 解析 |

> 通用解析透过 yt-dlp 实现，持续更新支援更多平台
>
> ⚠️ **抖音注意**：抖音目前需要有效的 cookies 才能解析。請在 `cookies.txt` 檔案中
>    設定從瀏覽器導出的抖音 cookies，或將 cookies 設為 Railway 環境變數 `DOUYIN_COOKIES`。

## API 使用

### 解析影片

```
GET /api/video-info?url=<影片链接>
```

**回应范例：**
```json
{
  "title": "影片标题",
  "thumbnail": "https://...缩图网址",
  "duration": 180,
  "uploader": "作者名称",
  "platform": "YouTube",
  "has_video": true,
  "cdn_url": "https://...CDN直链网址",
  "formats": [
    {"id": "best", "label": "下载（无水印）", "height": 0, "cdn_url": "...", "single": true}
  ]
}
```

### 健康检查（含支援平台列表）

```
GET /api/health
```

### 代理下载

```
GET /api/dl?url=<CDN网址>&filename=video.mp4
```

## 本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动伺服器
python server.py
# → http://localhost:7798
```

## 部署

### Railway 后端

1. Fork 此仓库到你的 GitHub
2. 在 [Railway](https://railway.com) 建立新专案 → 选择此仓库
3. Railway 自动部署（Nixpacks）
4. 设定自订域名（如有需要）

### Cloudflare Worker

```bash
# 安装 wrangler
npm install -g wrangler

# 部署 Worker
wrangler deploy worker.js --name chao8-api

# 设定路由
# s8.v8i8.com/* → chao8-api
```

### DNS 设定

在 Cloudflare DNS 加入：

| 类型 | 名称 | 值 |
|:----|:----|:----|
| CNAME | s8 | oq8ka5k2.up.railway.app |
| TXT | _railway-verify.s8 | railway-verify=... |

## 专案结构

```
chao8-watermark-free/
├── server.py          # FastAPI 主伺服器
├── index.html         # 前端页面
├── worker.js          # Cloudflare Worker（API 代理 + 前端托管）
├── railway.json       # Railway 部署配置
├── requirements.txt   # Python 依赖
├── wrangler.toml      # Cloudflare Worker 配置
└── README.md          # 本说明文件
```

## 新旧站差异

| 项目 | 超8 (s8.v8i8.com) | 旧站 (v8i8.com) |
|:----|:-----------------:|:---------------:|
| 下载方式 | 用户从 CDN 直下 | 伺服器下载后回传 |
| 伺服器流量 | ❌ 零流量 | ✅ 流量经过 |
| 支援平台 | 9 个 | 8 个 |
| 架构 | Worker + Railway | Railway 直连 |

## 免責聲明

- 本工具僅供學習與研究使用
- 使用者應遵守目標平台的使用條款
- 請勿用於任何侵權或非法用途
