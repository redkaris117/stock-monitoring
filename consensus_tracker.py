import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

def parse_price(raw_val: Any) -> Optional[float]:
    """
    '₩480,000', '$430.00', ' 276,000 ' 등의 문자열을 숫자로 변환합니다.
    """
    if raw_val is None:
        return None
    val_str = str(raw_val).strip()
    if not val_str or val_str in ["-", "N/A", "nan"]:
        return None
    cleaned = re.sub(r"[^\d.]", "", val_str)
    try:
        return float(cleaned)
    except ValueError:
        return None

def extract_date_from_str(text: str) -> Optional[datetime]:
    """
    문자열에서 날짜((YYYY-MM-DD), (MM/DD), YYYY-MM-DD 등)를 추출합니다.
    """
    if not text:
        return None
    # 1. 괄호 안의 전체 날짜: (2026-10-06), (2026.10.06) 등
    matches_full = list(re.finditer(r"\((\d{4})[./-](\d{1,2})[./-](\d{1,2})\)", text))
    if matches_full:
        m = matches_full[-1]
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # 2. 괄호 안의 월/일 날짜: (10/06), (10.06), (10-06)
    matches_short = list(re.finditer(r"\((\d{1,2})[./-](\d{1,2})\)", text))
    if matches_short:
        m = matches_short[-1]
        try:
            month = int(m.group(1))
            day = int(m.group(2))
            now = datetime.now()
            year = now.year
            # 연도 롤오버 처리 (현재 1월이고 기록이 12월인 경우 등)
            if now.month == 1 and month == 12:
                year -= 1
            elif now.month == 12 and month == 1:
                year += 1
            return datetime(year, month, day)
        except ValueError:
            pass

    # 3. 단독 ISO 형식 날짜: 2026-10-06 (기준일자 열 등)
    m_iso = re.search(r"\b(\d{4})[./-](\d{1,2})[./-](\d{1,2})\b", text)
    if m_iso:
        try:
            return datetime(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
        except ValueError:
            pass

    return None

# 연한 파스텔 톤 배경색 팔레트 정의
COLOR_CONSENSUS_UP = "#E6F4EA"     # 연한 파스텔 녹색1 (목표가 상향)
COLOR_CONSENSUS_DOWN = "#FCE8E6"   # 연한 파스텔 적색/분홍1 (목표가 하향)
COLOR_CONSENSUS_NEW = "#E8F0FE"    # 연한 파스텔 블루 (신규 등록)

COLOR_TECH_BUY = "#E0F2F1"         # 연한 파스텔 민트/녹색2 (지지선 안착/매수 추천)
COLOR_TECH_SELL = "#FDEBD0"        # 연한 파스텔 피치/적색2 (전고점 저항/익절/주의)

def evaluate_consensus_change(
    stock_in_sheet: Dict[str, Any],
    new_info: Dict[str, Any],
    tech_analysis: Dict[str, Any],
    min_change_pct: float = 3.0
) -> Tuple[bool, Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    시트에 적힌 기존 목표가와 새로 수집된 최신 목표가를 비교하여
    1) 변동 여부 (상향/하향/신규)
    2) 시트 수정용 데이터 페이로드 (새 목표가, 상승여력, 2개 열 코멘트 및 배경색 등)
    3) 알림용 요약 정보 (is_major_change 플래그 포함)
    를 생성합니다.
    """
    sheet_name = stock_in_sheet["sheet"]
    market = stock_in_sheet["market"]
    code = stock_in_sheet["code"]
    name = stock_in_sheet["name"]
    
    old_tp = parse_price(stock_in_sheet.get("target_price_raw"))
    new_tp = new_info.get("target_price")
    curr_p = new_info.get("current_price")
    
    if market == "KR":
        curr_symbol = "₩"
    elif ".HK" in code:
        curr_symbol = "HK$"
    elif any(x in code for x in [".SS", ".SZ"]):
        curr_symbol = "¥"
    else:
        curr_symbol = "$"
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_short = datetime.now().strftime("%m/%d")

    # 변동 판단
    is_changed = False
    is_major_change = False
    change_type = "유지"
    change_rate_pct = 0.0

    if new_tp is not None:
        if old_tp is not None and old_tp > 0:
            diff_ratio = (new_tp - old_tp) / old_tp
            if abs(diff_ratio) >= 0.005: # 0.5% 이상 변동 시 시트 갱신 감지
                is_changed = True
                change_rate_pct = diff_ratio * 100
                if diff_ratio > 0:
                    change_type = "상향(▲)"
                else:
                    change_type = "하향(▼)"
                # 텔레그램 알림용 주요 변동 판단 (|변동률| >= min_change_pct, 기본 3%)
                if abs(change_rate_pct) >= min_change_pct:
                    is_major_change = True
        else:
            is_changed = True
            is_major_change = True
            change_type = "신규 등록"

    # 상승여력 계산
    upside_str = stock_in_sheet.get("upside_raw", "-")
    if new_tp and curr_p and curr_p > 0:
        upside = ((new_tp - curr_p) / curr_p) * 100
        upside_str = f"+{upside:.1f}%" if upside >= 0 else f"{upside:.1f}%"

    # 포맷팅된 목표주가
    target_price_str = stock_in_sheet.get("target_price_raw", "-")
    if new_tp:
        if market == "KR":
            target_price_str = f"₩{int(round(new_tp)):,}"
        elif ".HK" in code:
            target_price_str = f"HK${new_tp:,.2f}"
        elif any(x in code for x in [".SS", ".SZ"]):
            target_price_str = f"¥{new_tp:,.2f}"
        else:
            target_price_str = f"${new_tp:,.2f}"

    # 1) 목표주가 변동 내용 및 배경색 (목표주가 변동사항 열용)
    consensus_note = ""
    consensus_bg_color = None
    existing_cn = (stock_in_sheet.get("consensus_note") or stock_in_sheet.get("목표주가 변동사항") or "").strip()

    if is_changed:
        if change_type in ["상향(▲)", "하향(▼)"]:
            old_str = f"{curr_symbol}{int(old_tp):,}" if market == "KR" else f"{curr_symbol}{old_tp:.2f}"
            new_str = f"{curr_symbol}{int(new_tp):,}" if market == "KR" else f"{curr_symbol}{new_tp:.2f}"
            sign = "+" if change_rate_pct >= 0 else ""
            consensus_note = f"[{change_type}] {old_str}➔{new_str} ({sign}{change_rate_pct:.1f}%) ({today_short})"
            consensus_bg_color = COLOR_CONSENSUS_UP if change_type == "상향(▲)" else COLOR_CONSENSUS_DOWN
        else:
            new_str = f"{curr_symbol}{int(new_tp):,}" if market == "KR" else f"{curr_symbol}{new_tp:.2f}"
            consensus_note = f"[신규] {new_str} ({today_short})"
            consensus_bg_color = COLOR_CONSENSUS_NEW
    else:
        # 특별한 변동이 없는 날: 최근 업데이트 건 1주일(7일) 유지 로직
        is_recent_update = any(tag in existing_cn for tag in ["[상향", "[하향", "[신규"])
        if is_recent_update:
            note_date = extract_date_from_str(existing_cn) or extract_date_from_str(stock_in_sheet.get("date", ""))
            days_diff = (datetime.now().date() - note_date.date()).days if note_date else 0
            if days_diff < 7:
                # 1주일(7일) 이내: 최근 업데이트 내용 및 배경색 그대로 유지 (시트 수정 건너뜀)
                consensus_note = ""
                consensus_bg_color = None
            else:
                # 1주일 경과: 1주일간 새로운 변경이 없었으므로 [컨센서스 유지]로 전환 및 배경색 초기화
                consensus_note = f"[컨센서스 유지] ({today_short})"
                consensus_bg_color = ""
        else:
            # 기존에 변동 기록이 없거나 이미 [컨센서스 유지]였던 경우
            if not existing_cn or existing_cn == "-":
                consensus_note = f"[컨센서스 유지] ({today_short})"
                consensus_bg_color = ""
            else:
                consensus_note = ""  # 기존 [컨센서스 유지] 기록 유지
                consensus_bg_color = None

    # 2) 기술적 분석 코멘트 및 배경색 (차트 기술적 분석 사항 열용)
    timing_comment = tech_analysis.get("timing_comment", "")
    has_tech_signal = tech_analysis.get("has_signal", False)
    tech_bg_color = None

    if has_tech_signal and "관망" not in tech_analysis.get("action_type", ""):
        act = tech_analysis.get("action_type", "")
        tech_note = f"[{act}] {timing_comment} ({today_short})"
        if "매수" in act:
            tech_bg_color = COLOR_TECH_BUY
        elif any(k in act for k in ["익절", "돌파", "저항", "주의", "이탈"]):
            tech_bg_color = COLOR_TECH_SELL
    else:
        tech_note = f"[중립/관망] {timing_comment} ({today_short})"

    display_cn = consensus_note if consensus_note else existing_cn
    full_update_note = (display_cn + " / " if display_cn else "") + tech_note

    # 시트 업데이트 페이로드
    sheet_update_item = {
        "sheet": sheet_name,
        "ticker": code,
        "date": today_str,
        "tech_note": tech_note,
        "tech_bg_color": tech_bg_color,
        "update_note": full_update_note
    }
    if consensus_note:
        sheet_update_item["consensus_note"] = consensus_note
        if consensus_bg_color is not None:
            sheet_update_item["consensus_bg_color"] = consensus_bg_color
    
    if new_tp:
        sheet_update_item["target_price"] = target_price_str
        sheet_update_item["upside"] = upside_str
        sheet_update_item["source"] = new_info.get("source", stock_in_sheet.get("source", ""))

    alert_item = {
        "sheet": sheet_name,
        "market": market,
        "code": code,
        "name": name,
        "is_consensus_changed": is_changed,
        "is_major_change": is_major_change,
        "change_type": change_type,
        "change_rate_pct": change_rate_pct,
        "old_tp": old_tp,
        "new_tp": new_tp,
        "curr_price": curr_p,
        "upside_str": upside_str,
        "has_tech_signal": has_tech_signal,
        "tech_action": tech_analysis.get("action_type", ""),
        "tech_comment": timing_comment,
        "update_note": full_update_note
    }

    return is_changed, sheet_update_item, alert_item

if __name__ == "__main__":
    test_stock = {
        "sheet": "한국주식",
        "market": "KR",
        "code": "005930",
        "name": "삼성전자",
        "target_price_raw": "₩480,000",
        "upside_raw": "+73.9%"
    }
    test_new = {
        "current_price": 276000.0,
        "target_price": 490000.0,
        "source": "에프앤가이드 컨센서스 / 키움증권"
    }
    test_tech = {
        "has_signal": True,
        "action_type": "단기 매수 관심",
        "timing_comment": "20일선(₩265,700) 지지 반등 시도 (+1.8%)"
    }
    changed, update_item, alert_item = evaluate_consensus_change(test_stock, test_new, test_tech)
    print("Changed:", changed)
    print("Sheet Update Payload:", update_item)
    print("Alert Item:", alert_item)
