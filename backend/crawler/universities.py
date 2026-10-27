"""서비스 대상 대학 (경기도 전체) 과 각 대학의 장학 공지 게시판 설정.

새 대학을 추가하려면 UNIVERSITIES 에 항목을 하나 추가하면 된다.
- boards[].url       : 게시판 목록 주소
- boards[].selector  : 목록에서 글 링크를 찾는 CSS selector (생략 시 범용 selector)
- boards[].view_patterns : onclick 으로 상세를 여는 게시판일 때 (정규식, URL 템플릿)
- boards[].type      : "html"(기본) / "ssc_api" / "auto"
- boards 를 생략하면 homepage 메뉴에서 장학 게시판을 자동으로 찾는다 (crawl_auto)
"""
import base64
import re
import time
from urllib.parse import quote, urlencode, urljoin, urlparse

from bs4 import BeautifulSoup

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
    # ---------------- 그 밖의 경기도 대학: 게시판 자동 탐색 (boards 없음) ----------------
    {"id": "gachon", "name": "가천대학교", "short": "가천대", "city": "성남시", "homepage": "https://www.gachon.ac.kr"},
    {"id": "eulji", "name": "을지대학교", "short": "을지대", "city": "성남시", "homepage": "https://www.eulji.ac.kr", "campus": "성남캠퍼스"},
    {"id": "dsc", "name": "동서울대학교", "short": "동서울대", "city": "성남시", "homepage": "https://www.dsc.ac.kr"},
    {"id": "shingu", "name": "신구대학교", "short": "신구대", "city": "성남시", "homepage": "https://www.shingu.ac.kr"},
    {"id": "catholic", "name": "가톨릭대학교", "short": "가톨릭대", "city": "부천시", "homepage": "https://www.catholic.ac.kr", "campus": "성심교정"},
    {"id": "stu", "name": "서울신학대학교", "short": "서울신대", "city": "부천시", "homepage": "https://www.stu.ac.kr"},
    {"id": "bc", "name": "부천대학교", "short": "부천대", "city": "부천시", "homepage": "https://www.bc.ac.kr"},
    {"id": "yuhan", "name": "유한대학교", "short": "유한대", "city": "부천시", "homepage": "https://www.yuhan.ac.kr"},
    {"id": "kangnam", "name": "강남대학교", "short": "강남대", "city": "용인시", "homepage": "https://web.kangnam.ac.kr"},
    {"id": "khu", "name": "경희대학교", "short": "경희대", "city": "용인시", "homepage": "https://www.khu.ac.kr", "campus": "국제캠퍼스"},
    {"id": "dankook", "name": "단국대학교", "short": "단국대", "city": "용인시", "homepage": "https://www.dankook.ac.kr", "campus": "죽전캠퍼스"},
    {"id": "ltu", "name": "루터대학교", "short": "루터대", "city": "용인시", "homepage": "https://www.ltu.ac.kr"},
    {"id": "mju", "name": "명지대학교", "short": "명지대", "city": "용인시", "homepage": "https://www.mju.ac.kr", "campus": "자연캠퍼스"},
    {"id": "yongin", "name": "용인대학교", "short": "용인대", "city": "용인시", "homepage": "https://www.yongin.ac.kr"},
    {"id": "hufs", "name": "한국외국어대학교", "short": "한국외대", "city": "용인시", "homepage": "https://www.hufs.ac.kr", "campus": "글로벌캠퍼스"},
    {"id": "calvin", "name": "칼빈대학교", "short": "칼빈대", "city": "용인시", "homepage": "https://www.calvin.ac.kr"},
    {"id": "yiu", "name": "용인예술과학대학교", "short": "용인예술과학대", "city": "용인시", "homepage": "https://www.yiu.ac.kr"},
    {"id": "sungkyul", "name": "성결대학교", "short": "성결대", "city": "안양시", "homepage": "https://www.sungkyul.ac.kr"},
    {"id": "anyang", "name": "안양대학교", "short": "안양대", "city": "안양시", "homepage": "https://www.anyang.ac.kr"},
    {"id": "daelim", "name": "대림대학교", "short": "대림대", "city": "안양시", "homepage": "https://www.daelim.ac.kr"},
    {"id": "yeonsung", "name": "연성대학교", "short": "연성대", "city": "안양시", "homepage": "https://www.yeonsung.ac.kr"},
    {"id": "hanyang", "name": "한양대학교", "short": "한양대", "city": "안산시", "homepage": "https://www.hanyang.ac.kr", "campus": "ERICA캠퍼스"},
    {"id": "sau", "name": "신안산대학교", "short": "신안산대", "city": "안산시", "homepage": "https://www.sau.ac.kr"},
    {"id": "ansan", "name": "안산대학교", "short": "안산대", "city": "안산시", "homepage": "https://www.ansan.ac.kr"},
    {"id": "seoularts", "name": "서울예술대학교", "short": "서울예대", "city": "안산시", "homepage": "https://www.seoularts.ac.kr"},
    {"id": "kau", "name": "한국항공대학교", "short": "한국항공대", "city": "고양시", "homepage": "https://www.kau.ac.kr"},
    {"id": "dongguk", "name": "동국대학교", "short": "동국대", "city": "고양시", "homepage": "https://www.dongguk.edu", "campus": "바이오메디캠퍼스"},
    {"id": "joongbu", "name": "중부대학교", "short": "중부대", "city": "고양시", "homepage": "https://www.joongbu.ac.kr", "campus": "고양캠퍼스"},
    {"id": "nonghyup", "name": "농협대학교", "short": "농협대", "city": "고양시", "homepage": "https://www.nonghyup.ac.kr"},
    {"id": "tukorea", "name": "한국공학대학교", "short": "한국공학대", "city": "시흥시", "homepage": "https://www.tukorea.ac.kr"},
    {"id": "gtec", "name": "경기과학기술대학교", "short": "경기과기대", "city": "시흥시", "homepage": "https://www.gtec.ac.kr"},
    {"id": "cau", "name": "중앙대학교", "short": "중앙대", "city": "안성시", "homepage": "https://www.cau.ac.kr", "campus": "다빈치캠퍼스"},
    {"id": "hknu", "name": "한경국립대학교", "short": "한경국립대", "city": "안성시", "homepage": "https://www.hknu.ac.kr"},
    {"id": "dima", "name": "동아방송예술대학교", "short": "동아방송예대", "city": "안성시", "homepage": "https://www.dima.ac.kr"},
    {"id": "doowon", "name": "두원공과대학교", "short": "두원공대", "city": "안성시", "homepage": "https://www.doowon.ac.kr"},
    {"id": "ptu", "name": "평택대학교", "short": "평택대", "city": "평택시", "homepage": "https://www.ptu.ac.kr"},
    {"id": "kookje", "name": "국제대학교", "short": "국제대", "city": "평택시", "homepage": "https://www.kookje.ac.kr"},
    {"id": "hanrw", "name": "한국복지대학교", "short": "한국복지대", "city": "평택시", "homepage": "https://www.hanrw.ac.kr"},
    {"id": "daejin", "name": "대진대학교", "short": "대진대", "city": "포천시", "homepage": "https://www.daejin.ac.kr"},
    {"id": "cha", "name": "차의과학대학교", "short": "차의과학대", "city": "포천시", "homepage": "https://www.cha.ac.kr"},
    {"id": "shinhan", "name": "신한대학교", "short": "신한대", "city": "의정부시", "homepage": "https://www.shinhan.ac.kr"},
    {"id": "kyungmin", "name": "경민대학교", "short": "경민대", "city": "의정부시", "homepage": "https://www.kyungmin.ac.kr"},
    {"id": "hansei", "name": "한세대학교", "short": "한세대", "city": "군포시", "homepage": "https://www.hansei.ac.kr"},
    {"id": "kduniv", "name": "경동대학교", "short": "경동대", "city": "양주시", "homepage": "https://www.kduniv.ac.kr", "campus": "메트로폴캠퍼스"},
    {"id": "yewon", "name": "예원예술대학교", "short": "예원예대", "city": "양주시", "homepage": "https://www.yewon.ac.kr", "campus": "경기캠퍼스"},
    {"id": "seojeong", "name": "서정대학교", "short": "서정대", "city": "양주시", "homepage": "https://www.seojeong.ac.kr"},
    {"id": "sjs", "name": "서울장신대학교", "short": "서울장신대", "city": "광주시", "homepage": "https://www.sjs.ac.kr"},
    {"id": "tw", "name": "동원대학교", "short": "동원대", "city": "광주시", "homepage": "https://www.tw.ac.kr"},
    {"id": "kbu", "name": "경복대학교", "short": "경복대", "city": "남양주시", "homepage": "https://www.kbu.ac.kr"},
    {"id": "kaywon", "name": "계원예술대학교", "short": "계원예대", "city": "의왕시", "homepage": "https://www.kaywon.ac.kr"},
    {"id": "kimpo", "name": "김포대학교", "short": "김포대", "city": "김포시", "homepage": "https://www.kimpo.ac.kr"},
    {"id": "yit", "name": "여주대학교", "short": "여주대", "city": "여주시", "homepage": "https://www.yit.ac.kr"},
    {"id": "ck", "name": "청강문화산업대학교", "short": "청강대", "city": "이천시", "homepage": "https://www.ck.ac.kr"},
    {"id": "ktc", "name": "한국관광대학교", "short": "한국관광대", "city": "이천시", "homepage": "https://www.ktc.ac.kr"},
    {"id": "wat", "name": "웅지세무대학교", "short": "웅지세무대", "city": "파주시", "homepage": "https://www.wat.ac.kr"},
    {"id": "suwoncatholic", "name": "수원가톨릭대학교", "short": "수원가톨릭대", "city": "화성시", "homepage": "https://www.suwoncatholic.ac.kr"},
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


