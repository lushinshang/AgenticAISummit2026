import os
import sys
import re
from urllib.parse import urlparse, urljoin, urldefrag
import requests
from bs4 import BeautifulSoup

# 設定目標網站與輸出目錄
BASE_URL = "https://rdi.berkeley.edu/events/agentic-ai-summit-2026"
DOMAIN = urlparse(BASE_URL).netloc
OUTPUT_DIR = "site_clone"

# 設定 Request Headers 模擬瀏覽器
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 已訪問與待訪問的 URL 集合
visited_pages = set()
pages_to_visit = [BASE_URL]

def clean_url(url):
    """去除 URL 的 fragment (如 #section-1) 並返回乾淨的 URL"""
    defragged, _ = urldefrag(url)
    return defragged

def url_to_local_path(url):
    """
    將 URL 映射到本地檔案路徑。
    例如:
    - https://rdi.berkeley.edu/events/agentic-ai-summit-2026 -> site_clone/events/agentic-ai-summit-2026/index.html
    - https://rdi.berkeley.edu/assets/css/tailwind.min.css -> site_clone/assets/css/tailwind.min.css
    """
    parsed = urlparse(url)
    if parsed.netloc != DOMAIN:
        return None # 外部網域不映射本地路徑
        
    path = parsed.path
    if not path or path == "/":
        path = "/index.html"
    elif path.endswith("/"):
        path = path + "index.html"
    else:
        # 檢查是否有副檔名，如果沒有則視為目錄並指向 index.html
        basename = os.path.basename(path)
        if "." not in basename:
            path = path + "/index.html"
            
    # 去除開頭的斜線，與 OUTPUT_DIR 結合
    clean_path = path.lstrip("/")
    return os.path.join(OUTPUT_DIR, clean_path)

def download_file(url, local_path):
    """下載資源檔案並存入本地路徑"""
    if os.path.exists(local_path):
        # 檔案已存在，不重複下載
        return True
        
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    try:
        print(f"[下載資源] {url} -> {local_path}")
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"[下載資源失敗] {url}: {e}")
        return False

def is_event_subpage(url):
    """判斷 URL 是否為該峰會活動的子網頁（即以 BASE_URL 開頭）"""
    base_clean = BASE_URL.rstrip("/")
    url_clean = url.rstrip("/")
    return url_clean == base_clean or url_clean.startswith(base_clean + "/")

def process_site():
    """執行遞迴下載與路徑轉換的主迴圈"""
    while pages_to_visit:
        current_url = pages_to_visit.pop(0)
        current_url = clean_url(current_url)
        
        if current_url in visited_pages:
            continue
            
        local_html_path = url_to_local_path(current_url)
        if not local_html_path:
            continue
            
        print(f"\n[開始處理頁面] {current_url}")
        print(f"[本地儲存路徑] {local_html_path}")
        visited_pages.add(current_url)
        
        # 下載網頁 HTML
        try:
            response = requests.get(current_url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            html_content = response.text
        except Exception as e:
            print(f"[錯誤] 無法下載網頁 {current_url}: {e}")
            continue
            
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 1. 處理靜態資源路徑 (images, stylesheets, scripts)
        resource_tags = [
            ("img", "src"),
            ("link", "href"),
            ("script", "src")
        ]
        
        for tag_name, attr_name in resource_tags:
            for tag in soup.find_all(tag_name):
                attr_value = tag.get(attr_name)
                if not attr_value:
                    continue
                    
                if attr_value.startswith("data:") or attr_value.startswith("javascript:"):
                    continue
                    
                abs_url = urljoin(current_url, attr_value)
                parsed_res = urlparse(abs_url)
                
                # 只下載同網域的靜態資源
                if parsed_res.netloc == DOMAIN:
                    local_res_path = url_to_local_path(abs_url)
                    if local_res_path and not local_res_path.endswith("index.html"):
                        download_file(abs_url, local_res_path)
                        # 計算本地相對路徑
                        rel_path = os.path.relpath(local_res_path, os.path.dirname(local_html_path))
                        tag[attr_name] = rel_path
                        
        # 2. 處理網頁連結 <a> 標籤
        for tag in soup.find_all("a"):
            href_value = tag.get("href")
            if not href_value:
                continue
                
            if href_value.startswith("#") or href_value.startswith("mailto:") or href_value.startswith("tel:") or href_value.startswith("javascript:"):
                continue
                
            abs_href = urljoin(current_url, href_value)
            parsed_href = urlparse(abs_href)
            
            if parsed_href.netloc == DOMAIN:
                # 如果是本活動的子網頁，需要下載並轉換成本地相對連結
                if is_event_subpage(abs_href):
                    local_href_path = url_to_local_path(abs_href)
                    if local_href_path:
                        # 去除 fragment 取得乾淨的 URL 放入待存取佇列
                        clean_target_url = clean_url(abs_href)
                        if clean_target_url not in visited_pages and clean_target_url not in pages_to_visit:
                            pages_to_visit.append(clean_target_url)
                            
                        # 計算並更新為本地相對連結（同時保留原本的 fragment）
                        rel_link = os.path.relpath(local_href_path, os.path.dirname(local_html_path))
                        if parsed_href.fragment:
                            rel_link = f"{rel_link}#{parsed_href.fragment}"
                        tag["href"] = rel_link
                else:
                    # 如果是同網域但非活動相關的連結（例如 RDI 首頁 /research 等）
                    # 重寫為線上絕對路徑，確保離線點擊時能連回網路上
                    tag["href"] = abs_href
            else:
                # 外部連結保持原樣
                tag["href"] = abs_href
                
        # 將最終 HTML 存檔
        os.makedirs(os.path.dirname(local_html_path), exist_ok=True)
        with open(local_html_path, "w", encoding="utf-8") as f:
            f.write(str(soup))
        print(f"[儲存成功] {local_html_path}")

if __name__ == "__main__":
    process_site()
