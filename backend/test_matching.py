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
assert evaluate(me("이천시"), s)["status"] == "check"         # 지역 맞음 (나머지 조건은 원문 확인)
assert evaluate(me("수원시"), s)["status"] == "ineligible"    # 다른 시·군 사업
assert "거주지 정보 미입력" in evaluate(me(None), s)["unknown"]
s.region = None
assert evaluate(me("수원시"), s)["status"] == "check"         # 경기도 전체 사업
print("ok")
