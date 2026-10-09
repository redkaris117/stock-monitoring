import requests
from typing import List, Dict, Any
from datetime import datetime

def get_currency_symbol(code: str, market: str) -> str:
    if market == "KR":
        return "₩"
    if ".HK" in code:
        return "HK$"
    if any(x in code for x in [".SS", ".SZ"]):
        return "¥"
    return "$"

def format_telegram_report(
    date_str: str,
    consensus_changes: List[Dict[str, Any]],
    timing_signals: List[Dict[str, Any]],
    spreadsheet_id: str = ""
) -> str:
    """
    모니터링 결과를 텔레그램용 HTML 메시지로 포맷팅합니다.
    """
    lines = []
    lines.append(f"📊 <b>[일일 주식 모니터링 브리핑]</b>")
    lines.append(f"📅 <b>기준일시:</b> {date_str} 저녁 9시")
    lines.append("─────────────────────")

    # 1. 목표주가 / 컨센서스 변동 섹션
    lines.append("🎯 <b>1. 오늘 목표주가/컨센서스 변동 내역</b>")
    if consensus_changes:
        for c in consensus_changes:
            name = c["name"]
            code = c["code"]
            ch_type = c["change_type"]
            sheet = c["sheet"]
            symbol = get_currency_symbol(code, c["market"])
            
            old_str = f"{symbol}{int(c['old_tp']):,}" if c["market"] == "KR" and c.get("old_tp") else (f"{symbol}{c['old_tp']:.2f}" if c.get("old_tp") else "-")
            new_str = f"{symbol}{int(c['new_tp']):,}" if c["market"] == "KR" and c.get("new_tp") else (f"{symbol}{c['new_tp']:.2f}" if c.get("new_tp") else "-")
            rate_str = f"({c['change_rate_pct']:+.1f}%)" if c.get("change_rate_pct") else ""
            
            lines.append(f"• <b>{name}</b> ({code}) [{sheet}]")
            lines.append(f"   ↳ <b>{ch_type}</b> {old_str} ➔ <b>{new_str}</b> {rate_str}")
            lines.append(f"   ↳ 상승여력: <b>{c.get('upside_str', '-')}</b> | 시트 자동 반영 완료 ✅")
    else:
        lines.append("• 오늘 새롭게 변동된 목표주가/컨센서스는 없습니다.")

    lines.append("")
    lines.append("─────────────────────")

    # 2. 기술적 분석 & 매매 타이밍 섹션
    lines.append("📈 <b>2. 지지/저항선 근접 & 매매 타이밍 선별</b>")
    if timing_signals:
        # 매수 관심 vs 익절/돌파 vs 주의 분리
        buy_list = [s for s in timing_signals if "매수" in s.get("tech_action", "")]
        sell_list = [s for s in timing_signals if any(k in s.get("tech_action", "") for k in ["익절", "돌파", "저항"])]
        risk_list = [s for s in timing_signals if "주의" in s.get("tech_action", "") or "이탈" in s.get("tech_action", "")]

        if buy_list:
            lines.append("\n🟢 <b>[지지선 안착 / 분할 매수 타점]</b>")
            kr_buy = [s for s in buy_list if s["market"] == "KR"]
            us_buy = [s for s in buy_list if s["market"] == "US"]
            cn_buy = [s for s in buy_list if s["market"] == "CN"]
            if kr_buy:
                lines.append(" <b>[국내]</b>")
                for s in kr_buy:
                    lines.append(f"  • <b>{s['name']}</b> (₩{int(s['curr_price']):,}): {s['tech_comment']}")
            if us_buy:
                lines.append(" <b>[미국]</b>")
                for s in us_buy:
                    lines.append(f"  • <b>{s['name']}</b> (${s['curr_price']:.2f}): {s['tech_comment']}")
            if cn_buy:
                lines.append(" <b>[중국/홍콩]</b>")
                for s in cn_buy:
                    sym = get_currency_symbol(s["code"], s["market"])
                    lines.append(f"  • <b>{s['name']}</b> ({sym}{s['curr_price']:.2f}): {s['tech_comment']}")

        if sell_list:
            lines.append("\n🔴 <b>[전고점 저항 근접 / 분할 익절 고려]</b>")
            kr_sell = [s for s in sell_list if s["market"] == "KR"]
            us_sell = [s for s in sell_list if s["market"] == "US"]
            cn_sell = [s for s in sell_list if s["market"] == "CN"]
            if kr_sell:
                lines.append(" <b>[국내]</b>")
                for s in kr_sell:
                    lines.append(f"  • <b>{s['name']}</b> (₩{int(s['curr_price']):,}): {s['tech_comment']}")
            if us_sell:
                lines.append(" <b>[미국]</b>")
                for s in us_sell:
                    lines.append(f"  • <b>{s['name']}</b> (${s['curr_price']:.2f}): {s['tech_comment']}")
            if cn_sell:
                lines.append(" <b>[중국/홍콩]</b>")
                for s in cn_sell:
                    sym = get_currency_symbol(s["code"], s["market"])
                    lines.append(f"  • <b>{s['name']}</b> ({sym}{s['curr_price']:.2f}): {s['tech_comment']}")

        if risk_list:
            lines.append("\n⚠️ <b>[주요 이평선 이탈 주의]</b>")
            kr_risk = [s for s in risk_list if s["market"] == "KR"]
            us_risk = [s for s in risk_list if s["market"] == "US"]
            cn_risk = [s for s in risk_list if s["market"] == "CN"]
            if kr_risk:
                lines.append(" <b>[국내]</b>")
                for s in kr_risk:
                    lines.append(f"  • <b>{s['name']}</b> (₩{int(s['curr_price']):,}): {s['tech_comment']}")
            if us_risk:
                lines.append(" <b>[미국]</b>")
                for s in us_risk:
                    lines.append(f"  • <b>{s['name']}</b> (${s['curr_price']:.2f}): {s['tech_comment']}")
            if cn_risk:
                lines.append(" <b>[중국/홍콩]</b>")
                for s in cn_risk:
                    sym = get_currency_symbol(s["code"], s["market"])
                    lines.append(f"  • <b>{s['name']}</b> ({sym}{s['curr_price']:.2f}): {s['tech_comment']}")
    else:
        lines.append("• 주요 이평선(20일/60일선) 또는 전고점/전저점 임계치(±2%)에 근접한 종목이 없습니다.")

    if spreadsheet_id:
        lines.append("")
        lines.append("─────────────────────")
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        lines.append(f"📋 <a href=\"{sheet_url}\">구글 시트 바로가기</a>")

    return "\n".join(lines)

