import json

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from sqlalchemy import inspect, or_, text

from auth import auth_bp, login_required
from config import Config
from crawler.run import crawl_stale, crawl_university, is_stale
from crawler.universities import BY_ID, UNIVERSITIES, public_info
from matcher import evaluate
from models import FLAGS, CrawlLog, Scholarship, db
from seed import seed_programs


def migrate():
    """create_all 은 기존 테이블에 컬럼을 추가하지 않으므로, 이전 버전 DB 에 새 컬럼을 붙인다."""
    insp = inspect(db.engine)
    for table, column in [("profile", "university_id"), ("scholarship", "university_id")]:
        if column not in [c["name"] for c in insp.get_columns(table)]:
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} VARCHAR(30)"))
    # 대학 선택 기능 이전에 수집한 한신대 공지는 대상 대학이 아니므로 정리
    Scholarship.query.filter(Scholarship.university_id.is_(None), Scholarship.source == "한신대").delete()
    db.session.commit()


def university_payload(uid):
    log = db.session.get(CrawlLog, uid)
    return {**public_info(BY_ID[uid]), "crawl": log.to_dict() if log else None, "stale": is_stale(uid)}


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

    # ---------------- 대학 ----------------
    @app.get("/api/universities")
    def universities():
        return jsonify(items=[public_info(u) for u in UNIVERSITIES])

    # ---------------- 회원 정보 ----------------
    @app.get("/api/profile")
    @login_required
    def get_profile():
        return jsonify(profile=g.user.profile.to_dict(), flag_options=FLAGS)

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
                return jsonify(error="수원시·화성시·오산시 대학 중에서 선택해 주세요."), 400
            p.university_id = data["university_id"]
        try:
            if "grade" in data:  # 학교만 바꾸는 요청도 허용
                p.department = (data.get("department") or "").strip() or None
                p.grade = num("grade", int)
                p.gpa = num("gpa", float)
                p.last_credits = num("last_credits", int)
                p.income_bracket = num("income_bracket", int)
                p.flags = json.dumps([f for f in data.get("flags", []) if f in FLAGS])
        except ValueError:
            return jsonify(error="숫자 항목을 올바르게 입력해 주세요."), 400
        if p.gpa is not None and not 0 <= p.gpa <= 4.5:
            return jsonify(error="평점은 0~4.5 사이로 입력해 주세요."), 400
        db.session.commit()
        return jsonify(profile=p.to_dict())

    # ---------------- 장학금 ----------------
    def scholarships_for(university_id):
        """선택한 대학의 공지 + 모든 대학생 대상(한국장학재단)"""
        return Scholarship.query.filter(or_(Scholarship.university_id == university_id,
                                            Scholarship.university_id.is_(None)))

    @app.get("/api/scholarships")
    def list_scholarships():
        uid = request.args.get("university")
        q = scholarships_for(uid) if uid in BY_ID else Scholarship.query
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
        result = [{**s.to_dict(), "match": evaluate(g.user.profile, s)} for s in scholarships_for(uid)]
        # 상태(지원 가능 → 확인 필요 → 해당 없음) 안에서 내 학교 공지 → 한국장학재단, 각각 최신 공지 순
        result.sort(key=lambda x: x["posted_at"] or "", reverse=True)
        result.sort(key=lambda x: (order[x["match"]["status"]], x["university_id"] is None))
        return jsonify(items=result, university=university_payload(uid))

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
