/**
 * 주식 모니터링 자동 갱신용 Google Apps Script Webhook
 * 
 * [배포 방법]
 * 1. 구글 시트 상단 메뉴 [확장 프로그램] -> [Apps Script] 클릭
 * 2. 기존 코드를 모두 지우고 이 파일의 내용을 전체 복사하여 붙여넣기
 * 3. 우측 상단 파란색 [배포] -> [새 배포] 클릭
 * 4. 유형 선택(톱니바퀴) -> [웹 앱] 선택
 * 5. 설명: 주식 모니터링 웹훅
 * 6. 다음 사용자로 실행: '나(내 계정)'
 * 7. 액세스 권한: '모든 사용자(Anyone)' 선택 (로그인 불필요)
 * 8. [배포] 클릭 후 승인 절차 완료 -> 생성된 '웹 앱 URL'을 복사하여 config.json의 webhook_url에 입력!
 */

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({
    status: "ok",
    message: "주식 모니터링 웹훅이 정상 작동 중입니다."
  })).setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return responseJSON({ status: "error", message: "데이터가 비어 있습니다." });
    }

    var data = JSON.parse(e.postData.contents);
    var action = data.action;

    if (action === "ping") {
      return responseJSON({ status: "ok", message: "pong" });
    }

    if (action === "update_stocks") {
      // data: { action: "update_stocks", updates: [ { sheet: "한국주식", ticker: "005930", target_price: "₩480,000", upside: "+73.9%", date: "2026-10-02", source: "...", update_note: "..." }, ... ] }
      var updates = data.updates || [];
      var results = [];
      var ss = SpreadsheetApp.getActiveSpreadsheet();

      // 시트별로 그룹화하여 처리
      var sheetMap = {};
      for (var i = 0; i < updates.length; i++) {
        var u = updates[i];
        if (!sheetMap[u.sheet]) {
          sheetMap[u.sheet] = [];
        }
        sheetMap[u.sheet].push(u);
      }

      for (var sheetName in sheetMap) {
        var sheet = ss.getSheetByName(sheetName);
        if (!sheet) {
          results.push({ sheet: sheetName, status: "error", message: "시트를 찾을 수 없음: " + sheetName });
          continue;
        }

        var sheetUpdates = sheetMap[sheetName];
        var lastRow = sheet.getLastRow();
        var lastCol = sheet.getLastColumn();
        if (lastRow < 2 || lastCol < 1) continue;

        var headerRange = sheet.getRange(1, 1, 1, lastCol);
        var headers = headerRange.getValues()[0];

        // 헤더 인덱스 매핑 (0-based)
        var colMap = {};
        for (var c = 0; c < headers.length; c++) {
          var hName = String(headers[c]).trim();
          colMap[hName] = c + 1; // 1-based column
        }

        var tickerCol = colMap["종목코드"] || colMap["티커"] || colMap["코드"];
        if (!tickerCol) {
          results.push({ sheet: sheetName, status: "error", message: "종목코드/티커 열을 찾을 수 없음" });
          continue;
        }

        // 시트의 모든 코드 읽기
        var codeRange = sheet.getRange(2, tickerCol, lastRow - 1, 1);
        var codes = codeRange.getValues();
        var rowLookup = {};
        for (var r = 0; r < codes.length; r++) {
          var cleanCode = String(codes[r][0]).trim();
          if (cleanCode) {
            rowLookup[cleanCode] = r + 2; // 실제 행 번호 (2부터 시작)
          }
        }

        var updatedCount = 0;
        for (var j = 0; j < sheetUpdates.length; j++) {
          var item = sheetUpdates[j];
          var targetRow = rowLookup[item.ticker];
          if (!targetRow) continue;

          // 목표주가 업데이트
          if (item.target_price !== undefined && colMap["목표주가 (컨센서스)"]) {
            sheet.getRange(targetRow, colMap["목표주가 (컨센서스)"]).setValue(item.target_price);
          }
          // 상승여력 업데이트
          if (item.upside !== undefined && colMap["상승여력"]) {
            sheet.getRange(targetRow, colMap["상승여력"]).setValue(item.upside);
          }
          // 기준일자 업데이트
          if (item.date !== undefined && colMap["기준일자"]) {
            sheet.getRange(targetRow, colMap["기준일자"]).setValue(item.date);
          }
          // 출처 업데이트
          if (item.source !== undefined && colMap["출처"]) {
            sheet.getRange(targetRow, colMap["출처"]).setValue(item.source);
          }
          // 차트 기술적 분석 사항 업데이트 및 배경색 적용
          if (item.tech_note !== undefined && colMap["차트 기술적 분석 사항"]) {
            var techCell = sheet.getRange(targetRow, colMap["차트 기술적 분석 사항"]);
            techCell.setValue(item.tech_note);
            if (item.tech_bg_color) {
              techCell.setBackground(item.tech_bg_color);
            } else {
              techCell.setBackground(null);
            }
          }
          // 목표주가 변동사항 업데이트 및 배경색 적용 (변동이 있을 때만 덮어쓰기하여 기존 기록 유지)
          if (item.consensus_note !== undefined && item.consensus_note !== "" && colMap["목표주가 변동사항"]) {
            var consensusCell = sheet.getRange(targetRow, colMap["목표주가 변동사항"]);
            consensusCell.setValue(item.consensus_note);
            if (item.consensus_bg_color) {
              consensusCell.setBackground(item.consensus_bg_color);
            } else {
              consensusCell.setBackground(null);
            }
          }

          updatedCount++;
        }

        results.push({ sheet: sheetName, status: "success", updatedCount: updatedCount });
      }

      return responseJSON({ status: "success", results: results });
    }

    return responseJSON({ status: "error", message: "알 수 없는 action: " + action });

  } catch (err) {
    return responseJSON({ status: "error", message: err.toString() });
  }
}

function responseJSON(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
