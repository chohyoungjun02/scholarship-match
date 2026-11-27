"""거주지 판정 셀프 체크:  python test_matching.py"""
from types import SimpleNamespace

from crawler.jobaba import region_of
from matcher import evaluate

assert region_of("경기도 이천시", "[이천시] 대출이자 지원") == "이천시"
assert region_of("", "[파주시] 2026년도 청년 전월세 지원") == "파주시"
assert region_of("경기도", "[경기도]경기청년 역량강화 기회 지원") is None
assert region_of("", "[화성시][2026년 특강] 면접") == "화성시"

s = SimpleNamespace(min_gpa=None, max_income_bracket=None, min_grade=None, max_grade=None, min_credits=None,
                    required_flags=None, departments=None, region="이천시", is_structured=False,
                    amount_by_bracket=None, amount_text=None, min_age=None, max_age=None, max_median_income=None,
                    statuses=None, interests=None)
def me(region, age=None, status=None):
    return SimpleNamespace(gpa=None, grade=None, last_credits=None, income_bracket=None, department=None,
                           region=region, flag_list=lambda: [], age=lambda: age, status=status,
                           median_income=None, interest=None)
assert evaluate(me("이천시"), s)["status"] == "eligible"      # 읽은 조건(지역)을 모두 통과
assert evaluate(me("수원시"), s)["status"] == "ineligible"    # 다른 시·군 사업
assert "거주지 정보 미입력" in evaluate(me(None), s)["unknown"]
s.region = None
assert evaluate(me("수원시"), s)["status"] == "check"         # 경기도 전체 사업, 읽은 조건 없음

# 나이·신분 (청년정책 카드)
s.is_structured, s.min_age, s.max_age, s.statuses = True, 19, 34, '["미취업", "졸업예정"]'
assert evaluate(me("수원시", 24, "미취업"), s)["status"] == "eligible"
assert evaluate(me("수원시", 35, "미취업"), s)["status"] == "ineligible"   # 나이 초과
assert evaluate(me("수원시", 24, "재직"), s)["status"] == "ineligible"     # 신분 불일치
assert evaluate(me("수원시"), s)["status"] == "check"                      # 생년월일·신분 모름
from datetime import date
from models import Profile
assert Profile(birth_date="2002-03-15").age(date(2026, 3, 14)) == 23
assert Profile(birth_date="2002-03-15").age(date(2026, 3, 15)) == 24
s.min_age = s.max_age = s.statuses = None
s.is_structured = False
from crawler.base import extract_deadline

assert extract_deadline("하나장학금 선발 안내(~09/23까지)", "", "2026-09-17") == "2026-09-23"
assert extract_deadline("x", "신청기간: 2026. 9. 30.(수) ~ 10. 11.(일) 23:59까지", "2026-09-30") == "2026-10-11"
assert extract_deadline("x", "접수기한 : 2026.11.02( 월 ) ~ 2026.11.06( 금 ) 17:00", "2026-10-13") == "2026-11-06"
assert extract_deadline("x", "신청기간 2026-10-27 ~ 2026-11-10 · 경기도", "2026-10-27") == "2026-11-10"
assert extract_deadline("x", "추천기간 : '26.10.26.(월) ~ '26.11.03.(화) 17:00", "2026-10-23") == "2026-11-03"
assert extract_deadline("x", "제출 기한 : ~ 10. 14.( 수 ) 까지", "2026-10-02") == "2026-10-14"
assert extract_deadline("x", "신청기간 : 2026.12.20 ~ 1. 5.", "2026-12-18") == "2027-01-05"
assert extract_deadline("x", "시험기간 ~ 10. 1.", "2026-09-01") is None  # 접수 기간이 아님
from crawler.base import extract_conditions, extract_region, is_admin_notice

assert extract_region("2026년도 하반기 재단법인 논산시장학회 장학생 선발 안내") == "논산시"
assert extract_region("2026년 하반기 은평구민 장학생 선발 안내") == "은평구"
assert extract_region("2026년 2학기 거창군 지역출신 대학생 등록금 지원사업 안내") == "거창군"
assert extract_region("2026년 하반기 아산시미래장학회 학자금대출 이자지원 신청 안내") == "아산시"
assert extract_region("[외부장학] 하나장학금 선발 안내(~09/23까지)") is None
assert is_admin_notice("2026년 2학기 푸른등대 기부장학금 신규장학생 선발 결과 발표 안내")
assert not is_admin_notice("2026년 2학기 푸른등대 기부장학금(2차) 신규장학생 선발 안내")
assert extract_conditions("직전학기 평점 B+ 이상인 자")["min_gpa"] == 3.5
assert extract_conditions("학자금 지원구간 0~5구간")["max_income_bracket"] == 5
assert extract_conditions("2027학년도 신입생 장학 안내")["max_grade"] == 1
from crawler.opendata import gov24_card

card = gov24_card({"서비스명": "청년 면접 지원", "상세조회URL": "u", "지원대상": "화성시 거주 만 19세~39세 청년",
                   "소관기관명": "경기도 화성시", "소관기관유형": "지방자치단체", "신청기한": "2026.11.01 ~ 2026.12.15"})
assert (card["region"], card["min_age"], card["max_age"], card["deadline"]) == ("화성시", 19, 39, "2026-12-15")
assert gov24_card({"서비스명": "청년 지원", "상세조회URL": "u", "지원대상": "청년", "소관기관명": "부산광역시",
                   "소관기관유형": "지방자치단체"}) is None  # 경기도 밖 지자체
assert gov24_card({"서비스명": "노인 일자리", "상세조회URL": "u", "지원대상": "만 65세 이상"}) is None
from crawler.opendata import youth_card
yc = youth_card({"plcyNo": "1", "plcyNm": "화성시 청년 면접수당", "zipCd": "41590,", "plcyKywdNm": "보조금", "plcySprtCn": "면접 1회 5만원", "aplyPrdSeCd": "0057001",
                 "aplyYmd": "20261101 ~ 20261231", "sprvsnInstCdNm": "경기도 화성시", "lclsfNm": "일자리",
                 "sprtTrgtMinAge": "19", "sprtTrgtMaxAge": "0"})
assert (yc["region"], yc["deadline"], yc["min_age"], yc["max_age"], yc["kind"]) == ("화성시", "2026-12-31", 19, None, "지역사업")
assert youth_card({"plcyNo": "2", "plcyNm": "대구 청년", "zipCd": "27110,"}) is None
assert youth_card({"plcyNo": "3", "plcyNm": "경기 청년 교육", "zipCd": "41590,", "plcyKywdNm": "교육지원"}) is None  # 지원금 아님
assert youth_card({"plcyNo": "4", "plcyNm": "일상돌봄 서비스 사업", "zipCd": "41590,", "plcyKywdNm": "보조금", "plcySprtCn": "재가돌봄 및 특화서비스 제공(사회서비스 바우처)"}) is None
print("ok")
