"""수원시육아종합지원센터 백일·돌상 11월 6일/13일 빈자리 감시 → 텔레그램 알림"""
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

URL = "https://www.suwonscc.or.kr/care/toy/appRent.asp?datToday=202611"
TARGET_DAYS = ["6", "13"]
SLOTS = 4  # 금요일마다 4칸
KST = timezone(timedelta(hours=9))
END = datetime(2026, 11, 13, 23, 59, tzinfo=KST)


class Cells(HTMLParser):
    """캘린더의 <td> 칸마다 글자를 모은다."""

    def __init__(self):
        super().__init__()
        self.cells, self.in_td = [], False

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            self.cells.append("")
            self.in_td = True

    def handle_endtag(self, tag):
        if tag == "td":
            self.in_td = False

    def handle_data(self, data):
        if self.in_td:
            self.cells[-1] += data + " "


def open_counts(html):
    """{날짜: 열린 칸 수} 반환. 날짜 칸을 못 찾으면 에러(사이트 구조 변경)."""
    p = Cells()
    p.feed(html)
    by_day = {c.split()[0]: c for c in p.cells if c.split() and c.split()[0].isdigit()}
    result = {}
    for d in TARGET_DAYS:
        if d not in by_day:
            raise RuntimeError(f"11월 {d}일 칸을 찾지 못함 - 사이트 구조가 바뀐 듯")
        result[d] = SLOTS - by_day[d].count("신청마감")
    return result


def telegram(text):
    token, chat = os.environ["TG_TOKEN"], os.environ["TG_CHAT_ID"]
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data, timeout=20)


def self_test():
    sample = "<table><tr><td>6 신청마감 신청마감 신청마감 신청마감</td>" \
             "<td>13 신청마감 신청하기 신청마감 신청마감</td></tr></table>"
    assert open_counts(sample) == {"6": 0, "13": 1}
    print("self-test OK")


def main():
    if datetime.now(KST) > END:
        print("감시 기간 종료")
        return
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "ko-KR,ko;q=0.9"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    counts = open_counts(html)
    print(counts)

    opened = [d for d, n in counts.items() if n > 0]
    if opened:
        days = ", ".join(f"11월 {d}일({counts[d]}칸)" for d in opened)
        telegram(f"🎉 빈자리 났어요! {days}\n바로 신청: {URL}")
    elif os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        # 수동 실행 시에는 연결 확인용으로 현재 상태를 보냄
        telegram("✅ 감시 작동 중 - 11월 6일, 13일 모두 아직 마감")


if __name__ == "__main__":
    self_test() if "--test" in sys.argv else main()
