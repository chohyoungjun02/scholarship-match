import { useEffect, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'

export const Icon = {
  chevronRight: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="m9 6 6 6-6 6" /></svg>
  ),
  chevronDown: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="m6 9 6 6 6-6" /></svg>
  ),
  back: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#191f28" strokeWidth="2.2" strokeLinecap="round"><path d="m15 5-7 7 7 7" /></svg>
  ),
  search: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
  ),
  check: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3.4" strokeLinecap="round"><path d="m5 12 5 5 9-10" /></svg>
  ),
  home: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M11.3 3.3a1 1 0 0 1 1.4 0l8 7.5A1 1 0 0 1 20 12.5h-1V20a1 1 0 0 1-1 1h-4v-5h-4v5H6a1 1 0 0 1-1-1v-7.5H4a1 1 0 0 1-.7-1.7z" /></svg>
  ),
  list: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="4" width="18" height="4" rx="2" /><rect x="3" y="10" width="18" height="4" rx="2" /><rect x="3" y="16" width="18" height="4" rx="2" /></svg>
  ),
  user: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="8" r="4.5" /><path d="M3.5 20.5c0-4.4 3.8-7 8.5-7s8.5 2.6 8.5 7a.5.5 0 0 1-.5.5H4a.5.5 0 0 1-.5-.5z" /></svg>
  ),
}

// 900px 이상이면 웹(데스크톱) 레이아웃, 미만이면 앱(모바일) 레이아웃
const DESKTOP_QUERY = '(min-width: 900px)'

export function useIsDesktop() {
  const [desktop, setDesktop] = useState(() => window.matchMedia(DESKTOP_QUERY).matches)
  useEffect(() => {
    const mq = window.matchMedia(DESKTOP_QUERY)
    const onChange = (e) => setDesktop(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return desktop
}

// 앱 설치(PWA): 안드로이드/PC 크롬·엣지는 설치 창, iOS 사파리는 안내 문구
const isStandalone = () => window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone
const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent)

export function useInstall() {
  const [canPrompt, setCanPrompt] = useState(!!window.__installPrompt)
  useEffect(() => {
    const on = () => setCanPrompt(true)
    window.addEventListener('installable', on)
    return () => window.removeEventListener('installable', on)
  }, [])
  const install = async () => {
    const p = window.__installPrompt
    if (!p) return
    p.prompt()
    await p.userChoice
    window.__installPrompt = null
    setCanPrompt(false)
  }
  return { installed: isStandalone(), canPrompt, ios: isIOS(), install }
}

export function InstallCard() {
  const { installed, canPrompt, ios, install } = useInstall()
  if (installed || (!canPrompt && !ios)) return null
  return (
    <div className="banner" style={{ marginTop: 24 }}>
      <img src="/icons/icon-192.png" alt="" width="40" height="40" style={{ borderRadius: 10 }} />
      <span className="body">
        <b>장학매칭 앱 설치</b><br />
        {ios ? '사파리 공유 버튼 → "홈 화면에 추가"를 눌러주세요' : '홈 화면에서 앱처럼 바로 열 수 있어요'}
      </span>
      {canPrompt && <button type="button" className="btn small" onClick={install}>설치</button>}
    </div>
  )
}

// 웹 버전 상단 내비게이션
export function TopHeader({ user, onLogout }) {
  const { installed, canPrompt, install } = useInstall()
  return (
    <header className="topheader">
      <div className="topheader-inner">
        <NavLink to="/" className="brand"><span className="brand-mark">🎓</span>장학매칭</NavLink>
        {user && (
          <nav>
            <NavLink to="/" end>맞춤 장학금</NavLink>
            <NavLink to="/all">전체 공고</NavLink>
            <NavLink to="/profile">내 정보</NavLink>
          </nav>
        )}
        <div className="topheader-right">
          {!installed && canPrompt && <button className="text-btn blue" onClick={install}>앱 설치</button>}
          {user ? (
            <>
              <span className="caption">{user.name}님</span>
              <button className="btn small secondary" onClick={onLogout}>로그아웃</button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="text-btn">로그인</NavLink>
              <NavLink to="/register"><button className="btn small">회원가입</button></NavLink>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

// 웹 버전 로그인/회원가입 왼쪽 소개 영역 (앱 화면에서는 CSS 로 숨김)
export function AuthHero() {
  return (
    <aside className="auth-hero">
      <div className="auth-hero-inner">
        <span className="badge src" style={{ background: 'rgba(255,255,255,.18)', color: '#fff' }}>수원 · 화성 · 오산 11개 대학</span>
        <h2>{'우리 학교 장학금,\n한 곳에서 확인하세요'}</h2>
        <ul>
          <li>🏫 내 학교 장학 공지를 자동으로 모아와요</li>
          <li>🏛️ 한국장학재단 국가장학금까지 함께</li>
          <li>✅ 내 학년·평점·소득구간으로 지원 가능 여부 확인</li>
        </ul>
      </div>
    </aside>
  )
}

export function TabBar() {
  return (
    <nav className="tabbar">
      <NavLink to="/" end>{Icon.home}홈</NavLink>
      <NavLink to="/all">{Icon.list}전체 공고</NavLink>
      <NavLink to="/profile">{Icon.user}내 정보</NavLink>
    </nav>
  )
}

export function TopNav({ title }) {
  const navigate = useNavigate()
  return (
    <div className="topnav">
      <button className="back" onClick={() => navigate(-1)} aria-label="뒤로">{Icon.back}</button>
      {title && <b style={{ fontSize: 17 }}>{title}</b>}
    </div>
  )
}

export function BottomSheet({ open, onClose, children }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="dim" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()} role="dialog">
        <div className="handle" />
        {children}
      </div>
    </div>
  )
}

export function useToast() {
  const [msg, setMsg] = useState('')
  useEffect(() => {
    if (!msg) return
    const t = setTimeout(() => setMsg(''), 1800)
    return () => clearTimeout(t)
  }, [msg])
  return [msg ? <div className="toast">{msg}</div> : null, setMsg]
}

export function timeAgo(iso) {
  if (!iso) return ''
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60) return '방금'
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`
  return `${Math.floor(diff / 86400)}일 전`
}

export const shortDate = (d) => (d ? d.slice(5).replace('-', '.') : '')
