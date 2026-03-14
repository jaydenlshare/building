# 使用官方 Python 3.10 slim 版本作為基底映像檔
FROM python:3.10-slim

# 設定環境變數
# 防止 Python 產生 .pyc 檔案
ENV PYTHONDONTWRITEBYTECODE 1
# 確保 Python 輸出直接送到終端機，避免被緩衝 (對於 schedule logs 很有用)
ENV PYTHONUNBUFFERED 1

# 安裝系統依賴 (git 以及 ddddocr 的底層影像處理依賴)
RUN apt-get update && apt-get install -y \
    git \
    libgl1 \
    libglib2.0-0 \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製 requirements.txt 並安裝 Python 依賴
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 將應用程式原始碼複製到容器內
COPY . /app/

# 設定預設執行的指令
CMD ["python", "query_service.py"]
