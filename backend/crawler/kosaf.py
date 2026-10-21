"""한국장학재단 공지사항 크롤러 (장학 관련 공지만 수집)."""
import re

from .base import get_soup, parse_board

SEQ_RE = re.compile(r"seqNo=(\d+)")

BASE = "https://www.kosaf.go.kr"
BOARDS = [
    {"name": "공지사항", "url": BASE + "/ko/notice.do"},
]
# 공지사항 목록 표의 제목 칸만 대상으로 한다 (헤더/푸터 링크 제외)
LINK_SELECTOR = "table.t-viewz td.subject a"
KEYWORDS = ["장학", "근로", "다자녀", "국가장학", "학자금 지원구간"]
PAGES = 3  # 공지가 많아 장학 글이 앞쪽에 몇 개 없으므로 여러 페이지를 본다


def crawl(delay=0.5):
    posts, errors = [], []
    for board in BOARDS:
        for page in range(1, PAGES + 1):
            url = f"{board['url']}?page={page}"
            try:
                found = parse_board(get_soup(url, delay), url, KEYWORDS, LINK_SELECTOR)
                for p in found:
                    p["source"] = "한국장학재단"
                    # 목록 링크에는 page= 값이 들어 있어 글이 밀리면 주소가 바뀐다 → seqNo만 남긴다
                    m = SEQ_RE.search(p["url"])
                    if m:
                        p["url"] = f"{board['url']}?mode=view&seqNo={m.group(1)}"
                posts.extend(found)
            except Exception as e:
                errors.append(f"{board['name']} {page}p: {e}")
    return posts, errors
