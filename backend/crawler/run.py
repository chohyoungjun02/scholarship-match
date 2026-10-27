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

from models import CrawlLog, Scholarship, db

from . import jobaba, kosaf
from .base import extract_body, extract_conditions, get_soup
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
    for post in posts:
        s = Scholarship.query.filter_by(url=post["url"]).first()
        if s is None:
            s = Scholarship(url=post["url"], source=post["source"], category="공지",
                            university_id=post.get("university_id"))
            db.session.add(s)
            added += 1
        s.title = post["title"][:300]
        s.posted_at = post["posted_at"] or s.posted_at

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
            apply_conditions(s, extract_conditions(s.title + " " + body))
    return added, errors


def _run(key, fetch):
    """fetch() -> (posts, errors) 를 실행하고 저장, CrawlLog 기록"""
    cfg = current_app.config
    with _lock(key):
        posts, errors = fetch(cfg["CRAWL_DELAY_SEC"])
        added, detail_errors = _save_posts(posts, cfg["CRAWL_DELAY_SEC"], cfg["CRAWL_DETAIL_LIMIT"])
        errors += detail_errors
        log = db.session.get(CrawlLog, key) or CrawlLog(key=key)
        log.crawled_at, log.added = datetime.utcnow(), added
        log.error = "\n".join(errors) or None
        db.session.add(log)
        db.session.commit()
    return {"key": key, "found": len(posts), "added": added, "errors": errors}


# 모든 학교 학생에게 보여 주는 공통 출처 (university_id 없음)
COMMON_SOURCES = {"kosaf": kosaf.crawl, "jobaba": jobaba.crawl}


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
