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
                    amount_by_bracket=None, amount_text=None)
def me(region):
    return SimpleNamespace(gpa=None, grade=None, last_credits=None, income_bracket=None, department=None,
                           region=region, flag_list=lambda: [])
assert evaluate(me("이천시"), s)["status"] == "eligible"      # 읽은 조건(지역)을 모두 통과
assert evaluate(me("수원시"), s)["status"] == "ineligible"    # 다른 시·군 사업
assert "거주지 정보 미입력" in evaluate(me(None), s)["unknown"]
s.region = None
assert evaluate(me("수원시"), s)["status"] == "check"         # 경기도 전체 사업, 읽은 조건 없음
from crawler.base import extract_deadline

assert extract_deadline("하나장학금 선발 안내(~09/23까지)", "", "2026-09-17") == "2026-09-23"
assert extract_deadline("x", "신청기간: 2026. 9. 30.(수) ~ 10. 11.(일) 23:59까지", "2026-09-30") == "2026-10-11"
assert extract_deadline("x", "접수기한 : 2026.11.02( 월 ) ~ 2026.11.06( 금 ) 17:00", "2026-10-13") == "2026-11-06"
assert extract_deadline("x", "신청기간 2026-10-27 ~ 2026-11-10 · 경기도", "2026-10-27") == "2026-11-10"
assert extract_deadline("x", "추천기간 : '26.10.26.(월) ~ '26.11.03.(화) 17:00", "2026-10-23") == "2026-11-03"
assert extract_deadline("x", "제출 기한 : ~ 10. 14.( 수 ) 까지", "2026-10-02") == "2026-10-14"
assert extract_deadline("x", "신청기간 : 2026.12.20 ~ 1. 5.", "2026-12-18") == "2027-01-05"
assert extract_deadline("x", "시험기간 ~ 10. 1.", "2026-09-01") is None  # 접수 기간이 아님
print("ok")