REDIRECT_RE = re.compile(r"""(?:location\.(?:href|replace)\s*\(?\s*=?\s*|http-equiv=["']?refresh["']?[^>]*url=)['"]?([^'"\s>)]+)""", re.I)
# 메뉴 글자로 게시판 찾기: 앞쪽 패턴일수록 우선. '장학'만 들어간 메뉴(장학제도·장학안내)는 소개 페이지인 경우가 많아 마지막
BOARD_LINK_PATTERNS = [r"장학\s*(공지|게시|소식|뉴스)", r"장학\s*[/·ㆍ및,]\s*(대출|학자금)", r"^장학금?$",
                       r"^(통합|일반|대학|학사)?\s*공지(사항)?$", r"장학"]
MAIN_LINK_RE = re.compile(r"main|index|home|/kor|/ko/|/www", re.I)


def _same_site(url, home):
    """학교 도메인(www.·web. 뗀 주소)과 같은 사이트인지 - 바깥 링크(국세청 등)를 게시글로 잡지 않도록"""
    root = re.sub(r"^(www|web)\.", "", urlparse(home).hostname or "")
    return (urlparse(url).hostname or "").endswith(root)


def _home_soup(url, delay):
    """홈페이지를 연다. 자바스크립트/meta 리다이렉트만 있거나 링크가 거의 없는 인트로 페이지면 메인으로 따라간다."""
    for _ in range(3):
        text = get_text(url, delay)
        soup = BeautifulSoup(text, "html.parser")
        m = REDIRECT_RE.search(text) if len(text) < 8000 else None
        if m:
            url = urljoin(url, m.group(1))
            continue
        links = soup.select("a[href]")
        if len(links) >= 30:
            break
        main = next((urljoin(url, a["href"]) for a in links
                     if MAIN_LINK_RE.search(a["href"]) and _same_site(urljoin(url, a["href"]), url)
                     and urljoin(url, a["href"]) != url), None)
        if not main:
            break
        url = main
    return soup, url


