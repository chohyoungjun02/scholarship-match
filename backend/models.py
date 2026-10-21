import json
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

# 회원이 체크할 수 있는 자격 조건 (key -> 화면 표시명)
FLAGS = {
    "basic_livelihood": "기초생활수급자",
    "near_poverty": "차상위계층",
    "multi_child": "다자녀 가구",
    "disabled": "장애인",
    "veteran_family": "국가유공자(자녀)",
    "single_parent": "한부모 가정",
}


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile = db.relationship("Profile", backref="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def to_dict(self):
        return {"id": self.id, "email": self.email, "name": self.name}


class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    university_id = db.Column(db.String(30))     # crawler/universities.py 의 id
    department = db.Column(db.String(100))       # 학과
    grade = db.Column(db.Integer)                # 학년 1~4
    gpa = db.Column(db.Float)                    # 직전학기 평점 (4.5 만점)
    last_credits = db.Column(db.Integer)         # 직전학기 이수학점
    income_bracket = db.Column(db.Integer)       # 학자금 지원구간 1~10
    flags = db.Column(db.Text, default="[]")     # FLAGS 키 목록(JSON)

    def flag_list(self):
        return json.loads(self.flags or "[]")

    def to_dict(self):
        return {
            "university_id": self.university_id,
            "department": self.department,
            "grade": self.grade,
            "gpa": self.gpa,
            "last_credits": self.last_credits,
            "income_bracket": self.income_bracket,
            "flags": self.flag_list(),
        }


class Scholarship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(30), nullable=False)    # 대학 약칭('아주대') / '한국장학재단'
    university_id = db.Column(db.String(30), index=True)  # None 이면 모든 대학생 대상(한국장학재단)
    category = db.Column(db.String(30))                  # '공지' / '프로그램'
    title = db.Column(db.String(300), nullable=False)
    url = db.Column(db.String(500), unique=True, nullable=False)
    posted_at = db.Column(db.String(20))
    description = db.Column(db.Text)
    amount_text = db.Column(db.String(200))
    amount_by_bracket = db.Column(db.Text)  # {"0": "등록금 전액", "1-3": "연 600만원"} 형식(JSON)

    # ---- 자격 조건 (None = 조건 없음/알 수 없음) ----
    min_gpa = db.Column(db.Float)
    max_income_bracket = db.Column(db.Integer)
    min_grade = db.Column(db.Integer)
    max_grade = db.Column(db.Integer)
    min_credits = db.Column(db.Integer)
    required_flags = db.Column(db.Text)     # 이 중 하나 이상 해당해야 함(JSON)
    departments = db.Column(db.Text)        # 학과 키워드 중 하나 포함(JSON)

    is_structured = db.Column(db.Boolean, default=False)  # 조건을 사람이 정리한 데이터인지
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "source": self.source,
            "university_id": self.university_id,
            "category": self.category,
            "title": self.title,
            "url": self.url,
            "posted_at": self.posted_at,
            "description": (self.description or "")[:500],
            "amount_text": self.amount_text,
            "conditions": {
                "min_gpa": self.min_gpa,
                "max_income_bracket": self.max_income_bracket,
                "min_grade": self.min_grade,
                "max_grade": self.max_grade,
                "min_credits": self.min_credits,
                "required_flags": json.loads(self.required_flags or "[]"),
                "departments": json.loads(self.departments or "[]"),
            },
            "is_structured": self.is_structured,
        }


class CrawlLog(db.Model):
    """대학(또는 'kosaf')별 마지막 크롤링 시각 - 오래됐을 때만 다시 크롤링한다."""
    key = db.Column(db.String(30), primary_key=True)
    crawled_at = db.Column(db.DateTime)
    added = db.Column(db.Integer, default=0)
    error = db.Column(db.Text)

    def to_dict(self):
        return {
            "crawled_at": self.crawled_at.isoformat() + "Z" if self.crawled_at else None,
            "added": self.added,
            "error": self.error,
        }
