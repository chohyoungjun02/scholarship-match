"""크롤러를 실행하고 결과를 DB에 저장(upsert)한다.

- crawl_university(id) : 회원이 고른 대학 + 한국장학재단 (오래된 경우만)
- crawl_all()          : 모든 대학 + 한국장학재단

터미널에서 전체 실행:  python -m crawler.run
특정 대학만:          python -m crawler.run ajou
"""
import json
import threading
import time
from datetime import datetime, timedelta

from flask import current_app

from models import CrawlLog, Saved, Scholarship, db

from . import jobaba, kosaf, opendata
from .base import (extract_body, extract_conditions, extract_deadline, extract_region, get_soup,
                   is_admin_notice)
from .universities import BY_ID, UNIVERSITIES
from .universities import crawl as crawl_univ_boards

STALE_AFTER = timedelta(hours=6)
_locks = {}  # 같은 대학을 동시에 두 번 크롤링하지 않도록


def _lock(key):
    return _locks.setdefault(key, threading.Lock())


def is_stale(key):
    log = db.session.get(CrawlLog, key)
    return not log or not log.crawled_at or datetime.utcnow() - log.crawled_at > STALE_AFTER


def _save_posts(posts, delay, detail_limit):
    added = details = 0
    errors = []
    # 공고마다 DB 를 조회하면 원격 DB 에서 수백 번 왕복해 서버리스 제한 시간을 넘으므로 한 번에 불러온다
    existing = {s.url: s for s in Scholarship.query.filter(Scholarship.url.in_([p["url"] for p in posts]))}
    for post in posts:
        if is_admin_notice(post["title"]):
            continue
        s = existing.get(post["url"])
        if s is None:
            s = existing[post["url"]] = Scholarship(url=post["url"], source=post["source"], category="공지",
                                                    university_id=post.get("university_id"))
            db.session.add(s)
            added += 1
        s.title = post["title"][:300]
        s.posted_at = post["posted_at"] or s.posted_at
        s.region = post.get("region") or s.region  # 제목에서 읽은 지역(…시장학회)을 지우지 않도록

        body = post.get("body")  # 목록에서 본문까지 주는 사이트(수원과학대)
        # 본문을 아직 못 읽은 글만 상세 페이지를 열어 조건을 추출 (1회 요청 수 제한,
        # 이번에 못 읽은 글은 다음 크롤링 때 이어서 읽는다)
        if not body and not s.description and details < detail_limit:
            try:
                body = extract_body(get_soup(post["url"], delay))
                details += 1
            except Exception as e:
                errors.append(f"상세 {post['url']}: {e}")
        if body and not s.description:
            s.description = body[:3000]
            refresh_conditions(s)
        for key in CARD_FIELDS:  # 공공데이터처럼 항목이 정리된 출처는 본문 추출보다 우선
            if post.get(key) is not None:
                setattr(s, key, post[key])
    return added, errors


CARD_FIELDS = ("kind", "agency", "target_text", "amount_text", "deadline", "min_age", "max_age")


EXTRACTED = ("max_income_bracket", "min_gpa", "min_credits", "min_grade", "max_grade", "amount_text", "required_flags")


def refresh_conditions(s):
    """제목·본문에서 조건과 마감일을 다시 읽는다 (추출 규칙을 고치면 이미 수집한 공고에도 반영되도록)"""
    for key in EXTRACTED:
        setattr(s, key, None)
    apply_conditions(s, extract_conditions(s.title + " " + (s.description or "")))
    s.region = extract_region(s.title) or s.region
    s.deadline = extract_deadline(s.title, s.description or "", s.posted_at)


def _run(key, fetch):
    """fetch() -> (posts, errors) 를 실행하고 저장, CrawlLog 기록"""
    cfg = current_app.config
    with _lock(key):
        posts, errors = fetch(cfg["CRAWL_DELAY_SEC"])
        added, detail_errors = _save_posts(posts, cfg["CRAWL_DELAY_SEC"], cfg["CRAWL_DETAIL_LIMIT"])
        errors += detail_errors
        if key == "youthcenter" and posts and not errors:
            # API 는 전체 목록을 주므로, 이번 목록에 없는 정책(지원금이 아니거나 내려간 정책)은 지운다
            gone = [s.id for s in Scholarship.query.filter(Scholarship.source == "온통청년",
                                                            Scholarship.url.notin_([p["url"] for p in posts]))]
            Saved.query.filter(Saved.scholarship_id.in_(gone)).delete()
            Scholarship.query.filter(Scholarship.id.in_(gone)).delete()
        log =db.session.get(CrawlLog, key) or CrawlLog(key=key)
        log.crawled_at, log.added = datetime.utcnow(), added
        log.error = "\n".join(errors) or None
        db.session.add(log)
        db.session.commit()
    return {"key": key, "found": len(posts), "added": added, "errors": errors}


# 모든 학교 학생에게 보여 주는 공통 출처 (university_id 없음)
COMMON_SOURCES = {"kosaf": kosaf.crawl, "jobaba": jobaba.crawl, "gov24": opendata.crawl_gov24,
                  "youthcenter": opendata.crawl_youthcenter, "work24": opendata.crawl_work24}


def crawl_common(force=False):
    return [_run(key, fn) for key, fn in COMMON_SOURCES.items() if force or is_stale(key)]


def crawl_university(university_id, force=False):
    univ = BY_ID[university_id]
    results = []
    if force or is_stale(university_id):
        results.append(_run(university_id, lambda delay: crawl_univ_boards(univ, delay)))
    return results + crawl_common(force)


def crawl_stale(time_budget_sec=45):
    """크롤링한 지 오래된 순서로, 제한 시간(서버리스 함수 실행 시간)을 넘지 않게 크롤링한다."""
    started = time.monotonic()
    results = crawl_common()

    def last(uid):
        log = db.session.get(CrawlLog, uid)
        return log.crawled_at if log and log.crawled_at else datetime.min

    for u in sorted(UNIVERSITIES, key=lambda u: last(u["id"])):
        if time.monotonic() - started > time_budget_sec * 0.6:  # 한 학교 ≈ 10~20초
            break
        if is_stale(u["id"]):
            results.append(_run(u["id"], lambda delay, u=u: crawl_univ_boards(u, delay)))
    return results


def crawl_all():
    results = [_run(u["id"], lambda delay, u=u: crawl_univ_boards(u, delay)) for u in UNIVERSITIES]
    results += crawl_common(force=True)
    return results


def apply_conditions(s, cond):
    for key in ("max_income_bracket", "min_gpa", "min_credits", "min_grade", "max_grade", "amount_text"):
        if key in cond:
            setattr(s, key, cond[key])
    if "required_flags" in cond:
        s.required_flags = json.dumps(cond["required_flags"])


if __name__ == "__main__":
    import sys

    from app import app

    sys.stdout.reconfigure(encoding="utf-8")
    with app.app_context():
        if len(sys.argv) > 1:
            for r in crawl_university(sys.argv[1], force=True):
                print(r)
        else:
            for r in crawl_all():
                print(r)
