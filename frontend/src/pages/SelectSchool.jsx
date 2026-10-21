import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api.js'
import { Icon, TopNav } from '../components/ui.jsx'
import { CITIES, useUniversities } from '../universities.js'

export default function SelectSchool() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const onboarding = params.get('onboarding') === '1'
  const universities = useUniversities()
  const [selected, setSelected] = useState(null)
  const [q, setQ] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api('/profile').then((d) => setSelected(d.profile.university_id)).catch(() => {})
  }, [])

  const filtered = universities.filter((u) => !q || u.name.includes(q) || u.short.includes(q))

  const save = async () => {
    setBusy(true)
    try {
      await api('/profile', { method: 'PUT', body: { university_id: selected } })
      navigate(onboarding ? '/profile?onboarding=1' : '/', { replace: true })
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  return (
    <>
      {!onboarding && <TopNav />}
      <div className="screen no-tab narrow" style={{ paddingTop: onboarding ? 48 : 8 }}>
        <h1 className="headline">{'다니는 학교를\n선택해 주세요'}</h1>
        <p className="sub" style={{ marginBottom: 20 }}>선택한 학교의 장학 공지를 바로 가져올게요</p>

        <div className="search">
          {Icon.search}
          <input className="input" placeholder="학교 이름 검색" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>

        {CITIES.map((city) => {
          const list = filtered.filter((u) => u.city === city)
          if (!list.length) return null
          return (
            <div key={city}>
              <div className="group-label">{city}</div>
              <div className="list">
                {list.map((u) => (
                  <button key={u.id} className={`list-row ${selected === u.id ? 'selected' : ''}`} onClick={() => setSelected(u.id)}>
                    <div className="icon school">🏫</div>
                    <div className="body">
                      <div className="title">{u.name}</div>
                      <div className="meta">{u.city}{u.campus && ` · ${u.campus}`}</div>
                    </div>
                    <span className="check">{selected === u.id && Icon.check}</span>
                  </button>
                ))}
              </div>
            </div>
          )
        })}
        {universities.length > 0 && filtered.length === 0 && (
          <div className="empty">수원시·화성시·오산시 대학만 지원해요</div>
        )}
        {error && <p className="error-text">{error}</p>}

        <div className="bottom-cta">
          <button className="btn" disabled={!selected || busy} onClick={save}>
            {busy ? '저장 중…' : onboarding ? '다음' : '이 학교로 변경'}
          </button>
        </div>
      </div>
    </>
  )
}
