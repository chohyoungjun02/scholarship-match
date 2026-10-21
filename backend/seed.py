"""한국장학재단 주요 장학 프로그램 (사람이 조건을 정리한 기본 데이터).

※ 금액·구간 기준은 2025년 공고를 참고한 값이며 매년 바뀝니다.
   실제 서비스 전에 반드시 한국장학재단 공고로 다시 확인하세요.
"""
import json

from models import Scholarship, db

KOSAF_MAIN = "https://www.kosaf.go.kr/ko/scholar.do?pg=scholarship_main&naviParam=JH,00,00,00"

PROGRAMS = [
    {
        "title": "국가장학금 Ⅰ유형 (학생직접지원형)",
        "url": KOSAF_MAIN + "#national-1",
        "description": "소득 연계형 국가장학금. 직전학기 12학점 이상 이수, 100점 만점 80점(B0) 이상. "
                       "기초·차상위 및 1~3구간은 C학점 경고제(70점 이상, 2회) 적용.",
        "amount_text": "학자금 지원구간별 차등 지급",
        "amount_by_bracket": {"0": "등록금 전액", "1-3": "연 최대 600만원", "4-6": "연 최대 440만원",
                              "7-8": "연 최대 360만원", "9": "연 최대 100만원"},
        "min_gpa": 3.0, "max_income_bracket": 9, "min_credits": 12,
    },
    {
        "title": "국가장학금 Ⅱ유형 (대학연계지원형)",
        "url": KOSAF_MAIN + "#national-2",
        "description": "대학이 자체 기준에 따라 선발·지급. 세부 성적·구간 기준은 한신대 공지를 확인하세요.",
        "amount_text": "대학별 기준에 따름",
        "max_income_bracket": 9,
    },
    {
        "title": "다자녀 국가장학금",
        "url": KOSAF_MAIN + "#multi-child",
        "description": "다자녀(자녀 3명 이상) 가구 대학생 대상. 직전학기 12학점 이상, 80점 이상.",
        "amount_text": "학자금 지원구간별 차등 지급 (기초·차상위 셋째 이상은 등록금 전액)",
        "min_gpa": 3.0, "max_income_bracket": 9, "min_credits": 12,
        "required_flags": ["multi_child"],
    },
    {
        "title": "국가근로장학금",
        "url": KOSAF_MAIN + "#work",
        "description": "교내·교외 근로를 통해 장학금 지급. 학자금 지원구간 8구간 이하 우선 선발, 70점(C0) 이상.",
        "amount_text": "근로시간에 따라 시급 지급 (교내/교외 차등)",
        "min_gpa": 2.0, "max_income_bracket": 8,
    },
    {
        "title": "인문100년장학금",
        "url": KOSAF_MAIN + "#humanities",
        "description": "인문·사회계열 우수 학생 대상 장학금. 학자금 지원구간 8구간 이하.",
        "amount_text": "등록금 전액 + 생활비 (공고 확인)",
        "min_gpa": 3.5, "max_income_bracket": 8,
        "departments": ["인문", "국어", "영어", "철학", "역사", "사회", "신학", "문화", "심리", "경영", "경제"],
    },
    {
        "title": "주거안정장학금",
        "url": KOSAF_MAIN + "#housing",
        "description": "원거리 진학으로 주거비 부담이 있는 기초·차상위 대학생 대상.",
        "amount_text": "연 최대 240만원 (공고 확인)",
        "required_flags": ["basic_livelihood", "near_poverty"],
    },
]


def seed_programs():
    for p in PROGRAMS:
        if Scholarship.query.filter_by(url=p["url"]).first():
            continue
        db.session.add(Scholarship(
            source="한국장학재단",
            category="프로그램",
            title=p["title"],
            url=p["url"],
            description=p.get("description"),
            amount_text=p.get("amount_text"),
            amount_by_bracket=json.dumps(p["amount_by_bracket"], ensure_ascii=False) if p.get("amount_by_bracket") else None,
            min_gpa=p.get("min_gpa"),
            max_income_bracket=p.get("max_income_bracket"),
            min_credits=p.get("min_credits"),
            required_flags=json.dumps(p.get("required_flags", [])),
            departments=json.dumps(p.get("departments", []), ensure_ascii=False),
            is_structured=True,
        ))
    db.session.commit()
