import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any

from sheet_client import load_config, get_all_stocks, push_updates_to_sheet
from data_collector import get_kr_stock_info, get_us_stock_info
from technical_analyzer import analyze_technical_levels
from consensus_tracker import evaluate_consensus_change
from notifier import format_telegram_report, send_telegram_message

def run_monitoring_pipeline(dry_run: bool = False, limit: int = None):
    print("=" * 60)
    print(f"🚀 [주식 모니터링 시스템 실행] - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if dry_run:
        print("⚠️ [DRY-RUN 모드] 시트 수정 및 텔레그램 실제 발송은 건너뜁니다.")
    print("=" * 60)

    config = load_config()
    tech_settings = config.get("analysis_settings", {})
    spreadsheet_id = config.get("spreadsheet_id", "")
    tg_config = config.get("telegram", {})
    bot_token = tg_config.get("bot_token", "")
    chat_id = tg_config.get("chat_id", "")

    # 1. 구글 시트에서 최신 종목 목록 읽기
    print("\n[1/4] 📥 구글 시트 종목 데이터 동기화 중...")
    stocks_by_sheet = get_all_stocks(config)
    total_stocks = sum(len(v) for v in stocks_by_sheet.values())
    print(f"  총 {total_stocks}개 종목 로드 완료")
    for s_name, s_list in stocks_by_sheet.items():
        print(f"  - {s_name}: {len(s_list)}개 종목")

    # 2. 데이터 수집 및 분석 수행
    print("\n[2/4] 🔍 주가, 컨센서스 및 기술적 지표 분석 진행 중...")
    sheet_updates = []
    consensus_changes = []
    timing_signals = []

    min_change_pct = tech_settings.get("min_consensus_change_pct", 3.0)

    for sheet_name, stock_list in stocks_by_sheet.items():
        if limit and limit > 0:
            stock_list = stock_list[:limit]

        print(f"\n  ▶ '{sheet_name}' 분석 중 ({len(stock_list)}종목)...")
        for idx, stock in enumerate(stock_list, 1):
            name = stock["name"]
            code = stock["code"]
            market = stock["market"]

            try:
                # 데이터 수집
                if market == "KR":
                    info = get_kr_stock_info(code)
                else:
                    info = get_us_stock_info(code)

                if not info or info.get("current_price") is None:
                    print(f"    [{idx}/{len(stock_list)}] {name}({code}): 주가 데이터 없음 (건너뜀)")
                    continue

                # 기술적 분석 (20/60일선, 고점/저점)
                tech_res = analyze_technical_levels(info, tech_settings)

                # 컨센서스 변동 감지 및 시트 수정 항목 생성 (주요 변동 기준 적용)
                is_changed, update_item, alert_item = evaluate_consensus_change(
                    stock, info, tech_res, min_change_pct=min_change_pct
                )

                # 항상 '최근 업데이트 항목' 또는 목표가 변경 사항을 시트에 반영
                if update_item:
                    sheet_updates.append(update_item)

                # 텔레그램 알림용: 주요 변동(|변동률| >= min_change_pct 또는 신규)만 포함
                if alert_item.get("is_major_change"):
                    consensus_changes.append(alert_item)
                    print(f"    🎯 [주요 목표가 변동] {name}: {alert_item['change_type']} {alert_item.get('upside_str')}")

                # 텔레그램 알림용: 유효 신호가 있고 '관망'이 아닌 명확한 액션 타점만 포함
                if tech_res.get("has_signal") and "관망" not in alert_item.get("tech_action", ""):
                    timing_signals.append(alert_item)
                    print(f"    📈 [타이밍 포착] {name}: {tech_res.get('timing_comment')}")

            except Exception as e:
                print(f"    ⚠️ {name}({code}) 처리 중 오류: {e}")

    print(f"\n  분석 완료 요약:")
    print(f"  - 주요 목표주가 변동: {len(consensus_changes)}개 (기준: ±{min_change_pct}% 이상)")
    print(f"  - 액션 타이밍 포착: {len(timing_signals)}개 (관망 제외)")
    print(f"  - 시트 갱신 대상: {len(sheet_updates)}건")

    # 3. 구글 시트 업데이트 전송
    print("\n[3/4] 📝 구글 시트 '최근 업데이트 항목' 및 목표주가 반영 중...")
    if dry_run:
        print("  [DRY-RUN] 시트 반영을 건너뜁니다.")
    else:
        if sheet_updates:
            res = push_updates_to_sheet(sheet_updates, config)
            print(f"  시트 갱신 결과: {res.get('status')} ({res.get('message', '정상 완료')})")
        else:
            print("  시트에 업데이트할 항목이 없습니다.")

    # 4. 텔레그램 리포트 포맷팅 및 발송
    print("\n[4/4] 📢 텔레그램 일일 브리핑 리포트 발송 중...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    report_text = format_telegram_report(
        date_str=today_str,
        consensus_changes=consensus_changes,
        timing_signals=timing_signals,
        spreadsheet_id=spreadsheet_id
    )

    if dry_run:
        print("\n=== [리포트 미리보기] ===")
        import re
        print(re.sub(r"<[^>]+>", "", report_text))
        print("========================\n")
    else:
        send_telegram_message(report_text, bot_token, chat_id)

    print("\n✅ [모든 작업이 성공적으로 완료되었습니다.]\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="주식 모니터링 및 텔레그램 알림 시스템")
    parser.add_argument("--dry-run", action="store_true", help="시트 수정 및 텔레그램 발송을 건너뛰고 분석만 수행")
    parser.add_argument("--limit", type=int, default=None, help="테스트용으로 시트당 N개 종목만 분석")
    args = parser.parse_args()

    run_monitoring_pipeline(dry_run=args.dry_run, limit=args.limit)
