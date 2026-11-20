"""공공데이터 인증키를 받기 전까지 쓰는 샘플 지원 카드 (온통청년·고용24·지자체 채널).

shortcut: 발표자료와 기관 안내를 바탕으로 손으로 정리한 값이라 실제와 다를 수 있음,
          인증키 발급 후 crawler/opendata.py 수집 결과로 교체하고 이 목록은 지운다
"""
import json

from models import Scholarship, db

NOTE = " ※ 샘플 데이터예요. 신청 전 기관 공고를 꼭 확인하세요."

SAMPLES = [
    {
        "source": "온통청년", "kind": "생활지원", "title": "청년월세 지원",
        "url": "https://www.bokjiro.go.kr#youth-rent", "agency": "국토교통부, 시·군·구",
        "amount_text": "월 최대 20만원 (최대 12개월)",
        "target_text": "부모와 따로 사는 무주택 청년 (만 19~34세), 청년가구·원가구 소득 기준 충족",
        "min_age": 19, "max_age": 34, "max_median_income": 60,
    },
    {
        "source": "온통청년", "kind": "생활지원", "title": "국민취업지원제도 (Ⅰ유형)",
        "url": "https://www.work24.go.kr#kua", "agency": "고용노동부",
        "amount_text": "구직촉진수당 월 50만원 × 6개월 + 취업지원 서비스",
        "target_text": "취업하지 않은 청년 (만 18~34세), 가구 소득 기준중위소득 120% 이하 등",
        "min_age": 18, "max_age": 34, "statuses": ["졸업예정", "미취업"],
    },
    {
        "source": "고용24", "kind": "국비교육", "title": "국민내일배움카드 훈련과정",
        "url": "https://www.work24.go.kr#hrd-card", "agency": "고용노동부",
        "amount_text": "5년간 300~500만원 훈련비 지원",
        "target_text": "국민 누구나 (대학 재학생은 졸업예정 학년 등 일부만 가능)",
        "statuses": ["휴학", "졸업예정", "미취업", "재직"], "interests": ["IT", "디자인", "사무", "서비스", "제조", "기타"],
    },
    {
        "source": "고용24", "kind": "국비교육", "title": "K-디지털 트레이닝",
        "url": "https://www.work24.go.kr#kdt", "agency": "고용노동부",
        "amount_text": "디지털 첨단분야 훈련비 지원 (2026년부터 자기부담금 최대 60만원)",
        "target_text": "국민내일배움카드 발급자 중 디지털 분야 취업 희망 청년",
        "statuses": ["휴학", "졸업예정", "미취업"], "interests": ["IT", "디자인"],
    },
    {
        "source": "지자체", "kind": "지역사업", "title": "경기도 청년기본소득",
        "url": "https://youth.gg.go.kr#basic-income", "agency": "경기도",
        "amount_text": "분기 25만원, 연 최대 100만원 (지역화폐)",
        "target_text": "경기도에 거주하는 만 24세 청년",
        "min_age": 24, "max_age": 24,
    },
    {
        "source": "지자체", "kind": "지역사업", "title": "경기도 청년 면접수당",
        "url": "https://youth.gg.go.kr#interview", "agency": "경기도, 경기도미래세대재단",
        "amount_text": "면접 1회 5만원, 연 최대 3회 (지역화폐)",
        "target_text": "경기도 거주 만 18~39세, 취업 여부 무관",
        "min_age": 18, "max_age": 39,
    },
    {
        "source": "지자체", "kind": "지역사업", "title": "화성시 청년 면접 지원",
        "url": "https://www.hscity.go.kr#youth-interview", "agency": "화성시", "region": "화성시",
        "amount_text": "면접 정장 대여 연 최대 5회",
        "target_text": "화성시 거주 만 19~39세 청년",
        "min_age": 19, "max_age": 39,
    },
]


def seed_samples():
    for p in SAMPLES:
        if Scholarship.query.filter_by(url=p["url"]).first():
            continue
        db.session.add(Scholarship(
            category="샘플", is_structured=True,
            description=p["target_text"] + NOTE,
            statuses=json.dumps(p.get("statuses", []), ensure_ascii=False),
            interests=json.dumps(p.get("interests", []), ensure_ascii=False),
            **{k: v for k, v in p.items() if k not in ("statuses", "interests")},
        ))
    db.session.commit()
