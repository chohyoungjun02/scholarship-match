# 배포 가이드 (Vercel → `https://프로젝트이름.vercel.app`)

> **현재 배포 주소: https://scholarship-match-bice.vercel.app** (Vercel 프로젝트 `chj10/scholarship-match`)
> 다시 배포: `장학금` 폴더에서 `npx vercel deploy --prod`

프론트엔드(React)와 백엔드(Flask)를 **Vercel 프로젝트 하나**로 배포합니다.

```
https://xxx.vercel.app/        → React 빌드 결과 (frontend/dist)
https://xxx.vercel.app/api/... → Python 서버리스 함수 (api/index.py → backend/app.py)
```

관련 파일: `vercel.json`, `api/index.py`, `requirements.txt`(루트), `.vercelignore`

---

## 1. 데이터베이스 준비 (필수)

Vercel 서버리스는 파일을 저장할 수 없어서 **SQLite 대신 PostgreSQL**이 필요합니다. (무료 플랜으로 충분)

**방법 A — Vercel 대시보드에서 Neon 연결 (가장 쉬움)**
1. vercel.com → 프로젝트 → **Storage** → **Create Database** → **Neon (Postgres)** 선택
2. 프로젝트에 연결하면 `DATABASE_URL` 환경변수가 자동으로 추가됩니다.

**방법 B — Supabase (서울 리전 선택 가능)**
1. supabase.com → New project → Region: **Northeast Asia (Seoul)**
2. Project Settings → Database → Connection string → **Transaction pooler** URI 복사
3. 아래 3단계에서 `DATABASE_URL` 로 등록

> 테이블은 첫 요청 때 자동으로 만들어지고, 한국장학재단 기본 장학금도 자동으로 들어갑니다.

## 2. Vercel CLI 로 배포

`장학금` 폴더에서 실행합니다.

```bash
npx vercel login
```
```bash
npx vercel
```
처음 실행 시 질문에는 이렇게 답합니다.
- Set up and deploy? → **Y**
- Link to existing project? → **N** (새 프로젝트)
- Project name → 예: `scholarship-match` (→ `scholarship-match.vercel.app`)
- In which directory is your code located? → **./** (그대로 Enter)
- Modify settings? → **N** (설정은 `vercel.json` 에 있음)

## 3. 환경변수 등록

```bash
npx vercel env add SECRET_KEY production
```
값은 아무도 모르는 긴 문자열 — 아래 명령으로 만들 수 있습니다.
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
```bash
npx vercel env add DATABASE_URL production
```
(방법 A로 Neon 을 연결했다면 이미 있으므로 생략)
```bash
npx vercel env add CRON_SECRET production
```
(매일 자동 크롤링 요청이 진짜 Vercel Cron 인지 확인하는 값, 아무 긴 문자열)

## 4. 실제 배포

```bash
npx vercel --prod
```
끝나면 `https://프로젝트이름.vercel.app` 주소가 출력됩니다.
`https://프로젝트이름.vercel.app/api/health` 에서 `{"db": "postgresql", "ok": true}` 가 나오면 성공입니다.

이후 코드를 고치면 `npx vercel --prod` 만 다시 실행하면 됩니다.
(GitHub 저장소에 올리고 vercel.com/new 에서 Import 하면 push 할 때마다 자동 배포도 됩니다.)

---

## 배포 설정 요약 (`vercel.json`)

| 항목 | 값 | 이유 |
|---|---|---|
| `regions` | `icn1` (서울) | 국내 대학 사이트 크롤링 속도·차단 회피 |
| `functions.maxDuration` | 60초 | 첫 크롤링이 20~30초 걸림 |
| `rewrites` | `/api/*` → Flask, 나머지 → `index.html` | 새로고침해도 React 라우팅 유지 |
| `crons` | 매일 06:00(KST) `/api/cron/crawl` | 사용자가 들어오기 전에 오래된 학교부터 미리 크롤링 |

## 앱 버전 (PWA) 설치

배포된 주소는 HTTPS 라서 휴대폰에 **앱으로 설치**할 수 있습니다.
- **안드로이드 (크롬)**: 내 정보 화면의 "설치" 버튼, 또는 메뉴 → "앱 설치"
- **아이폰 (사파리)**: 공유 버튼 → "홈 화면에 추가"
- **PC (크롬/엣지)**: 상단 "앱 설치" 버튼 또는 주소창 오른쪽 설치 아이콘

설치하면 주소창 없이 앱처럼 열리고, 화면 폭이 좁으면 하단 탭바가 있는 앱 레이아웃,
900px 이상이면 상단 메뉴가 있는 웹 레이아웃으로 자동 전환됩니다.

## 주의

- 로컬 `backend/scholarship.db` 의 회원·데이터는 배포 DB 로 옮겨지지 않습니다 (새로 가입).
- 일부 대학 사이트가 해외/클라우드 IP 를 막으면 해당 학교 크롤링이 실패할 수 있습니다 → `/api/health` 와 Vercel 대시보드 **Logs** 에서 확인.
- Vercel 무료(Hobby) 플랜은 Cron 이 하루 1회만 가능합니다.