def send_telegram_message(text: str, bot_token: str, chat_id: str) -> bool:
    """
    텔레그램 봇 API를 통해 메시지를 전송합니다 (HTML 서식 적용).
    """
    if not bot_token or not chat_id:
        print("[NOTI WARNING] Telegram bot_token 또는 chat_id가 설정되지 않았습니다.")
        print("\n=== [리포트 콘솔 미리보기] ===\n")
        # 태그 제거한 일반 텍스트로 콘솔 출력
        import re
        clean_text = re.sub(r"<[^>]+>", "", text)
        print(clean_text)
        print("\n==============================\n")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # 텔레그램 글자 수 제한 (4096자) 대응: 필요한 경우 분할 발송
    MAX_LEN = 4000
    parts = []
    if len(text) > MAX_LEN:
        split_lines = text.split("\n")
        curr = ""
        for line in split_lines:
            if len(curr) + len(line) + 1 > MAX_LEN:
                parts.append(curr)
                curr = line + "\n"
            else:
                curr += line + "\n"
        if curr:
            parts.append(curr)
    else:
        parts = [text]

    success = True
    for p in parts:
        payload = {
            "chat_id": chat_id,
            "text": p,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code != 200:
                print(f"[NOTI ERROR] 텔레그램 전송 실패: {resp.text}")
                success = False
            else:
                print("[NOTI SUCCESS] 텔레그램 메시지 발송 완료")
        except Exception as e:
            print(f"[NOTI ERROR] 텔레그램 전송 중 예외 발생: {e}")
            success = False

    return success

if __name__ == "__main__":
    test_changes = [{
        "name": "삼성전자",
        "code": "005930",
        "sheet": "한국주식",
        "market": "KR",
        "change_type": "상향(▲)",
        "old_tp": 480000.0,
        "new_tp": 490000.0,
        "change_rate_pct": 2.1,
        "upside_str": "+77.5%"
    }]
    test_signals = [
        {
            "name": "삼성전자",
            "code": "005930",
            "market": "KR",
            "curr_price": 276000.0,
            "tech_action": "단기 매수 관심",
            "tech_comment": "20일선(₩265,700) 단기 지지 반등 시도 (+1.8%)"
        },
        {
            "name": "테슬라",
            "code": "TSLA",
            "market": "US",
            "curr_price": 370.59,
            "tech_action": "분할 익절 / 돌파 대기",
            "tech_comment": "60일 최고점($420.00) 저항대 근접 (-11.8%)"
        }
    ]
    report = format_telegram_report("2026-10-05", test_changes, test_signals, "test-sheet-id")
    send_telegram_message(report, "", "")
