"""공공데이터포털 수집기: 행정안전부 공공서비스(혜택), 온통청년, 고용24.

인증키는 환경변수로만 받는다. 키가 없으면 조용히 건너뛰어 다른 수집에 영향을 주지 않는다.
"""
import os
import re
import time

import requests

from models import REGIONS

from .base import DATE_RE, HEADERS

# shortcut: data.go.kr 상세 페이지에서 경로·항목 이름만 확인, 호스트(odcloud)·인증 파라미터 이름은 미확인이라
#           인증키 발급 후 샘플 응답으로 맞춰야 함
GOV24_URL = "https://api.odcloud.kr/api/gov24/v3/serviceList"
YOUTH_RE = re.compile(r"청년|대학생|대학원생|취업준비|구직")
AGE_RE = re.compile(r"만\s*(\d{2})\s*세?\s*[~\-]\s*(?:만\s*)?(\d{2})\s*세")
KIND_BY_FIELD = {"교육": "국비교육", "고용": "국비교육", "주거": "생활지원", "생활": "생활지원"}


def _end_date(text):
    """'2026.3.1 ~ 2026.3.31' 처럼 날짜가 둘 이상이면 마지막 날짜, '상시'면 None"""
    dates = DATE_RE.findall(text or "")
    return "{}-{:0>2}-{:0>2}".format(*dates[-1]) if dates else None


def gov24_card(row):
    """공공서비스 목록 한 줄 → 공통 카드. 청년 대상이 아니거나 경기도 밖 지자체 사업이면 None"""
    target = row.get("지원대상") or ""
    agency = row.get("소관기관명") or ""
    if not YOUTH_RE.search(target + (row.get("서비스명") or "")):
        return None
    if row.get("소관기관유형") == "지방자치단체" and not agency.startswith("경기"):
        return None
    age = AGE_RE.search(target)
    field = row.get("서비스분야") or ""
    return {
        "title": row["서비스명"], "url": row["상세조회URL"], "posted_at": (row.get("등록일시") or "")[:10] or None,
        "source": "지자체" if row.get("소관기관유형") == "지방자치단체" else "보조금24",
        "kind": next((k for f, k in KIND_BY_FIELD.items() if f in field), "지역사업" if agency.startswith("경기") else "생활지원"),
        "agency": agency, "target_text": target[:1000], "amount_text": (row.get("지원내용") or "")[:200],
        "body": target,  # 상세 페이지를 따로 열지 않도록
        "deadline": _end_date(row.get("신청기한")),
        "region": next((w for w in agency.split() if w in REGIONS), None),
        "min_age": int(age.group(1)) if age else None, "max_age": int(age.group(2)) if age else None,
    }


def crawl_gov24(delay=0.5):
    key = os.environ.get("DATA_GO_KR_KEY")
    if not key:
        return [], []
    posts, errors = [], []
    try:
        for page in range(1, 31):  # 하루 1회, 개발계정 1만 건 한도 안에서
            res = requests.get(GOV24_URL, params={"serviceKey": key, "page": page, "perPage": 500},
                               headers=HEADERS, timeout=20)
            res.raise_for_status()
            rows = res.json().get("data") or []
            posts += [c for c in map(gov24_card, rows) if c]
            if len(rows) < 500:
                break
    except Exception as e:
        errors.append(f"공공서비스: {e}".replace(key, "***"))  # 오류 URL 에 인증키가 들어 있음
    return posts, errors


def _not_ready(name, env):
    def crawl(delay=0.5):
        # 응답 항목 명세를 아직 확인하지 못해 키가 있어도 수집하지 않는다 (키 발급 후 샘플 응답으로 구현)
        return [], [f"{name}: 응답 형식 확인 후 구현 예정"] if os.environ.get(env) else []
    return crawl


YOUTH_URL = "https://www.youthcenter.go.kr/go/ythip/getPlcy"
MONEY_RE = re.compile(r"\d[\d,.]*\s*[만천억]?\s*원|장학금|수당|환급|준비금|정착금|지원금|적금|기여금|보증금|이용료|응시료|인건비|활동비|자금|소득공제")
YOUTH_DETAIL = "https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/"


def _age(v):
    return int(v) if (v or "").strip().isdigit() and int(v) > 0 else None


def youth_card(p):
    """온통청년 정책 한 건 → 공통 카드. 경기도(법정동 코드 41…)가 대상이 아니거나 마감된 정책이면 None"""
    if not any(z.startswith("41") for z in (p.get("zipCd") or "").split(",")):
        return None
    # 지원금 정책만: 키워드가 보조금·바우처여도 돌봄·상담 이용권처럼 돈을 주지 않는 사업이 섞여 있어 내용도 본다
    if not any(w in (p.get("plcyKywdNm") or "") for w in ("보조금", "바우처")):
        return None
    if not MONEY_RE.search((p.get("plcySprtCn") or "") + (p.get("plcyExplnCn") or "") + p["plcyNm"]):
        return None
    if p.get("aplyPrdSeCd") == "0057003":  # 신청 마감
        return None
    if "jobaba.net" in (p.get("aplyUrlAddr") or ""):  # 잡아바 수집기가 이미 가져오는 공고
        return None
    agency = p.get("sprvsnInstCdNm") or p.get("operInstCdNm") or ""
    if p.get("pvsnInstGroupCd") == "0054002" and p.get("rgtrHghrkInstCdNm") != "경기도":  # 다른 시·도 지자체 사업
        return None
    field = p.get("lclsfNm") or ""
    dates = re.findall(r"\d{8}", p.get("aplyYmd") or "")
    target = "\n".join(x for x in (p.get("addAplyQlfcCndCn"), p.get("ptcpPrpTrgtCn"), p.get("earnEtcCn")) if x and x.strip())
    return {
        "title": p["plcyNm"], "url": YOUTH_DETAIL + p["plcyNo"],
        "posted_at": (p.get("frstRegDt") or "")[:10] or None, "source": "온통청년",
        "kind": "국비교육" if "교육" in field else "지역사업" if ("일자리" in field or "참여" in field) else "생활지원",
        "agency": agency, "target_text": target[:1000] or None, "amount_text": (p.get("plcySprtCn") or "")[:200] or None,
        "body": "\n".join(x for x in (p.get("plcyExplnCn"), target) if x) or p["plcyNm"],
        "deadline": "{}-{}-{}".format(dates[-1][:4], dates[-1][4:6], dates[-1][6:]) if dates else None,
        "region": next((r for r in REGIONS if r in agency + " " + p["plcyNm"]), None),
        "min_age": _age(p.get("sprtTrgtMinAge")), "max_age": _age(p.get("sprtTrgtMaxAge")),
    }


def crawl_youthcenter(delay=0.5):
    key = os.environ.get("YOUTHCENTER_KEY")
    if not key:
        return [], []
    posts, errors = [], []
    try:
        for page in range(1, 21):  # 전체 약 4천 건, 500건씩
            res = requests.get(YOUTH_URL, params={"apiKeyNm": key, "pageNum": page, "pageSize": 500, "rtnType": "json"},
                               headers=HEADERS, timeout=30)
            res.raise_for_status()
            rows = (res.json().get("result") or {}).get("youthPolicyList") or []
            time.sleep(delay)  # 연달아 요청하면 400 으로 막힘
            posts += [c for c in map(youth_card, rows) if c]
            if len(rows) < 500:
                break
    except Exception as e:
        errors.append(f"온통청년: {e}".replace(key, "***"))  # 오류 URL 에 인증키가 들어 있음
    return posts, errors


crawl_work24 = _not_ready("고용24", "WORK24_KEY")
