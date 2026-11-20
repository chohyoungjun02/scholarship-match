import json
from datetime import date, datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

# 회원이 체크할 수 있는 자격 조건 (key -> 화면 표시명)
# 거주지 선택지: 경기도 31개 시·군 (잡아바 어플라이 사업은 대부분 시·군 거주자 대상)
REGIONS = ["수원시", "성남시", "의정부시", "안양시", "부천시", "광명시", "평택시", "동두천시", "안산시", "고양시",
           "과천시", "구리시", "남양주시", "오산시", "시흥시", "군포시", "의왕시", "하남시", "용인시", "파주시",
           "이천시", "안성시", "김포시", "화성시", "광주시", "양주시", "포천시", "여주시", "연천군", "가평군", "양평군"]

FLAGS = {
    "basic_livelihood": "기초생활수급자",
    "near_poverty": "차상위계층",
    "multi_child": "다자녀 가구",
    "disabled": "장애인",
    "veteran_family": "국가유공자(자녀)",
    "single_parent": "한부모 가정",
}

STATUSES = ["재학", "휴학", "졸업예정", "미취업", "재직"]
# 가구 소득: 기준중위소득 몇 % 이하인지 (None = 모름)
MEDIAN_INCOMES = {50: "기준중위소득 50% 이하", 60: "60% 이하", 100: "100% 이하", 150: "150% 이하", 200: "150% 초과"}
INTERESTS = ["IT", "디자인", "사무", "서비스", "제조", "기타"]
# 지원 카드 분류
KINDS = ["장학금", "생활지원", "국비교육", "지역사업"]


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
    region = db.Column(db.String(10))            # 거주 시·군 (REGIONS)
    department = db.Column(db.String(100))       # 학과
    grade = db.Column(db.Integer)                # 학년 1~4
    gpa = db.Column(db.Float)                    # 직전학기 평점 (4.5 만점)
    last_credits = db.Column(db.Integer)         # 직전학기 이수학점
    income_bracket = db.Column(db.Integer)       # 학자금 지원구간 1~10
    flags = db.Column(db.Text, default="[]")     # FLAGS 키 목록(JSON)
    birth_date = db.Column(db.String(10))        # YYYY-MM-DD
    status = db.Column(db.String(10))            # STATUSES
    median_income = db.Column(db.Integer)        # MEDIAN_INCOMES 키
    interest = db.Column(db.String(10))          # INTERESTS

    def flag_list(self):
        return json.loads(self.flags or "[]")

    def age(self, today=None):
        """만 나이"""
        if not self.birth_date:
            return None
        today = today or date.today()
        b = date.fromisoformat(self.birth_date)
        return today.year - b.year - ((today.month, today.day) < (b.month, b.day))

    def to_dict(self):
        return {
            "birth_date": self.birth_date,
            "status": self.status,
            "median_income": self.median_income,
            "interest": self.interest,
            "university_id": self.university_id,
            "region": self.region,
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
    deadline = db.Column(db.String(30))  # 접수 마감일 YYYY-MM-DD (None = 모름/상시)
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
    region = db.Column(db.String(10))       # 이 시·군 거주자만 (None = 지역 조건 없음)
    departments = db.Column(db.Text)        # 학과 키워드 중 하나 포함(JSON)

    # ---- 공통 카드 필드 (공공데이터·운영자 등록) ----
    kind = db.Column(db.String(10))         # KINDS (None 이면 출처로 추정)
    agency = db.Column(db.String(100))      # 운영 기관 (값이 있으면 공공데이터·운영자 카드)
    target_text = db.Column(db.Text)        # 대상 (원문)
    apply_start = db.Column(db.String(10))  # 신청 시작일
    min_age = db.Column(db.Integer)
    max_age = db.Column(db.Integer)
    statuses = db.Column(db.Text)           # 이 신분 중 하나여야 함(JSON, STATUSES)
    max_median_income = db.Column(db.Integer)  # 기준중위소득 % 이하
    interests = db.Column(db.Text)          # 관련 관심 분야(JSON, INTERESTS)

    is_structured = db.Column(db.Boolean, default=False)  # 조건을 사람이 정리한 데이터인지
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def kind_or_guess(self):
        return self.kind or ("지역사업" if self.source == "잡아바어플라이" else "장학금")

    def to_dict(self):
        return {
            "id": self.id,
            "source": self.source,
            "kind": self.kind_or_guess(),
            "agency": self.agency,
            "target_text": self.target_text,
            "apply_start": self.apply_start,
            "region": self.region,
            "min_age": self.min_age,
            "max_age": self.max_age,
            "verified_at": self.updated_at.date().isoformat() if self.updated_at else None,
            "university_id": self.university_id,
            "category": self.category,
            "title": self.title,
            "url": self.url,
            "posted_at": self.posted_at,
            "deadline": self.deadline,
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


class Saved(db.Model):
    """관심 지원 저장 (마감 알림 대상)"""
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    scholarship_id = db.Column(db.Integer, db.ForeignKey("scholarship.id", ondelete="CASCADE"), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


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
