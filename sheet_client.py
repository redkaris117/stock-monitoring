import os
import json
import csv
import io
import requests
from typing import List, Dict, Any

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config() -> Dict[str, Any]:
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            
    # GitHub Actions 환경변수 오버라이드 지원
    if os.getenv("SPREADSHEET_ID"):
        config["spreadsheet_id"] = os.getenv("SPREADSHEET_ID")
    if os.getenv("WEBHOOK_URL"):
        config["webhook_url"] = os.getenv("WEBHOOK_URL")
    if "telegram" not in config:
        config["telegram"] = {}
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        config["telegram"]["bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN")
    if os.getenv("TELEGRAM_CHAT_ID"):
        config["telegram"]["chat_id"] = os.getenv("TELEGRAM_CHAT_ID")
        
    return config

def fetch_sheet_rows(spreadsheet_id: str, gid: str) -> List[Dict[str, str]]:
    """
    구글 시트의 공개 gviz CSV 엔드포인트를 통해 실시간 데이터를 읽어옵니다.
    """
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&gid={gid}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"
        
    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)
    if not rows:
        return []
    
    headers = [h.strip() for h in rows[0]]
    data = []
    for r in rows[1:]:
        if not any(r):
            continue
        row_dict = {}
        for idx, h in enumerate(headers):
            val = r[idx].strip() if idx < len(r) else ""
            row_dict[h] = val
        data.append(row_dict)
        
    return data

def get_all_stocks(config: Dict[str, Any] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    설정에 등록된 모든 시트(한국주식, 미국주식)의 종목 데이터를 읽어옵니다.
    """
    if config is None:
        config = load_config()
        
    spreadsheet_id = config["spreadsheet_id"]
    sheets_info = config["sheets"]
    
    result = {}
    for sheet_name, s_info in sheets_info.items():
        gid = s_info["gid"]
        market = s_info.get("market", "KR")
        rows = fetch_sheet_rows(spreadsheet_id, gid)
        
        parsed_stocks = []
        for r in rows:
            # 종목코드 또는 티커 추출
            code = r.get("종목코드") or r.get("티커") or ""
            name = r.get("종목명") or ""
            if not code or code == "비상장":
                continue
                
            parsed_stocks.append({
                "sheet": sheet_name,
                "market": market,
                "name": name,
                "code": code,
                "current_price_raw": r.get("현재가 (수식)", ""),
                "target_price_raw": r.get("목표주가 (컨센서스)", ""),
                "upside_raw": r.get("상승여력", ""),
                "date": r.get("기준일자", ""),
                "source": r.get("출처", ""),
                "desc": r.get("비고 (핵심 기술 및 사업)", ""),
                "tech_note": r.get("차트 기술적 분석 사항", ""),
                "consensus_note": r.get("목표주가 변동사항", "")
            })
            
        result[sheet_name] = parsed_stocks
        
    return result

def push_updates_to_sheet(updates: List[Dict[str, Any]], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Apps Script Webhook으로 변경된 목표주가, 상승여력, 최근 업데이트 항목을 전송하여 시트를 수정합니다.
    """
    if config is None:
        config = load_config()
        
    webhook_url = config.get("webhook_url", "").strip()
    if not webhook_url:
        return {
            "status": "skipped",
            "message": "webhook_url이 설정되지 않아 시트 수정을 건너뜁니다. (config.json 확인)"
        }
        
    payload = {
        "action": "update_stocks",
        "updates": updates
    }
    
    try:
        # Apps Script 웹앱은 302 리다이렉트를 따르므로 allow_redirects=True 필수
        resp = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=30, allow_redirects=True)
        return resp.json()
    except Exception as e:
        return {
            "status": "error",
            "message": f"시트 웹훅 요청 실패: {str(e)}"
        }

if __name__ == "__main__":
    print("Testing sheet client with requests...")
    data = get_all_stocks()
    for s_name, s_list in data.items():
        print(f"Sheet: {s_name}, Stocks: {len(s_list)}")
        if s_list:
            print("  First stock sample:", s_list[0])
