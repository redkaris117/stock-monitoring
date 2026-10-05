#!/bin/bash

# 매일 저녁 9시 (21:00) 주식 모니터링 자동 실행 스케줄러 등록 스크립트

PLIST_NAME="com.stockmonitoring.daily.plist"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/$PLIST_NAME"
CURRENT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"

if [ ! -f "$PYTHON_PATH" ]; then
    PYTHON_PATH=$(which python3)
fi

echo "============================================================"
echo "🕒 주식 모니터링 저녁 9시(21:00) 자동 스케줄러 설정"
echo "============================================================"
echo "작업 디렉토리: $CURRENT_DIR"
echo "파이썬 경로: $PYTHON_PATH"

mkdir -p "$TARGET_DIR"

if [ "$1" == "uninstall" ]; then
    echo "스케줄러 등록 해제 중..."
    launchctl unload "$TARGET_PLIST" 2>/dev/null
    rm -f "$TARGET_PLIST"
    echo "✅ 스케줄러가 성공적으로 삭제되었습니다."
    exit 0
fi

# 기존 등록 해제
launchctl unload "$TARGET_PLIST" 2>/dev/null

cat <<EOF > "$TARGET_PLIST"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.stockmonitoring.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$CURRENT_DIR/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$CURRENT_DIR</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>21</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$CURRENT_DIR/monitoring.log</string>
    <key>StandardErrorPath</key>
    <string>$CURRENT_DIR/monitoring_error.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

# 등록 및 로드
launchctl load "$TARGET_PLIST"

echo "✅ 스케줄러 등록 완료!"
echo "• 실행 시각: 매일 저녁 9시 (21:00:00)"
echo "• 로그 파일: $CURRENT_DIR/monitoring.log"
echo "• 등록 파일: $TARGET_PLIST"
echo ""
echo "※ 등록을 해제하려면: ./setup_schedule.sh uninstall"
