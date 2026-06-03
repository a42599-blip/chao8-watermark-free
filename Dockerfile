FROM python:3.12-slim

WORKDIR /app

# 安裝 ffmpeg（YouTube 高畫質合併用）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# Railway 會動態設定 PORT
EXPOSE 7798

CMD uvicorn server:app --host 0.0.0.0 --port $PORT
