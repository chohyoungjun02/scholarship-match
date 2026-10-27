import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { ScholarshipRow, ScholarshipSheet } from '../components/Scholarship.jsx'
import { Icon } from '../components/ui.jsx'
import { useUniversities } from '../universities.js'

export default function Scholarships() {
  const universities = useUniversities()
  const [mySchool, setMySchool] = useState('')
  const [school, setSchool] = useState(null) // null = 아직 내 학교 로딩 전
  const [items, setItems] = useState(null)
  const [q, setQ] = useState('')
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    api('/profile').then((d) => {
      setMySchool(d.profile.university_id || '')
      setSchool(d.profile.university_id || '')
    }).catch(() => setSchool(''))
  }, [])

  // 내 학교를 맨 앞에
  const schoolOptions = [...universities].sort((a, b) => (b.id === mySchool) - (a.id === mySchool))

  useEffect(() => {
    if (school === null) return
    const params = new URLSearchParams()
    if (school) params.set('university', school)
    if (q) params.set('q', q)
    const t = setTimeout(() => api(`/scholarships?${params}`).then((d) => setItems(d.items)), q ? 250 : 0)
    return () => clearTimeout(t)
  }, [school, q])

  return (
    <div className="screen">
      <h1 className="headline" style={{ marginBottom: 20 }}>전체 공고</h1>

      <div className="search">
        {Icon.search}
        <input className="input" placeholder="장학금 이름으로 검색" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      <select className="select" style={{ marginBottom: 8 }} value={school ?? ''} onChange={(e) => setSchool(e.target.value)}>
        <option value="">전체 대학</option>
        {schoolOptions.map((u) => (
          <option key={u.id} value={u.id}>{u.id === mySchool ? `내 학교 · ${u.name}` : `${u.name} (${u.city})`}</option>
        ))}
      </select>
      <p className="caption" style={{ margin: '4px 0 8px' }}>
        {school ? '선택한 학교 공지 + 한국장학재단 · 잡아바' : '경기도 모든 대학 + 한국장학재단 · 잡아바'}
        {items && ` · ${items.length}건`}
      </p>

      <div className="list">
        {!items && [1, 2, 3, 4].map((i) => <div key={i} className="skeleton" />)}
        {items?.length === 0 && (
          <div className="empty"><span className="emoji">📭</span>아직 가져온 공고가 없어요.<br />홈에서 새로고침을 눌러 보세요.</div>
        )}
        {items?.map((item) => <ScholarshipRow key={item.id} item={item} onClick={setSelected} />)}
      </div>
      <ScholarshipSheet item={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
