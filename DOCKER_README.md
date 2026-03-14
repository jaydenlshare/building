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

## 技術細節與排程說明

- **執行模式 (`EXECUTION_MODE`)**：您可以在 `.env` 中切換模式：
  - `PROD` (預設)：**週一至週五 10:00~17:00** 之間執行，每 **1 小時** 啟動一次。
  - `TEST`：每 **10 分鐘** 執行一次，且**不限**於任何時段，適合測試連線狀快。
- **排程執行**：容器啟動後，內部的 `schedule` 會根據上述模式自動執行。
- **檔案同步**：透過 `docker-compose.yml` 內的 `volumes` 設定，容器會將目前目錄掛載為 `/app`，所以容器內產生的 `.json` 與 `.html` 會直接呈現在您本機資料夾中。
- **Git 自動推播機制**：這支程式會自動執行 `git commit` 以及 `git push`。為了解決容器內的身分問題：
  1. 優先使用 `.env` 中的 `GITHUB_PAT` 進行 HTTPS 改寫推送（推薦）。
  2. 若未設定 PAT，則會嘗試使用掛載的 SSH 金鑰進行推送。
  3. `query_service.py` 已更新，如果容器內抓不到使用者身分，它會自動以 `AutoQueryBot` 為名稱做為 Git 使用者。
