from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request

from models import Profile, User, db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def make_token(user):
    payload = {
        "sub": str(user.id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=current_app.config["JWT_EXPIRES_HOURS"]),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="로그인이 필요합니다."), 401
        try:
            payload = jwt.decode(header[7:], current_app.config["SECRET_KEY"], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify(error="로그인이 만료되었습니다. 다시 로그인해 주세요."), 401
        except jwt.InvalidTokenError:
            return jsonify(error="유효하지 않은 토큰입니다."), 401
        g.user = db.session.get(User, int(payload["sub"]))
        if g.user is None:
            return jsonify(error="존재하지 않는 회원입니다."), 401
        return fn(*args, **kwargs)

    return wrapper


@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    password = data.get("password") or ""
    if not email or not name or len(password) < 8:
        return jsonify(error="이름, 이메일, 8자 이상 비밀번호를 입력해 주세요."), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error="이미 가입된 이메일입니다."), 409

    user = User(email=email, name=name)
    user.set_password(password)
    user.profile = Profile()
    db.session.add(user)
    db.session.commit()
    return jsonify(token=make_token(user), user=user.to_dict()), 201


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    user = User.query.filter_by(email=(data.get("email") or "").strip().lower()).first()
    if not user or not user.check_password(data.get("password") or ""):
        return jsonify(error="이메일 또는 비밀번호가 올바르지 않습니다."), 401
    return jsonify(token=make_token(user), user=user.to_dict())


@auth_bp.get("/me")
@login_required
def me():
    return jsonify(user=g.user.to_dict())


@auth_bp.delete("/me")
@login_required
def delete_me():
    """회원 탈퇴: 계정과 프로필을 삭제한다."""
    db.session.delete(g.user)
    db.session.commit()
    return jsonify(ok=True)
