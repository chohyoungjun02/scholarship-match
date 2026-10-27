"""잡아바 어플라이(경기도 일자리재단 통합접수) 진행 중 지원사업 크롤러.

목록을 화면에서 자바스크립트로 불러오므로 그 API(getBsnsList.do)를 직접 호출한다.
목록 응답에 본문(contents)까지 들어 있어 상세 페이지를 따로 열 필요가 없다.
"""
import html
import json
import re

import requests
from bs4 import BeautifulSoup

from models import REGIONS

from .base import HEADERS

API = "https://apply.jobaba.net/bsns/getBsnsList.do?_REQ_DATA_TYPE_=json&_USE_WRAPPED_OBJECT_=true"
DETAIL = "https://apply.jobaba.net/bsns/bsnsDetailView.do?bsnsSeq={}"
# shortcut: 제목·태그 키워드로 '대학생 대상' + '돈으로 받는 지원'만 고름, 사업 대상 필드가 생기면 그걸로 교체
KEYWORDS = ["청년", "대학", "학생", "장학", "학자금", "등록금"]
MONEY = ["지원", "수당", "이자", "장학", "학자금", "등록금", "포인트"]
EXCLUDE = ["참여기업", "기업 등록", "사업장", "특강", "교육생"]


def region_of(address, title):
    """사업 대상 시·군. 주소("경기도 이천시")가 비어 있으면 제목 머리말("[파주시]")로, 경기도 전체 사업이면 None"""
    for word in (address or "").split() + re.findall(r"\[([^\]]+)\]", title):
        if word in REGIONS:
            return word
    return None


def crawl(delay=0.5):
    try:
        param = {"statusCd": "", "newSortTarget": "01", "listBlock": "200",
                 "schLocation": ["4100000000"], "schBsnsType": []}  # 4100000000 = 경기도
        res = requests.post(API, data={"_REQ_JSON_OBJECT_": json.dumps(param)},
                            headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"}, timeout=20, verify=False)
        res.raise_for_status()
        rows = res.json()["data"]["list"]
    except Exception as e:
        return [], [f"잡아바어플라이: {e}"]

    posts = []
    for row in rows:
        title = html.unescape(row["bsnsTitle"]).strip()
        text = title + " " + (row.get("tag") or "")
        if (not any(k in text for k in KEYWORDS) or not any(k in title for k in MONEY)
                or any(k in title for k in EXCLUDE)):
            continue
        body = BeautifulSoup(html.unescape(row.get("contents") or ""), "html.parser").get_text(" ", strip=True)
        period = f"신청기간 {row['bsnsStartDate']} ~ {row['bsnsEndDate']}"
        region = row.get("adstrdAdres") or "경기도"
        posts.append({
            "title": title,
            "url": DETAIL.format(row["bsnsSeq"]),
            "posted_at": row.get("bsnsStartDate"),
            "body": f"{period} · {region} · " + " ".join(body.split()),
            "source": "잡아바어플라이",
            "region": region_of(row.get("adstrdAdres"), title),
        })
    return posts, []
