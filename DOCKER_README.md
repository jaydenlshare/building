# 使用 Docker 執行自動查詢程式

現在您可以使用 Docker 來執行 `query_service.py`，這能確保排程任務在背景穩定執行，而且不必擔心本機 Python 環境版本或依賴套件衝突的問題。

## 前置作業

請確保您的環境已經安裝了 [Docker Desktop](https://www.docker.com/products/docker-desktop/) 或 Docker Engine 以及 Docker Compose (通常會內建)。

## 啟動與執行

1. **開啟終端機 (Terminal)**
   切換到此專案目錄 `c:\ai-projects\use-permit\`。

2. **背景啟動容器**
   執行以下指令來建置映像檔並啟動背景服務：
   ```bash
   docker-compose up -d --build
   ```

3. **查看執行日誌 (Logs)**
   您可以隨時透過以下指令查看容器目前的輸出日誌（例如確認驗證碼辨識狀況與查詢進度）：
   ```bash
   docker logs -f query_service_container
   ```
   > 提示：按 `Ctrl + C` 可以退出日誌監看，但容器仍然會在背景繼續執行。

4. **停止服務**
   若您需要停止自動查詢服務，請執行：
   ```bash
   docker-compose down
   ```

## 技術細節說明

- **排程執行**：容器啟動後，內部的 `schedule` 會像在本機一樣，每 10 分鐘自動執行一次查詢。
- **檔案同步**：透過 `docker-compose.yml` 內的 `volumes` 設定，容器會將目前目錄掛載為 `/app`，所以容器內產生的 `.json` 與 `.html` 會直接呈現在您本機資料夾中。
- **Git 自動推播機制**：這支程式會自動執行 `git commit` 以及 `git push`。為了解決容器內沒有 SSH 憑證的問題：
  1. `docker-compose.yml` 已經設定會將您的本機 SSH 金鑰 `~/.ssh` 以唯讀 (`ro`) 的方式掛載進入容器（路徑對應為 `/root/.ssh`）。
  2. 若本機沒有 `~/.ssh` 或是權限問題，您也可以改用 HTTPS 加上 Personal Access Token 的方式，或是在容器啟動後進入設定。
  3. `query_service.py` 已更新，如果容器內抓不到本機的 `~/.gitconfig`，它會自動以 `AutoQueryBot` 為名稱做為 Git 使用者。