def crawl_auto(board, delay):
    """게시판 설정이 없는 학교: 홈페이지 메뉴에서 장학 게시판을 찾아 크롤링한다.
    shortcut: 메뉴 글자 기반 추측이라 메뉴를 자바스크립트로 그리는 학교는 실패함, 그런 학교는 UNIVERSITIES 에 boards 를 직접 지정"""
    soup, home = _home_soup(board["url"], delay)
    candidates, tried = _board_links(soup, home, BOARD_LINK_PATTERNS), set()
    deadline = time.monotonic() + 35  # 서버리스 60초 제한 안에서 끝내기
    while candidates and len(tried) < 8 and time.monotonic() < deadline:
        url = candidates.pop(0)
        if url in tried:
            continue
        tried.add(url)
        try:
            soup = get_soup(url, delay)
        except Exception:
            continue
        posts = parse_board(soup, url, SCHOLAR_KEYWORDS)
        if not posts:  # 범용 selector 로 못 찾으면 모든 링크 중 날짜가 붙은 줄(게시글)만
            posts = [p for p in parse_board(soup, url, SCHOLAR_KEYWORDS, selector="a") if p["posted_at"]]
        posts = [p for p in posts if len(p["title"]) >= 8 and _same_site(p["url"], home)]
        if posts:
            return posts
        # 장학 소개 페이지 안의 하위 메뉴(장학공지 등)를 다음 후보 맨 앞에 넣는다
        candidates[:0] = [u for u in _board_links(soup, url, BOARD_LINK_PATTERNS[:3]) if u not in tried]
    raise RuntimeError("장학 게시판을 자동으로 찾지 못했어요")


def _board_links(soup, base, patterns):
    links = [(" ".join(a.get_text(" ", strip=True).split()), urljoin(base, a["href"]))
             for a in soup.select("a[href]") if not a["href"].startswith(("#", "javascript", "mailto"))]
    found = []
    for pattern in patterns:
        for text, url in links:
            if re.search(pattern, text) and len(text) < 20 and url not in found and _same_site(url, base):
                found.append(url)
    return found


BOARD_TYPES = {"html": crawl_html_board, "ssc_api": crawl_ssc_api, "auto": crawl_auto}


def crawl(university, delay=0.5):
    posts, errors = [], []
    boards = university.get("boards") or [{"name": "자동 탐색", "type": "auto", "url": university["homepage"]}]
    for board in boards:
        try:
            found = BOARD_TYPES[board.get("type", "html")](board, delay)
            for p in found:
                p["source"] = university["short"]
                p["university_id"] = university["id"]
            posts.extend(found)
        except Exception as e:  # 한 게시판이 실패해도 나머지는 계속
            errors.append(f"{university['short']} {board['name']}: {e}")
    return posts, errors
