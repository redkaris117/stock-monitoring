import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
import yfinance as yf
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_kr_stock_info(code: str) -> Optional[Dict[str, Any]]:
    """
    국내 주식(005930 등)의 최근 60일 주가(이평선/고저점용) 및 컨센서스/목표주가를 조회합니다.
    """
    clean_code = code.strip().zfill(6)
    
    # 1. 60거래일 일봉 데이터 조회 (fchart)
    chart_url = f"https://fchart.stock.naver.com/sise.nhn?symbol={clean_code}&timeframe=day&count=60&requestType=0"
    try:
        resp = requests.get(chart_url, headers=HEADERS, timeout=10)
        root = ET.fromstring(resp.content.decode("euc-kr", errors="ignore"))
        items = root.findall(".//item")
    except Exception as e:
        print(f"[KR ERROR] {clean_code} 차트 수집 실패: {e}")
        items = []

    if not items:
        return None

    candles = []
    for it in items:
        parts = it.get("data", "").split("|")
        if len(parts) >= 5:
            # 날짜, 시가, 고가, 저가, 종가
            try:
                date_str, o, h, l, c = parts[0], float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                candles.append({"date": date_str, "open": o, "high": h, "low": l, "close": c})
            except ValueError:
                continue

    if not candles:
        return None

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    current_price = closes[-1]
    ma20 = sum(closes[-20:]) / min(len(closes), 20)
    ma60 = sum(closes[-60:]) / len(closes)
    high_60d = max(highs)
    low_60d = min(lows)

    # 2. 컨센서스 및 최근 리포트 조회 (통합 API)
    integ_url = f"https://m.stock.naver.com/api/stock/{clean_code}/integration"
    target_price = None
    consensus_date = datetime.now().strftime("%Y-%m-%d")
    source = "에프앤가이드 컨센서스"

    try:
        i_resp = requests.get(integ_url, headers=HEADERS, timeout=10)
        if i_resp.status_code == 200:
            i_data = i_resp.json()
            c_info = i_data.get("consensusInfo")
            if c_info and c_info.get("priceTargetMean"):
                raw_tp = str(c_info["priceTargetMean"]).replace(",", "")
                try:
                    target_price = float(raw_tp)
                except ValueError:
                    target_price = None
            if c_info and c_info.get("createDate"):
                consensus_date = c_info["createDate"]
                
            researches = i_data.get("researches", [])
            if researches:
                latest_bnm = researches[0].get("bnm", "")
                if latest_bnm:
                    source = f"에프앤가이드 컨센서스 / {latest_bnm}"
    except Exception as e:
        print(f"[KR INFO] {clean_code} 컨센서스 파싱 실패(또는 없음): {e}")

    return {
        "market": "KR",
        "code": clean_code,
        "current_price": current_price,
        "ma20": ma20,
        "ma60": ma60,
        "high_60d": high_60d,
        "low_60d": low_60d,
        "target_price": target_price,
        "consensus_date": consensus_date,
        "source": source
    }

def get_us_stock_info(ticker: str) -> Optional[Dict[str, Any]]:
    """
    미국 주식(TSLA, NVDA 등)의 최근 60일 주가 및 월가 컨센서스/목표주가를 조회합니다.
    """
    clean_ticker = ticker.strip().upper()
    try:
        t = yf.Ticker(clean_ticker)
        # 1. 3개월(약 60거래일) 일봉 데이터 조회
        hist = t.history(period="3mo")
        if hist.empty or len(hist) < 5:
            return None

        closes = hist["Close"].tolist()
        highs = hist["High"].tolist()
        lows = hist["Low"].tolist()

        current_price = closes[-1]
        ma20 = sum(closes[-20:]) / min(len(closes), 20)
        ma60 = sum(closes[-60:]) / len(closes)
        high_60d = max(highs)
        low_60d = min(lows)

        # 2. 목표주가 및 컨센서스 조회
        info = t.info
        target_price = info.get("targetMeanPrice")
        if target_price is not None:
            target_price = float(target_price)

        consensus_date = datetime.now().strftime("%Y-%m-%d")
        source = "월가 컨센서스"

        return {
            "market": "US",
            "code": clean_ticker,
            "current_price": current_price,
            "ma20": ma20,
            "ma60": ma60,
            "high_60d": high_60d,
            "low_60d": low_60d,
            "target_price": target_price,
            "consensus_date": consensus_date,
            "source": source
        }
    except Exception as e:
        print(f"[US ERROR] {clean_ticker} 수집 실패: {e}")
        return None

if __name__ == "__main__":
    print("Testing KR Stock (005930 - Samsung)...")
    kr_info = get_kr_stock_info("005930")
    print("KR Info:", kr_info)

    print("\nTesting US Stock (TSLA - Tesla)...")
    us_info = get_us_stock_info("TSLA")
    print("US Info:", us_info)
