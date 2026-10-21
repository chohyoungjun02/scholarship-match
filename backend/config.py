import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ON_VERCEL = bool(os.environ.get("VERCEL"))


def database_url():
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if url:
        # Neon/Supabase/Vercel 이 주는 postgres:// · postgresql:// 를 설치된 드라이버(psycopg2)로 고정
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                url = "postgresql+psycopg2://" + url[len(prefix):]
        return url
    if ON_VERCEL:
        # 서버리스 환경은 /tmp 만 쓸 수 있고 재시작하면 사라진다 → 데모용. 실제 배포는 DATABASE_URL 필수
        return "sqlite:////tmp/scholarship.db"
    return "sqlite:///" + os.path.join(BASE_DIR, "scholarship.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or ("" if ON_VERCEL else "dev-secret-change-me")
    if not SECRET_KEY:
        raise RuntimeError("배포 환경에서는 SECRET_KEY 환경변수를 설정해야 합니다.")
    SQLALCHEMY_DATABASE_URI = database_url()
    # 서버리스에서 끊긴 커넥션을 재사용하지 않도록
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_EXPIRES_HOURS = 24 * 7
    # 상세 페이지까지 들어가서 본문을 읽을 최대 게시글 수 (사이트 부하 방지)
    CRAWL_DETAIL_LIMIT = int(os.environ.get("CRAWL_DETAIL_LIMIT", "8"))
    CRAWL_DELAY_SEC = float(os.environ.get("CRAWL_DELAY_SEC", "0.3"))
    # Vercel Cron 이 보내는 Authorization: Bearer <CRON_SECRET> 확인용
    CRON_SECRET = os.environ.get("CRON_SECRET")
