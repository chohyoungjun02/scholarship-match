"""회원 프로필과 장학금 조건을 비교해 '해당 / 확인 필요 / 미해당'을 판정한다."""
import json

from models import FLAGS


def _effective_bracket(profile):
    """기초·차상위는 학자금 지원구간 0으로 취급한다."""
    flags = profile.flag_list()
    if "basic_livelihood" in flags or "near_poverty" in flags:
        return 0
    return profile.income_bracket


def _bracket_in(key, bracket):
    if "-" in key:
        lo, hi = key.split("-")
        return int(lo) <= bracket <= int(hi)
    return int(key) == bracket


def expected_amount(profile, s):
    if not s.amount_by_bracket:
        return s.amount_text
    bracket = _effective_bracket(profile)
    if bracket is None:
        return s.amount_text
    for key, value in json.loads(s.amount_by_bracket).items():
        if _bracket_in(key, bracket):
            return value
    return s.amount_text


def evaluate(profile, s):
    """returns dict(status, passed, failed, unknown, amount)"""
    passed, failed, unknown = [], [], []

    def check(label, need, have, ok):
        if need is None:
            return
        if have is None:
            unknown.append(f"{label} 정보 미입력")
        elif ok(have, need):
            passed.append(label)
        else:
            failed.append(label)

    check(f"평점 {s.min_gpa} 이상", s.min_gpa, profile.gpa, lambda h, n: h >= n)
    check(f"학자금 지원구간 {s.max_income_bracket}구간 이하", s.max_income_bracket,
          _effective_bracket(profile), lambda h, n: h <= n)
    check(f"{s.min_grade}학년 이상", s.min_grade, profile.grade, lambda h, n: h >= n)
    check(f"{s.max_grade}학년 이하", s.max_grade, profile.grade, lambda h, n: h <= n)
    check(f"직전학기 {s.min_credits}학점 이상 이수", s.min_credits, profile.last_credits, lambda h, n: h >= n)

    req_flags = json.loads(s.required_flags or "[]")
    if req_flags:
        names = "/".join(FLAGS.get(f, f) for f in req_flags)
        if set(req_flags) & set(profile.flag_list()):
            passed.append(names)
        else:
            failed.append(f"{names} 대상")

    if s.region:  # 시·군 거주자 대상 사업 (잡아바 어플라이)
        if not profile.region:
            unknown.append("거주지 정보 미입력")
        elif profile.region == s.region:
            passed.append(f"{s.region} 거주")
        else:
            failed.append(f"{s.region} 거주자 대상")

    depts = json.loads(s.departments or "[]")
    if depts:
        label = "학과(" + ", ".join(depts) + ")"
        if not profile.department:
            unknown.append("학과 정보 미입력")
        elif any(d in profile.department for d in depts):
            passed.append(label)
        else:
            failed.append(label)

    if failed:
        status = "ineligible"
    elif unknown or not s.is_structured:
        # 크롤링한 공지는 조건을 완전히 파악할 수 없으므로 '확인 필요'
        status = "check"
    else:
        status = "eligible"

    return {
        "status": status,
        "passed": passed,
        "failed": failed,
        "unknown": unknown,
        "amount": expected_amount(profile, s),
    }
