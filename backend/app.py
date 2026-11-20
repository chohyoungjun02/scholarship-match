import json
from datetime import date, datetime, timedelta, timezone

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from sqlalchemy import inspect, or_, text

from auth import admin_required, auth_bp, login_required
from config import Config
from crawler.base import is_admin_notice
from crawler.run import COMMON_SOURCES, crawl_stale, crawl_university, is_stale, refresh_conditions
from crawler.universities import BY_ID, UNIVERSITIES, public_info
from matcher import evaluate
from models import (FLAGS, INTERESTS, KINDS, MEDIAN_INCOMES, REGIONS, STATUSES, CrawlLog, Saved, Scholarship,
                    db)
from samples import seed_samples
from seed import seed_programs


def migrate():
    """create_all 은 기존 테이블에 컬럼을 추가하지 않으므로, 이전 버전 DB 에 새 컬럼을 붙인다."""
    insp = inspect(db.engine)
    s30, s100, i, t = "VARCHAR(30)", "VARCHAR(100)", "INTEGER", "TEXT"
    for table, column, ctype in [
        ("profile", "university_id", s30), ("scholarship", "university_id", s30), ("profile", "region", s30),
        ("scholarship", "region", s30), ("scholarship", "deadline", s30),
        ("profile", "birth_date", s30), ("profile", "status", s30), ("profile", "median_income", i),
        ("profile", "interest", s30), ("scholarship", "kind", s30), ("scholarship", "agency", s100),
        ("scholarship", "target_text", t), ("scholarship", "apply_start", s30), ("scholarship", "min_age", i),
        ("scholarship", "max_age", i), ("scholarship", "statuses", t), ("scholarship", "max_median_income", i),
        ("scholarship", "interests", t),
    ]:
        if column not in [c["name"] for c in insp.get_columns(table)]:
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ctype}"))
    # 이미 수집한 공고에도 최신 추출 규칙 적용: 행정 공지는 지우고 조건·마감일은 다시 읽는다
    # (운영 기관이 있는 카드는 공공데이터 항목을 그대로 쓰므로 제외)
    # shortcut: 서버가 켜질 때마다 크롤링 공고 전체를 다시 읽음, 공고가 수천 개로 늘면 규칙 버전을 저장해 바뀔 때만 실행
    for s in Scholarship.query.filter(Scholarship.is_structured.is_(False), Scholarship.agency.is_(None)):
        if is_admin_notice(s.title):
            db.session.delete(s)
        else:
            refresh_conditions(s)
    # 대학 선택 기능 이전에 수집한 한신대 공지는 대상 대학이 아니므로 정리
    Scholarship.query.filter(Scholarship.university_id.is_(None), Scholarship.source == "한신대").delete()
    db.session.commit()


