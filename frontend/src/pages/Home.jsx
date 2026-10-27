import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { ScholarshipRow, ScholarshipSheet, STATUS } from '../components/Scholarship.jsx'
import { Icon, timeAgo, useToast } from '../components/ui.jsx'

export default function Home() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [data, setData] = useState(null)       // { items, university }
  const [profile, setProfile] = useState(null)
  const [tab, setTab] = useState('eligible')
  const [crawling, setCrawling] = useState(false)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [toast, showToast] = useToast()
  const autoCrawled = useRef(false)

  const load = useCallback(() =>
    api('/matches').then((d) => {
      setData(d)
      return d
    }), [])

  const crawl = useCallback(async (force = false) => {
    setCrawling(true)
    try {
      const r = await api('/crawl', { method: 'POST', body: { force } })
      await load()
      const added = r.results.reduce((s, x) => s + x.added, 0)
      const errors = r.results.flatMap((x) => x.errors)
      if (force) showToast(errors.length ? '일부 공지를 못 가져왔어요' : added ? `새 공고 ${added}개를 찾았어요` : '최신 상태예요')
    } catch (e) {
      showToast(e.message)
    } finally {
      setCrawling(false)
    }
  }, [load, showToast])

  useEffect(() => {
    api('/profile').then((d) => setProfile(d.profile)).catch(() => {})
    load()
      .then((d) => {
        // 처음이거나 6시간이 지났으면 학교 공지를 자동으로 새로 가져온다
        if (d.university.stale && !autoCrawled.current) {
          autoCrawled.current = true
          crawl(false)
        }
      })
      .catch((e) => {
        if (e.message.includes('학교를 먼저')) navigate('/school?onboarding=1', { replace: true })
        else setError(e.message)
      })
  }, [load, crawl, navigate])

  if (error) return <div className="screen"><div className="empty">{error}</div></div>
  if (!data) return <div className="screen"><div className="skeleton" style={{ height: 120 }} />{[1, 2, 3].map((i) => <div key={i} className="skeleton" />)}</div>

  const { items, university } = data
  const count = (s) => items.filter((i) => i.match.status === s).length
  const shown = items.filter((i) => i.match.status === tab)
  const firstCrawl = crawling && !university.crawl
  const profileEmpty = profile && ((!profile.grade && !profile.gpa && !profile.income_bracket) || !profile.region)
  // 학교 게시판 자동 수집에 실패했고 학교 공지가 하나도 없으면 홈페이지로 안내
  const schoolFailed = !crawling && university.crawl?.error && !items.some((i) => i.university_id)

  return (
    <div className="screen home-grid">
      <aside className="home-side">
      <Link to="/school" className="school-switch">{university.name}{Icon.chevronDown}</Link>
      <h1 className="big-number">
        {user?.name}님이 지원할 수 있는<br />
        장학금 <span className="accent">{count('eligible')}개</span>
      </h1>
      <div className="updated">
        {crawling ? <span>공지 가져오는 중…</span> : university.crawl
          ? <span>{timeAgo(university.crawl.crawled_at)} 업데이트</span>
          : <span>아직 학교 공지를 가져오지 않았어요</span>}
        {!crawling && <button onClick={() => crawl(true)}>새로고침</button>}
      </div>

      {schoolFailed && (
        <a href={university.homepage} target="_blank" rel="noreferrer" className="banner" style={{ background: 'var(--orange-light)' }}>
          <span style={{ fontSize: 24 }}>🏫</span>
          <span className="body"><b style={{ color: 'var(--orange)' }}>{university.short} 공지는 아직 자동으로 못 가져와요</b><br />학교 홈페이지에서 장학 공지를 확인해 주세요</span>
          <span className="chev" style={{ color: 'var(--orange)' }}>{Icon.chevronRight}</span>
        </a>
      )}
      {profileEmpty && (
        <Link to="/profile" className="banner">
          <span style={{ fontSize: 24 }}>✍️</span>
          <span className="body"><b>사는 곳·학년·평점·소득구간</b>을 입력하면<br />받을 수 있는 장학금·지원금을 더 정확히 알려드려요</span>
          <span className="chev" style={{ color: 'var(--blue)' }}>{Icon.chevronRight}</span>
        </Link>
      )}

      <div className="summary">
        {Object.entries(STATUS).map(([key, label]) => (
          <button key={key} className={tab === key ? 'on' : ''} onClick={() => setTab(key)}>
            <span>{label}</span>
            <b>{count(key)}</b>
          </button>
        ))}
      </div>
      <p className="caption web-only" style={{ lineHeight: 1.6 }}>
        결과는 참고용이에요. 지원 전에 반드시 각 기관의 공고 원문을 확인하세요.
      </p>
      </aside>

      <section className="home-main">
      <h2 className="section-title web-only">{STATUS[tab]} 공고 {shown.length}개</h2>
      {firstCrawl ? (
        <div className="loading-card">
          <div className="spinner" />
          <p>{university.short} 장학 공지를 가져오고 있어요</p>
          <span className="caption">처음 한 번은 20초 정도 걸려요</span>
          <div style={{ marginTop: 24 }}>{[1, 2, 3].map((i) => <div key={i} className="skeleton" />)}</div>
        </div>
      ) : (
        <div className="list">
          {shown.length === 0 && (
            <div className="empty">
              <span className="emoji">{tab === 'eligible' ? '🔍' : '📭'}</span>
              {tab === 'eligible' ? <>조건이 확실히 맞는 장학금이 아직 없어요.<br />'확인 필요' 공고도 살펴보세요.</> : '해당하는 공고가 없어요'}
            </div>
          )}
          {shown.map((item) => <ScholarshipRow key={item.id} item={item} onClick={setSelected} />)}
        </div>
      )}

      <p className="caption app-only" style={{ marginTop: 24, lineHeight: 1.6 }}>
        결과는 참고용이에요. 지원 전에 반드시 각 기관의 공고 원문을 확인하세요.
      </p>
      </section>
      <ScholarshipSheet item={selected} onClose={() => setSelected(null)} />
      {toast}
    </div>
  )
}
