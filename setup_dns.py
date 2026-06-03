"""
超8去水印下载 - DNS 設定腳本
用法: python setup_dns.py <CLOUDFLARE_API_KEY>
"""
import sys, json, urllib.request, urllib.error

EMAIL = "a42599@gmail.com"
ZONE_NAME = "v8i8.com"
SUBDOMAIN = "s8"
TARGET = "a42599-blip.github.io"

def api_call(method, path, data=None):
    url = f"https://api.cloudflare.com/client/v4{path}"
    headers = {
        "X-Auth-Email": EMAIL,
        "X-Auth-Key": API_KEY,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"Error: {e.code} - {e.reason}")
        print(e.read().decode())
        sys.exit(1)

# 1. 取得 Zone ID
print("取得 Zone ID...")
zones = api_call("GET", f"/zones?name={ZONE_NAME}")
if not zones["success"]:
    print("無法找到 v8i8.com 的 zone")
    sys.exit(1)
zone_id = zones["result"][0]["id"]
print(f"Zone ID: {zone_id}")

# 2. 建立 CNAME 記錄
print(f"\n建立 {SUBDOMAIN}.{ZONE_NAME} → {TARGET}...")
record = json.dumps({
    "type": "CNAME",
    "name": SUBDOMAIN,
    "content": TARGET,
    "proxied": True,
    "ttl": 1,  # Auto
}).encode()
result = api_call("POST", f"/zones/{zone_id}/dns_records", record)
if result["success"]:
    print(f"✅ DNS 記錄建立成功！")
    print(f"   https://{SUBDOMAIN}.{ZONE_NAME} → {TARGET}")
else:
    print(f"❌ 失敗: {result['errors']}")

print("\n完成！請等待 1-2 分鐘讓 DNS 生效。")
