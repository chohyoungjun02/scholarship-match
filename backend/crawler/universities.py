"""서비스 대상 대학 (수원시·화성시·오산시) 과 각 대학의 장학 공지 게시판 설정.

새 대학을 추가하려면 UNIVERSITIES 에 항목을 하나 추가하면 된다.
- boards[].url       : 게시판 목록 주소
- boards[].selector  : 목록에서 글 링크를 찾는 CSS selector (생략 시 범용 selector)
- boards[].view_patterns : onclick 으로 상세를 여는 게시판일 때 (정규식, URL 템플릿)
- boards[].type      : "html"(기본) 또는 별도 함수가 필요한 경우의 이름 (custom.py)
"""
import base64
from urllib.parse import quote, urlencode

from .base import SCHOLAR_KEYWORDS, get_soup, get_text, parse_board

UNIVERSITIES = [
    # ---------------- 수원시 ----------------
    {
        "id": "kyonggi", "name": "경기대학교", "short": "경기대", "city": "수원시", "campus": "수원캠퍼스",
        "homepage": "https://www.kyonggi.ac.kr",
        # 통합 공지사항에서 제목에 '장학'이 들어간 글을 검색 (searchCnd=SJ: 제목)
        "boards": [{"name": "공지사항(장학 검색)", "url": "https://www.kyonggi.ac.kr/www/selectBbsNttList.do?key=7520&bbsNo=1073&searchCnd=SJ&searchKrwd=%EC%9E%A5%ED%95%99"}],
    },
    {
        "id": "skku", "name": "성균관대학교", "short": "성균관대", "city": "수원시", "campus": "자연과학캠퍼스",
        "homepage": "https://www.skku.edu",
        "boards": [{"name": "장학 공지", "url": "https://www.skku.edu/skku/campus/skk_comm/notice06.do"}],
    },
    {
        "id": "ajou", "name": "아주대학교", "short": "아주대", "city": "수원시",
        "homepage": "https://www.ajou.ac.kr",
        "boards": [{"name": "장학 공지", "url": "https://www.ajou.ac.kr/kr/ajou/notice_scholarship.do"}],
    },
    {
        "id": "swwu", "name": "수원여자대학교", "short": "수원여대", "city": "수원시",
        "homepage": "https://www.swwu.ac.kr",
        "boards": [{"name": "장학/대출", "url": "https://www.swwu.ac.kr/cop/bbs/BBSMSTR_000000000011/selectBoardList.do?mn=ko"}],
    },
    {
        "id": "dongnam", "name": "동남보건대학교", "short": "동남보건대", "city": "수원시",
        "homepage": "https://www.dongnam.ac.kr",
        "boards": [{"name": "장학/대출", "url": "https://www.dongnam.ac.kr/main/485/subview.do"}],
    },
    # ---------------- 화성시 ----------------
    {
        "id": "suwon", "name": "수원대학교", "short": "수원대", "city": "화성시",
        "homepage": "https://www.suwon.ac.kr",
        "boards": [{
            "name": "장학/대출", "url": "https://www.suwon.ac.kr/index.html?menuno=2041",
            "selector": "ul.board_basic_list a",
            # onclick="return submitForm(this,'view',1031);" → GET ...&act=view&bbsno=1031
            "view_patterns": [(r"submitForm\(this,\s*'view',\s*(\d+)\)", "{page}&act=view&bbsno={0}")],
        }],
    },
    {
        "id": "uhs", "name": "협성대학교", "short": "협성대", "city": "화성시",
        "homepage": "https://www.uhs.ac.kr",
        # 통합공지에서 제목에 '장학'이 들어간 글을 검색
        "boards": [{"name": "통합공지(장학 검색)", "url": "https://www.uhs.ac.kr/portalBbs/uhs/4/list.do?srchColumn=sj&srchWrd=%EC%9E%A5%ED%95%99"}],
    },
    {
        "id": "jangan", "name": "장안대학교", "short": "장안대", "city": "화성시",
        "homepage": "https://www.jangan.ac.kr",
        "boards": [{"name": "장학/대출", "url": "https://www.jangan.ac.kr/jangan/681/subview.do"}],
    },
    {
        "id": "ssc", "name": "수원과학대학교", "short": "수원과학대", "city": "화성시",
        "homepage": "https://www.ssc.ac.kr",
        "boards": [{"name": "장학 및 대출", "type": "ssc_api", "url": "https://www.ssc.ac.kr/plaza/sub040401"}],
    },
    # ---------------- 오산시 ----------------
    {
        "id": "hanshin", "name": "한신대학교", "short": "한신대", "city": "오산시",
        "homepage": "https://www.hs.ac.kr",
        # 장학 공지 게시판 (K2Web). 2페이지 이후는 POST 방식이라 1페이지만 수집
        "boards": [{"name": "장학 공지", "url": "https://www.hs.ac.kr/kor/4957/subview.do"}],
    },
    {
        "id": "osan", "name": "오산대학교", "short": "오산대", "city": "오산시",
        "homepage": "https://www.osan.ac.kr",
        "boards": [{
            "name": "장학공지", "url": "https://www.osan.ac.kr/?menuno=975",
            # 수원대와 같은 CMS: onclick="return submitForm(this,'view',102);"
            "selector": "a[onclick*=\"'view'\"]",
            "view_patterns": [(r"submitForm\(this,\s*'view',\s*(\d+)\)", "{page}&act=view&bbsno={0}")],
        }],
    },
]

