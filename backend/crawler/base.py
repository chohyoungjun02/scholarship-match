"""크롤러 공통 기능: HTTP 요청, 게시판 목록 파싱, 본문에서 자격 조건 추출."""
import re
import time
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

# 일부 대학 사이트는 인증서 체인이 불완전해서 검증을 끄고 요청한다 (공개 게시판 읽기 전용).
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120 Safari/537.36 scholarship-finder"
}
DATE_RE = re.compile(r"(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})")

# 장학 관련 글만 남기기 위한 제목 키워드
SCHOLAR_KEYWORDS = ["장학", "근로", "학자금", "등록금", "대출", "생활비"]

# href 대신 onclick 등의 자바스크립트로 상세 페이지를 여는 게시판 패턴
# (정규식, 상세 URL 템플릿) - 템플릿의 {0},{1}.. 은 정규식 그룹, {page} 는 목록 주소
DEFAULT_VIEW_PATTERNS = [
    # K2Web: jf_viewArtcl('kor', '123', '456')
    (r"jf_viewArtcl\('(\w+)',\s*'(\d+)',\s*'(\d+)'\)", "/bbs/{0}/{1}/{2}/artclView.do"),
    # K2Web 포털게시판: jf_view('uhs', '4', '99257')
    (r"jf_view\('(\w+)',\s*'(\d+)',\s*'(\d+)'\)", "/portalBbs/{0}/{1}/{2}/view.do"),
]

DEFAULT_LINK_SELECTOR = "table tbody a, .board-list a, .board-list-wrap a, ul.board a, .bbs-list a, .list a"
# 목록 제목에 붙는 말머리/표시 제거: "[ 일반공지 ]", "[공지]" 접두어, "새글" 접미어
TITLE_PREFIX_RE = re.compile(r"^\[\s*(?:일반공지|공지)\s*\]\s*")
TITLE_SUFFIX_RE = re.compile(r"\s*(새글|NEW|new|N)$")
JSESSION_RE = re.compile(r";jsessionid=[^?#]*", re.I)
SKIP_URL_RE = re.compile(r"mode=download|fileDown|download\.do|rssList", re.I)
FILE_TITLE_RE = re.compile(r"\.(pdf|hwp|hwpx|docx?|xlsx?|zip|jpg|png)$", re.I)


def get_soup(url, delay=0.5):
    return BeautifulSoup(get_text(url, delay), "html.parser")


def get_text(url, delay=0.5):
    time.sleep(delay)
    res = requests.get(url, headers=HEADERS, timeout=15, verify=False)
    res.raise_for_status()
    if res.encoding in (None, "ISO-8859-1"):
        res.encoding = res.apparent_encoding
    return res.text


def clean_title(text):
    title = " ".join(text.split())
    return TITLE_SUFFIX_RE.sub("", TITLE_PREFIX_RE.sub("", title))


def parse_board(soup, page_url, keywords=None, selector=DEFAULT_LINK_SELECTOR, view_patterns=()):
    """게시판 목록에서 (제목, 링크, 작성일)을 뽑는다.

    사이트마다 구조가 달라서 table/ul 형태를 모두 시도하는 범용 파서다.
    특정 사이트가 잘 안 잡히면 대학 설정(universities.py)에서 selector / view_patterns 를 지정한다.
    상대 링크(?mode=view...)는 목록 페이지 주소(page_url) 기준으로 변환한다.
    """
    patterns = [(re.compile(p), t) for p, t in list(view_patterns) + DEFAULT_VIEW_PATTERNS]
    posts, seen = [], set()
    for a in soup.select(selector):
        title = clean_title(a.get("title") if a.get("title") and len(a.get_text(strip=True)) < 4
                            else a.get_text(" ", strip=True))
        if len(title) < 4 or FILE_TITLE_RE.search(title):
            continue
        href = a.get("href") or ""
        script = href + " " + (a.get("onclick") or "")
        for regex, template in patterns:
            m = regex.search(script)
            if m:
                href = template.format(*m.groups(), page=page_url)
                break
        if not href or href.startswith(("javascript", "#")):
            continue
        url = JSESSION_RE.sub("", urljoin(page_url, href))
        if url in seen or SKIP_URL_RE.search(url):
            continue
        if keywords and not any(k in title for k in keywords):
            continue
        row = a.find_parent(["tr", "li"])
        date = None
        if row:
            dm = DATE_RE.search(row.get_text(" "))
            if dm:
                date = "{}-{:0>2}-{:0>2}".format(*dm.groups())
        seen.add(url)
        posts.append({"title": title, "url": url, "posted_at": date})
    return posts


# 상세 페이지 본문 영역 (대학별 CMS)
BODY_SELECTORS = [
    ".artclView",            # K2Web (장안대, 동남보건대)
    "#VIEW_MCONTENT",        # 한국장학재단
    ".fr-view",              # 아주대·성균관대
    ".b-content-box",        # 아주대·성균관대
    ".iwest_view",           # 협성대 포털게시판
    "#txt",                  # 수원여대
    ".board_view1",          # 오산대
    ".board_view_con",
    ".view_cont", ".view-con", ".view_content", ".board_view", ".board-view",
    ".bbs-view", ".bbsView", ".view_txt", ".board_contents", ".boardContent",
    "#content", "article",
]


def extract_body(soup):
    for sel in BODY_SELECTORS:
        node = soup.select_one(sel)
        if node and len(node.get_text(strip=True)) > 20:
            return " ".join(node.get_text(" ", strip=True).split())
    return " ".join(soup.get_text(" ", strip=True).split())[:3000]


FLAG_KEYWORDS = {
    "basic_livelihood": ["기초생활", "기초수급"],
    "near_poverty": ["차상위"],
    "multi_child": ["다자녀"],
    "disabled": ["장애"],
    "veteran_family": ["국가유공자", "보훈"],
    "single_parent": ["한부모"],
}


def extract_conditions(text):
    """공지 본문에서 자격 조건을 '추정'한다. 정확하지 않을 수 있으므로 결과는 '확인 필요'로 표시된다."""
    cond = {}
    m = re.search(r"(\d{1,2})\s*구간\s*이하", text)
    if m:
        cond["max_income_bracket"] = int(m.group(1))
    m = re.search(r"평[균점][^0-9]{0,10}([1-4]\.\d{1,2})\s*(?:점)?\s*이상", text)
    if m:
        cond["min_gpa"] = float(m.group(1))
    m = re.search(r"(\d{1,2})\s*학점\s*이상", text)
    if m and 6 <= int(m.group(1)) <= 21:
        cond["min_credits"] = int(m.group(1))
    m = re.search(r"([1-4])\s*[~\-]\s*([1-4])\s*학년", text)
    if m:
        cond["min_grade"], cond["max_grade"] = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"([1-4])\s*학년\s*(?:재학생|대상|만)", text)
        if m:
            cond["min_grade"] = cond["max_grade"] = int(m.group(1))
    # 제목/본문 앞부분에 대상자로 명시된 경우만 필수 조건으로 본다.
    head = text[:300]
    flags = [k for k, words in FLAG_KEYWORDS.items() if any(w in head for w in words)]
    if flags:
        cond["required_flags"] = flags
    m = re.search(r"(\d[\d,]*)\s*만\s*원", text)
    if m:
        cond["amount_text"] = m.group(0).replace(" ", "")
    return cond
