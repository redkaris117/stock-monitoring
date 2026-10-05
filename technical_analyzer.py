from typing import Dict, Any, Optional

def analyze_technical_levels(stock_info: Dict[str, Any], settings: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    당일 종가 기준으로 20일선/60일선 및 직전 고점/저점과의 이격도를 계산하고
    매수/매도 타이밍 관점의 신호 및 코멘트를 생성합니다.
    """
    if not stock_info or "current_price" not in stock_info:
        return {"has_signal": False, "signals": [], "action_type": "데이터 없음", "timing_comment": ""}

    if settings is None:
        settings = {
            "ma_proximity_percent": 1.2,
            "resistance_proximity_percent": 1.5,
            "support_proximity_percent": 1.5
        }

    price = stock_info["current_price"]
    ma20 = stock_info.get("ma20")
    ma60 = stock_info.get("ma60")
    high_60d = stock_info.get("high_60d")
    low_60d = stock_info.get("low_60d")
    market = stock_info.get("market", "KR")
    curr_symbol = "₩" if market == "KR" else "$"

    ma_threshold = settings.get("ma_proximity_percent", 1.2)
    res_threshold = settings.get("resistance_proximity_percent", 1.5)
    sup_threshold = settings.get("support_proximity_percent", 1.5)

    signals = []
    action_types = []
    comments = []

    # 1. 20일 이동평균선 이격도 분석
    if ma20 and ma20 > 0:
        diff_ma20_pct = ((price - ma20) / ma20) * 100
        if 0.0 <= diff_ma20_pct <= ma_threshold:
            signals.append("20일선 지지")
            action_types.append("단기 매수 관심")
            comments.append(f"20일선({curr_symbol}{ma20:,.0f}) 단기 지지 반등 시도 (+{diff_ma20_pct:.1f}%)" if market == "KR" else f"20일선({curr_symbol}{ma20:.2f}) 단기 지지 반등 시도 (+{diff_ma20_pct:.1f}%)")
        elif -ma_threshold <= diff_ma20_pct < 0.0:
            signals.append("20일선 이탈 주의")
            action_types.append("단기 주의/관망")
            comments.append(f"20일선({curr_symbol}{ma20:,.0f}) 하향 이탈 주의 ({diff_ma20_pct:.1f}%)" if market == "KR" else f"20일선({curr_symbol}{ma20:.2f}) 하향 이탈 주의 ({diff_ma20_pct:.1f}%)")

    # 2. 60일 이동평균선 이격도 분석 (중기 지지선)
    if ma60 and ma60 > 0:
        diff_ma60_pct = ((price - ma60) / ma60) * 100
        if -1.0 <= diff_ma60_pct <= ma_threshold:
            signals.append("60일선 중기 지지")
            action_types.append("중기 분할 매수")
            comments.append(f"60일선({curr_symbol}{ma60:,.0f}) 중기 지지선 안착 (+{diff_ma60_pct:.1f}%)" if market == "KR" else f"60일선({curr_symbol}{ma60:.2f}) 중기 지지선 안착 (+{diff_ma60_pct:.1f}%)")

    # 3. 최근 60일 전고점(저항선) 근접 분석
    if high_60d and high_60d > 0:
        diff_high_pct = ((price - high_60d) / high_60d) * 100
        if -res_threshold <= diff_high_pct <= 0.0:
            signals.append("전고점 저항 근접")
            action_types.append("분할 익절 / 돌파 대기")
            comments.append(f"60일 최고점({curr_symbol}{high_60d:,.0f}) 저항대 근접 ({diff_high_pct:.1f}%)" if market == "KR" else f"60일 최고점({curr_symbol}{high_60d:.2f}) 저항대 근접 ({diff_high_pct:.1f}%)")
        elif diff_high_pct > 0.0:
            signals.append("신고가 돌파")
            action_types.append("상승 추세 추종")
            comments.append(f"60일 신고가 돌파 (+{diff_high_pct:.1f}%)")

    # 4. 최근 60일 전저점(바닥권 지지) 근접 분석
    if low_60d and low_60d > 0:
        diff_low_pct = ((price - low_60d) / low_60d) * 100
        if 0.0 <= diff_low_pct <= sup_threshold:
            signals.append("전저점 바닥 지지")
            action_types.append("기술적 반등 매수")
            comments.append(f"60일 최저점({curr_symbol}{low_60d:,.0f}) 바닥 지지 테스트 (+{diff_low_pct:.1f}%)" if market == "KR" else f"60일 최저점({curr_symbol}{low_60d:.2f}) 바닥 지지 테스트 (+{diff_low_pct:.1f}%)")

    has_signal = len(signals) > 0
    main_action = " / ".join(list(dict.fromkeys(action_types))) if action_types else "추세 유지/관망"
    full_comment = " | ".join(comments) if comments else "주요 지지/저항선 사이 중립 구간"

    return {
        "has_signal": has_signal,
        "signals": signals,
        "action_type": main_action,
        "timing_comment": full_comment,
        "levels": {
            "current_price": price,
            "ma20": ma20,
            "ma60": ma60,
            "high_60d": high_60d,
            "low_60d": low_60d
        }
    }

if __name__ == "__main__":
    test_kr = {
        "market": "KR",
        "current_price": 276000,
        "ma20": 273000,
        "ma60": 260000,
        "high_60d": 280000,
        "low_60d": 200000
    }
    res = analyze_technical_levels(test_kr)
    print("Test KR Result:")
    print("Has Signal:", res["has_signal"])
    print("Action:", res["action_type"])
    print("Comment:", res["timing_comment"])