BY_ID = {u["id"]: u for u in UNIVERSITIES}


def public_info(u):
    return {k: u.get(k) for k in ("id", "name", "short", "city", "campus", "homepage")}


# ---------------------------------------------------------------------------
# 게시판 타입별 크롤링
# ---------------------------------------------------------------------------
def crawl_html_board(board, delay):
    soup = get_soup(board["url"], delay)
    return parse_board(
        soup, board["url"], board.get("keywords", SCHOLAR_KEYWORDS),
        **({"selector": board["selector"]} if board.get("selector") else {}),
        view_patterns=board.get("view_patterns", ()),
    )


def crawl_ssc_api(board, delay):
    """수원과학대: 목록을 자바스크립트가 JSON API 로 불러오므로 API 를 직접 호출한다.
    목록 응답에 본문(postContent)까지 들어 있어 상세 페이지를 따로 열 필요가 없다."""
    import json
    from bs4 import BeautifulSoup

    api = "https://www.ssc.ac.kr/board/templetList/search?" + urlencode(
        {"page": 1, "pageSize": 20, "boardId": "SSC_SCHOLAR", "postNo": "", "searchDiv": "", "searchWord": ""})
    data = json.loads(get_text(api, delay))["data"]["list"]
    posts = []
    for row in data:
        # 사이트의 상세 이동 방식: /plaza/sub040401_view?query=base64(encodeURI(파라미터))
        params = f"page=1&pageSize=10&boardId=SSC_SCHOLAR&postNo={row['postNo']}&searchDiv=&searchWord="
        query = base64.b64encode(quote(params, safe="=&").encode()).decode()
        body = BeautifulSoup(row.get("postContent") or "", "html.parser").get_text(" ", strip=True)
        date = row.get("regDateYmd")
        posts.append({
            "title": " ".join(row["postTitle"].split()),
            "url": f"https://www.ssc.ac.kr/plaza/sub040401_view?query={query}",
            "posted_at": date,
            "body": " ".join(body.split()),
        })
    return posts


BOARD_TYPES = {"html": crawl_html_board, "ssc_api": crawl_ssc_api}


def crawl(university, delay=0.5):
    posts, errors = [], []
    for board in university["boards"]:
        try:
            found = BOARD_TYPES[board.get("type", "html")](board, delay)
            for p in found:
                p["source"] = university["short"]
                p["university_id"] = university["id"]
            posts.extend(found)
        except Exception as e:  # 한 게시판이 실패해도 나머지는 계속
            errors.append(f"{university['short']} {board['name']}: {e}")
    return posts, errors