def university_payload(uid):
    log = db.session.get(CrawlLog, uid)
    return {**public_info(BY_ID[uid]), "crawl": log.to_dict() if log else None,
            # 학교 공지가 최신이어도 한국장학재단·잡아바가 오래됐으면 다시 수집하도록
            "stale": is_stale(uid) or any(is_stale(k) for k in COMMON_SOURCES)}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.json.ensure_ascii = False
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()
        migrate()
        seed_programs()
        seed_samples()

    # ---------------- 대학 ----------------
    @app.get("/api/universities")
    def universities():
        return jsonify(items=[public_info(u) for u in UNIVERSITIES])

    # ---------------- 회원 정보 ----------------
    @app.get("/api/profile")
    @login_required
    def get_profile():
        return jsonify(profile=g.user.profile.to_dict(), flag_options=FLAGS, region_options=REGIONS,
                       status_options=STATUSES, income_options=MEDIAN_INCOMES, interest_options=INTERESTS)

    @app.put("/api/profile")
    @login_required
    def update_profile():
        data = request.get_json() or {}
        p = g.user.profile

        def num(key, cast):
            v = data.get(key)
            return None if v in (None, "") else cast(v)

        if "university_id" in data:
            if data["university_id"] not in BY_ID:
                return jsonify(error="경기도 대학 중에서 선택해 주세요."), 400
            p.university_id = data["university_id"]
        try:
            if "grade" in data:  # 학교만 바꾸는 요청도 허용
                p.department = (data.get("department") or "").strip() or None
                p.grade = num("grade", int)
                p.gpa = num("gpa", float)
                p.last_credits = num("last_credits", int)
                p.income_bracket = num("income_bracket", int)
                p.flags = json.dumps([f for f in data.get("flags", []) if f in FLAGS])
                if data.get("region") not in REGIONS + [None, ""]:
                    return jsonify(error="거주지는 경기도 시·군 중에서 선택해 주세요."), 400
                p.region = data.get("region") or None
                for key, options in (("status", STATUSES), ("interest", INTERESTS)):
                    if data.get(key) not in options + [None, ""]:
                        return jsonify(error="선택지에서 골라 주세요."), 400
                    setattr(p, key, data.get(key) or None)
                p.median_income = num("median_income", int)
                if p.median_income is not None and p.median_income not in MEDIAN_INCOMES:
                    return jsonify(error="가구 소득 수준을 선택지에서 골라 주세요."), 400
                p.birth_date = data.get("birth_date") or None
                if p.birth_date and not 15 <= (p.age() or 0) <= 60:  # 형식이 틀리면 ValueError
                    return jsonify(error="생년월일을 확인해 주세요."), 400
        except ValueError:
            return jsonify(error="숫자 항목을 올바르게 입력해 주세요."), 400
        if p.gpa is not None and not 0 <= p.gpa <= 4.5:
            return jsonify(error="평점은 0~4.5 사이로 입력해 주세요."), 400
        db.session.commit()
        return jsonify(profile=p.to_dict())

    # ---------------- 장학금 ----------------
    def open_scholarships():
        """접수 마감일이 지난 공고는 뺀다 (마감일을 모르는 공고는 남김)"""
        today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()  # 한국 시간 기준
        return Scholarship.query.filter(or_(Scholarship.deadline.is_(None), Scholarship.deadline >= today))

    def scholarships_for(university_id):
        """선택한 대학의 공지 + 모든 대학생 대상(한국장학재단)"""
        return open_scholarships().filter(or_(Scholarship.university_id == university_id,
                                              Scholarship.university_id.is_(None)))

    @app.get("/api/scholarships")
    def list_scholarships():
        uid = request.args.get("university")
        q = scholarships_for(uid) if uid in BY_ID else open_scholarships()
        if keyword := request.args.get("q"):
            q = q.filter(Scholarship.title.contains(keyword))
        # 대학 공지(최신순) → 한국장학재단 프로그램 → 한국장학재단 공지
        items = q.order_by(Scholarship.university_id.is_(None), Scholarship.is_structured.desc(),
                           Scholarship.posted_at.desc()).all()
        return jsonify(items=[s.to_dict() for s in items])

    @app.get("/api/matches")
    @login_required
    def matches():
        uid = g.user.profile.university_id
        if not uid:
            return jsonify(error="학교를 먼저 선택해 주세요.", code="NO_UNIVERSITY"), 400
        order = {"eligible": 0, "check": 1, "ineligible": 2}
        saved = {r.scholarship_id for r in Saved.query.filter_by(user_id=g.user.id)}
        result = [{**s.to_dict(), "match": evaluate(g.user.profile, s), "saved": s.id in saved}
                  for s in scholarships_for(uid)]
        # 상태(지원 가능 → 확인 필요 → 해당 없음) 안에서 내 학교 공지 → 한국장학재단, 각각 최신 공지 순
        result.sort(key=lambda x: x["posted_at"] or "", reverse=True)
        result.sort(key=lambda x: (order[x["match"]["status"]], x["university_id"] is None))
        return jsonify(items=result, university=university_payload(uid))

    # ---------------- 관심 지원 저장 (마감 알림) ----------------
    @app.get("/api/saved")
    @login_required
    def list_saved():
        """저장한 지원을 마감 빠른 순으로 (마감일 모르는 지원은 뒤로)"""
        rows = (Scholarship.query.join(Saved, Saved.scholarship_id == Scholarship.id)
                .filter(Saved.user_id == g.user.id).all())
        items = [{**s.to_dict(), "match": evaluate(g.user.profile, s), "saved": True} for s in rows]
        items.sort(key=lambda x: x["deadline"] or "9999")
        return jsonify(items=items)

    @app.put("/api/saved/<int:sid>")
    @login_required
    def save(sid):
        if not db.session.get(Scholarship, sid):
            return jsonify(error="없는 공고예요."), 404
        if not db.session.get(Saved, (g.user.id, sid)):
            db.session.add(Saved(user_id=g.user.id, scholarship_id=sid))
            db.session.commit()
        return jsonify(ok=True)

    @app.delete("/api/saved/<int:sid>")
    @login_required
    def unsave(sid):
        Saved.query.filter_by(user_id=g.user.id, scholarship_id=sid).delete()
        db.session.commit()
        return jsonify(ok=True)

    # ---------------- 운영자: 지자체 사업 등 수동 등록 ----------------
    @app.get("/api/admin/cards")
    @admin_required
    def admin_cards():
        rows = Scholarship.query.filter_by(category="운영자").order_by(Scholarship.id.desc()).all()
        return jsonify(items=[s.to_dict() for s in rows], kind_options=KINDS, status_options=STATUSES,
                       region_options=REGIONS)

    @app.post("/api/admin/cards")
    @admin_required
    def admin_add_card():
        d = request.get_json() or {}
        title, url = (d.get("title") or "").strip(), (d.get("url") or "").strip()
        if not title or not url.startswith(("http://", "https://")):
            return jsonify(error="제목과 신청 링크(https://…)는 꼭 입력해 주세요."), 400
        if d.get("kind") not in KINDS or d.get("region") not in REGIONS + [None, ""]:
            return jsonify(error="분류·지역을 선택지에서 골라 주세요."), 400
        if Scholarship.query.filter_by(url=url).first():
            return jsonify(error="같은 링크의 지원이 이미 있어요."), 409
        try:
            ages = [int(d[k]) if d.get(k) not in (None, "") else None for k in ("min_age", "max_age")]
            for k in ("apply_start", "deadline"):
                if d.get(k):
                    date.fromisoformat(d[k])
        except ValueError:
            return jsonify(error="나이는 숫자로, 날짜는 YYYY-MM-DD로 입력해 주세요."), 400
        s = Scholarship(
            source="지자체" if d["kind"] == "지역사업" else "운영자 등록", category="운영자", is_structured=True,
            title=title, url=url, kind=d["kind"], region=d.get("region") or None,
            agency=(d.get("agency") or "").strip() or "운영자 확인", target_text=d.get("target_text") or None,
            description=d.get("target_text") or None, amount_text=d.get("amount_text") or None,
            apply_start=d.get("apply_start") or None, deadline=d.get("deadline") or None,
            min_age=ages[0], max_age=ages[1],
            statuses=json.dumps([x for x in d.get("statuses", []) if x in STATUSES], ensure_ascii=False),
        )
        db.session.add(s)
        db.session.commit()
        return jsonify(item=s.to_dict()), 201

    @app.delete("/api/admin/cards/<int:sid>")
    @admin_required
    def admin_delete_card(sid):
        Saved.query.filter_by(scholarship_id=sid).delete()
        Scholarship.query.filter_by(id=sid, category="운영자").delete()
        db.session.commit()
        return jsonify(ok=True)

    @app.post("/api/crawl")
    @login_required
    def run_crawl():
        """내 학교(또는 지정한 학교) 장학 공지를 크롤링. 최근 6시간 내 수집했으면 건너뛴다."""
        data = request.get_json(silent=True) or {}
        uid = data.get("university_id") or g.user.profile.university_id
        if uid not in BY_ID:
            return jsonify(error="학교를 먼저 선택해 주세요."), 400
        results = crawl_university(uid, force=bool(data.get("force")))
        return jsonify(results=results, university=university_payload(uid))

    @app.get("/api/cron/crawl")
    def cron_crawl():
        """Vercel Cron 이 하루 한 번 호출: 오래된 학교부터 제한 시간 안에서 미리 크롤링해 둔다."""
        secret = app.config["CRON_SECRET"]
        if secret and request.headers.get("Authorization") != f"Bearer {secret}":
            return jsonify(error="unauthorized"), 401
        return jsonify(results=crawl_stale(time_budget_sec=45))

    @app.get("/api/health")
    def health():
        return jsonify(ok=True, db=app.config["SQLALCHEMY_DATABASE_URI"].split(":")[0])

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
