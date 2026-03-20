import requests
import ddddocr
import time
import json
import re
import subprocess
import schedule
import os
from datetime import datetime
from bs4 import BeautifulSoup
import urllib3

# 禁用 urllib3 的不安全請求警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BuildingPermitQuery:
    def __init__(self):
        self.session = requests.Session()
        # 設定基本的 Header 讓請求看起來像正常的瀏覽器
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        # 初始化 ddddocr (設定 show_ad=False 隱藏啟動廣告)
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        self.base_url = "https://building-management.publicwork.ntpc.gov.tw"

    def init_session(self):
        """進入首頁以獲取初始 Cookie"""
        print("[*] 正在初始化 Session...")
        try:
            self.session.get(f"{self.base_url}/bp_query.jsp", verify=False, timeout=10)
        except Exception as e:
            print(f"[!] 初始化 Session 失敗: {e}")

    def get_captcha(self):
        """下載驗證碼圖片並回傳圖片內容"""
        timestamp = int(time.time() * 1000)
        url = f"{self.base_url}/ImageServlet?time={timestamp}"
        print(f"[*] 正在獲取驗證碼圖片...")
        try:
            response = self.session.get(url, verify=False, timeout=10)
            if response.status_code == 200:
                return response.content
            else:
                print(f"[!] 獲取驗證碼失敗，狀態碼: {response.status_code}")
                return None
        except Exception as e:
            print(f"[!] 獲取驗證碼發生例外錯誤: {e}")
            return None

    def recognize_captcha(self, image_bytes):
        """使用 ddddocr 辨識驗證碼"""
        print("[*] 正在辨識驗證碼...")
        result = self.ocr.classification(image_bytes)
        print(f"[*] 辨識結果: {result}")
        return result

    def verify_captcha(self, code):
        """傳送驗證碼到 CheckCode 進行驗證"""
        url = f"{self.base_url}/CheckCode"
        data = {"code": code}
        
        # 針對 CheckCode 的特定 Header
        headers = {
            "Accept": "text/plain, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        print(f"[*] 正在驗證驗證碼是否正確 ({code})...")
        try:
            response = self.session.post(url, data=data, headers=headers, verify=False, timeout=10)
            if response.text.strip() == "true":
                print("[+] 驗證碼正確！")
                return True
            else:
                print("[-] 驗證碼錯誤，將重新嘗試。")
                return False
        except Exception as e:
            print(f"[!] 驗證過程發生錯誤: {e}")
            return False

    def submit_query(self, captcha_code, payload=None):
        """送出最終的表單查詢"""
        url = f"{self.base_url}/bp_list.jsp"
        
        # 預設的查詢 payload，這裡以你提供的案例 (建照號碼 108-00275) 為例
        if payload is None:
            payload = {
                "A1V": "", "A1": "", "C1": "", 
                "B1": "", "B2": "", "B3": "",
                "I1": "111", "I2": "00275", 
                "E1": "", "F1": "", "G1": "", "H1": "",
                "D1V": "請選擇...", "D1": "", "D2": "", "D3": "", 
                "D4": "", "D5": "", "D6": "", "D7": "", "D8": "",
                "Z1": captcha_code  # 填入辨識成功的驗證碼
            }
        else:
            payload["Z1"] = captcha_code
            
        print("[*] 正在送出查詢表單...")
        try:
            response = self.session.post(url, data=payload, verify=False, timeout=15)
            response.encoding = 'utf-8'
            if response.status_code == 200:
                print("[+] 查詢成功！")
                return response.text
            else:
                print(f"[!] 查詢失敗，狀態碼: {response.status_code}")
                return None
        except Exception as e:
            print(f"[!] 送出查詢發生錯誤: {e}")
            return None

    def run_auto_query(self, payload=None, max_retries=5, permit_number="result"):
        """自動化執行完整流程"""
        self.init_session()
        
        for attempt in range(max_retries):
            print(f"\n--- 嘗試次數: {attempt + 1}/{max_retries} ---")
            
            img_bytes = self.get_captcha()
            if not img_bytes:
                continue
                
            code = self.recognize_captcha(img_bytes)
            # 由於驗證碼通常是4碼英文或數字，可以做簡單長度判斷
            if len(code) != 4:
                print(f"[-] 辨識結果長度不對 ({len(code)})，重新取得。")
                continue
                
            is_valid = self.verify_captcha(code)
            if is_valid:
                html_result = self.submit_query(code, payload)
                if html_result:
                    # 儲存原始 HTML 檔案
                    html_filename = f"{permit_number}.html"
                    try:
                        with open(html_filename, "w", encoding="utf-8") as f:
                            f.write(html_result)
                        print(f"[+] 已將原始 HTML 存為: {html_filename}")
                    except Exception as e:
                        print(f"[!] 儲存 HTML 檔案發生錯誤: {e}")
                        
                    return self.parse_and_save_json(html_result, filename=f"{permit_number}.json", permit_number=permit_number)
                break
            
            time.sleep(1) # 暫停一下再重試
            
        print("[!] 達到最大重試次數，查詢失敗。")
        return None
        
    def fetch_and_parse_detail(self, ri_val, permit_number):
        """爬取最新一筆資料的 detail 並解析進度，存成 建案_detail.html"""
        detail_url = f"{self.base_url}/bp_detail.jsp?ri={ri_val}"
        print(f"[*] 正在抓取最新資料的詳細進度: {detail_url}")
        
        try:
            response = self.session.get(detail_url, verify=False, timeout=10)
            response.encoding = 'utf-8'
            html_content = response.text
            
            # 儲存 html
            html_filename = f"{permit_number}_detail.html"
            with open(html_filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"[+] 已將 detail HTML 存為: {html_filename}")
            
            # 準備解析
            soup = BeautifulSoup(html_content, 'html.parser')
            processes = []
            
            # 找到審核進度的標題
            h3 = soup.find(lambda tag: tag.name == "h3" and "審核進度" in tag.text)
            if h3:
                table = h3.find_next_sibling("table")
                if table:
                    trs = table.find_all("tr")
                    data_start_idx = -1
                    # 找出 Header 列的下標
                    for i, tr in enumerate(trs):
                        ths = tr.find_all("th")
                        if ths and len(ths) >= 4 and "序號" in ths[0].text:
                            data_start_idx = i + 1
                            break
                    
                    if data_start_idx != -1:
                        # 從資料列開始處理
                        for tr in trs[data_start_idx:]:
                            tds = tr.find_all("td")
                            if len(tds) >= 4:
                                seq = tds[0].text.strip()
                                date_val = tds[1].text.strip()
                                rank = tds[2].text.strip()
                                result = tds[3].text.strip()
                                processes.append({
                                    "序號": seq,
                                    "日期": date_val,
                                    "審核職階": rank,
                                    "審核結果": result
                                })
                                
            # 依日期 DESC 去排序進度
            processes.sort(key=lambda x: x.get("日期", ""), reverse=True)
            return {"processes": processes}
            
        except Exception as e:
            print(f"[!] 爬取詳細進度時發生例外: {e}")
            return None

    def parse_and_save_json(self, html_content, filename="result.json", permit_number=None):
        """解析 HTML 表格內容，並以 JSON 格式儲存到 result.json"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 尋找這個表單的表格，通常結果都是放在 class="table" 的 table 裡面
        tables = soup.find_all('table', class_='table')
        
        if not tables:
            print("[-] 找不到預期的結果表格。將儲存錯誤頁面以供除錯。")
            with open("error_result.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            return None
            
        result_data = []
        
        # 取得最後一個表格 (根據你提供的 HTML，資料在 tbody 裡面的 tr)
        for table in tables:
            tbody = table.find('tbody')
            if not tbody: continue
            
            rows = tbody.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    # 解析第一個欄位 (送件資訊) 包含日期與號碼與 ri
                    send_info_html = str(cols[0])
                    # 用 Regex 抓取日期
                    date_match = re.search(r'日期：([0-9\-]+)', send_info_html)
                    date_val = date_match.group(1) if date_match else ""
                    # 用 Regex 抓取號碼
                    id_match = re.search(r'號碼：([0-9]+)', send_info_html)
                    id_val = id_match.group(1) if id_match else ""
                    # 用 Regex 抓取 href 內的 ri 參數
                    ri_match = re.search(r'ri=([0-9]+)', send_info_html)
                    ri_val = ri_match.group(1) if ri_match else ""
                    
                    # 解析第二個欄位 (申請類別)
                    class_val = cols[1].text.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                    
                    # 解析第三個欄位 (執照資訊)
                    info_val = cols[2].text.strip().replace('\n', '').replace('\r', '').replace('  ', ' ')
                    
                    # 解析第四個欄位 (審核進度)
                    status_val = cols[3].text.strip().replace('\n', '').replace('\r', '')

                    result_data.append({
                        "idNumber": id_val,
                        "date": date_val,
                        "class": class_val,
                        "info": info_val,
                        "status": status_val,
                        "ri": ri_val
                    })

        # 依照 idNumber 進行降冪排序
        result_data.sort(key=lambda x: x.get("idNumber", ""), reverse=True)
        
        # 取得最新一筆的 detail
        if result_data and permit_number:
            latest = result_data[0]
            if latest.get("ri"):
                detail_data = self.fetch_and_parse_detail(latest["ri"], permit_number)
                if detail_data:
                    latest["detail"] = detail_data

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(result_data, f, ensure_ascii=False, indent=4)
            print(f"[+] 已將查詢結果解析並存為: {filename} (共 {len(result_data)} 筆資料)")
            
            # 更新 updateTimeLog.json
            if permit_number:
                updated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_filename = "updateTimeLog.json"
                log_data = {}
                try:
                    with open(log_filename, "r", encoding="utf-8") as lf:
                        log_data = json.load(lf)
                except (FileNotFoundError, json.JSONDecodeError):
                    pass
                
                log_data[permit_number] = updated_time
                with open(log_filename, "w", encoding="utf-8") as lf:
                    json.dump(log_data, lf, ensure_ascii=False, indent=4)
                print(f"[+] 已更新 updateTimeLog.json 內的 {permit_number} 時間為: {updated_time}")
            
            return filename
        except Exception as e:
            print(f"[!] 儲存 JSON 檔案發生錯誤: {e}")
            return None


def git_pull():
    """在執行任務前先執行 git pull，確保資料是最新的"""
    print("\n[*] 正在執行 git pull 拉取最新資料...")
    try:
        github_pat = os.environ.get('GITHUB_PAT')
        github_user = os.environ.get('GITHUB_USER')
        github_repo = os.environ.get('GITHUB_REPO')

        if github_pat and github_user and github_repo:
            remote_url = f"https://{github_user}:{github_pat}@github.com/{github_user}/{github_repo}.git"
            subprocess.run(['git', 'pull', remote_url, 'main', '--rebase'], check=True)
        else:
            subprocess.run(['git', 'pull', 'origin', 'main', '--rebase'], check=False)
        print("[+] Git pull 完成。")
    except subprocess.CalledProcessError as e:
        print(f"[!] Git pull 失敗 (這在初次執行或無遠端時可能正常): {e}")
    except Exception as e:
        print(f"[!] 執行 Git pull 時發生錯誤: {e}")


def git_commit_and_push():
    """檢查 git status，若有 json 檔案變動則執行 add, commit, push"""
    print("\n[*] 正在檢查 Git 狀態...")
    try:
        # 從環境變數讀取 Git 設定 (對應 .env)
        git_user = os.environ.get('GIT_USERNAME', 'AutoQueryBot')
        git_email = os.environ.get('GIT_EMAIL', 'bot@autoquery.local')
        github_pat = os.environ.get('GITHUB_PAT')
        github_user = os.environ.get('GITHUB_USER')
        github_repo = os.environ.get('GITHUB_REPO')

        # 確保 Git 使用者設定存在
        try:
            subprocess.run(['git', 'config', 'user.name'], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(['git', 'config', '--global', 'user.name', git_user], check=True)
            
        try:
            subprocess.run(['git', 'config', 'user.email'], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(['git', 'config', '--global', 'user.email', git_email], check=True)

        # 首先將所有 json 檔案加入追蹤
        subprocess.run(['git', 'add', '*.json'], check=True)
        
        # 檢查已加入暫存區 (Staging Area) 的檔案是否有變動
        status_result = subprocess.run(['git', 'status', '--porcelain', '*.json'], capture_output=True, text=True)
        
        if not status_result.stdout.strip():
            print("[+] 沒有偵測到檔案變動，略過提交。")
            return

        print("[*] 偵測到 JSON 檔案變動，開始執行 Git 推送...")
        
        # 產生時間戳記提交訊息
        commit_msg = f"update {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        
        # 如果有提供 PAT，設定新的 remote url 進行 HTTPS 推送
        if github_pat and github_user and github_repo:
            print("[*] 使用 Personal Access Token (PAT) 進行 Git 推送...")
            remote_url = f"https://{github_user}:{github_pat}@github.com/{github_user}/{github_repo}.git"
            
            # 使用臨時的 remote 名稱來推送，避免修改到原本的 origin 導致 PAT 洩漏在 git config 中
            print("[*] 正在執行 git push...")
            subprocess.run(['git', 'push', remote_url, 'HEAD:main'], check=True)
        else:
            print("[-] 未設定 GITHUB_PAT 或相關環境變數，將嘗試使用本機預設的 origin 推送...")
            print("[*] 正在執行 git push...")
            subprocess.run(['git', 'push', 'origin'], check=True)
            
        print(f"[+] Git 操作完成！提交訊息: {commit_msg}")
            
        print(f"[+] Git 操作完成！提交訊息: {commit_msg}")
        
    except subprocess.CalledProcessError as e:
        print(f"[!] Git 操作失敗: {e}")
    except FileNotFoundError:
        print("[!] 找不到 git 指令，請確認系統是否已安裝 Git 並加入環境變數。")


def is_working_hours():
    """
    檢查目前是否為可執行時間:
    1. 週一至週五 10:00~17:00
    2. 每天 00:00~02:00
    """
    now = datetime.now()
    
    # 每天 00:00~02:59 (00:00, 01:00, 02:00 各整點啟動)
    if 0 <= now.hour <= 2:
        return True
        
    # 週一至週五 10:00~17:59 (10:00~17:00 各整點啟動)
    is_weekday = 0 <= now.weekday() <= 4
    is_daytime_window = 10 <= now.hour <= 17
    
    return is_weekday and is_daytime_window


def run_job(force=False):
    mode = os.environ.get('EXECUTION_MODE', 'PROD').upper()
    
    # 如果不是強制執行，且不是 TEST 模式，則檢查是否在可執行時間內
    if not force and mode != 'TEST':
        if not is_working_hours():
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 非執行時間 (不在平日 10:00-17:00 或每天 00:00-02:00 範圍內)，跳過此次執行。")
            return

    print("\n" + "="*50)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 自動查詢任務開始執行 (模式: {mode})")
    print("="*50)

    # 執行最前面的 git pull
    git_pull()
    
    bot = BuildingPermitQuery()
    
    # 新增可設定多筆建案查詢的陣列，格式為 ["年度-流水號", "年度-流水號"]
    permits = [
        "111-00275",
        "110-00402",
        "112-00141"
    ]
    
    for permit in permits:
        parts = permit.split("-")
        if len(parts) != 2:
            print(f"[-] 無效的建照號碼格式: {permit}，略過。")
            continue
            
        i1, i2 = parts[0], parts[1]
        
        payload = {
            "A1V": "", "A1": "", "C1": "", 
            "B1": "", "B2": "", "B3": "",
            "I1": i1, "I2": i2, 
            "E1": "", "F1": "", "G1": "", "H1": "",
            "D1V": "請選擇...", "D1": "", "D2": "", "D3": "", 
            "D4": "", "D5": "", "D6": "", "D7": "", "D8": "",
            "Z1": "" # Z1 會在程式內自動填入
        }
        
        print(f"\n>>> 開始查詢建照號碼: {permit}")
        file_path = bot.run_auto_query(payload=payload, permit_number=permit)
        if file_path:
            print(f"[+] {permit} 執行完畢，結果請見 {permit}.html 與 {file_path}")
        else:
            print(f"[-] {permit} 查詢失敗。")
            
    # 執行完畢後做 Git 操作
    git_commit_and_push()


if __name__ == "__main__":
    mode = os.environ.get('EXECUTION_MODE', 'TEST').upper()
    
    print("="*50)
    print(f"新北市政府建管便民服務資訊網 - 自動排程查詢服務已啟動 ({mode} 模式)")
    print("="*50)
    
    # 啟動時先執行一次 (不受時間視窗限制，方便重啟後立即確認)
    run_job(force=True)
    
    if mode == 'TEST':
        # 測試模式：每 10 分鐘執行一次，不限時間
        schedule.every(10).minutes.do(run_job)
        print("\n[*] 測試模式：進入待命狀態，將於每 10 分鐘自動執行 (不限時段)...")
    else:
        # 正式模式：每一小時執行一次 (內含時間視窗檢查)
        schedule.every(1).hours.do(run_job)
        print("\n[*] 正式模式：進入待命狀態，將於每 1 小時自動執行 (平日 10:00-17:00 及 每天 00:00-02:00)...")

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\n[!] 排程服務已被手動中止。")
