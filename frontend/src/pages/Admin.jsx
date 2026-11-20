import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useToast } from '../components/ui.jsx'

const EMPTY = { title: '', kind: '지역사업', agency: '', region: '', amount_text: '', target_text: '',
  min_age: '', max_age: '', statuses: [], apply_start: '', deadline: '', url: '' }

// 운영자 화면: 공공데이터에 없는 지자체 사업 등을 직접 등록 (ADMIN_EMAILS 계정만)
export default function Admin() {
  const [data, setData] = useState(null)
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [toast, showToast] = useToast()

  const load = () => api('/admin/cards').then(setData).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const toggleStatus = (st) =>
    setForm({ ...form, statuses: form.statuses.includes(st) ? form.statuses.filter((x) => x !== st) : [...form.statuses, st] })

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api('/admin/cards', { method: 'POST', body: form })
      setForm(EMPTY)
      showToast('등록했어요')
      load()
    } catch (err) {
      setError(err.message)
    }
  }
  const remove = async (id) => {
    if (!window.confirm('이 지원을 삭제할까요?')) return
    await api(`/admin/cards/${id}`, { method: 'DELETE' })
    load()
  }

  if (!data) return <div className="screen narrow"><p className="error-text">{error}</p></div>

  return (
    <div className="screen narrow">
      <h1 className="headline" style={{ marginBottom: 8 }}>운영자 화면</h1>
      <p className="sub" style={{ marginBottom: 24 }}>공공데이터에 없는 지원을 직접 등록해요. 등록하면 바로 모든 회원 목록에 나와요.</p>

      <form onSubmit={submit}>
        <label className="field"><span>지원 이름 *</span><input className="input" value={form.title} onChange={set('title')} required /></label>
        <div className="row2">
          <label className="field"><span>분류</span>
            <select className="select" value={form.kind} onChange={set('kind')}>{data.kind_options.map((k) => <option key={k}>{k}</option>)}</select>
          </label>
          <label className="field"><span>지역</span>
            <select className="select" value={form.region} onChange={set('region')}>
              <option value="">경기도 전체 / 전국</option>
              {data.region_options.map((r) => <option key={r}>{r}</option>)}
            </select>
          </label>
        </div>
        <label className="field"><span>운영 기관</span><input className="input" value={form.agency} onChange={set('agency')} placeholder="예: 화성시 청년정책과" /></label>
        <label className="field"><span>지원 내용</span><input className="input" value={form.amount_text} onChange={set('amount_text')} placeholder="예: 면접 1회 5만원, 연 최대 3회" /></label>
        <label className="field"><span>대상 (원문)</span><textarea className="input" rows="3" value={form.target_text} onChange={set('target_text')} /></label>
        <div className="row2">
          <label className="field"><span>최소 나이 (만)</span><input className="input" type="number" value={form.min_age} onChange={set('min_age')} /></label>
          <label className="field"><span>최대 나이 (만)</span><input className="input" type="number" value={form.max_age} onChange={set('max_age')} /></label>
        </div>
        <div className="field"><span>대상 신분 (고르지 않으면 누구나)</span>
          <div className="chips">
            {data.status_options.map((st) => (
              <button type="button" key={st} className={`chip ${form.statuses.includes(st) ? 'on' : ''}`} onClick={() => toggleStatus(st)}>{st}</button>
            ))}
          </div>
        </div>
        <div className="row2">
          <label className="field"><span>신청 시작</span><input className="input" type="date" value={form.apply_start} onChange={set('apply_start')} /></label>
          <label className="field"><span>마감</span><input className="input" type="date" value={form.deadline} onChange={set('deadline')} /></label>
        </div>
        <label className="field"><span>신청 링크 *</span><input className="input" type="url" value={form.url} onChange={set('url')} placeholder="https://" required /></label>
        {error && <p className="error-text">{error}</p>}
        <button className="btn" type="submit" style={{ marginTop: 8 }}>등록하기</button>
      </form>

      <h2 className="section-title" style={{ marginTop: 40 }}>등록한 지원 {data.items.length}개</h2>
      <div className="list">
        {data.items.map((i) => (
          <div key={i.id} className="list-row">
            <div className="body">
              <div className="title">{i.title}</div>
              <div className="meta">{i.kind} · {i.region || '전체'} · {i.deadline ? `~${i.deadline}` : '상시'}</div>
            </div>
            <button type="button" className="text-btn" onClick={() => remove(i.id)}>삭제</button>
          </div>
        ))}
      </div>
      {toast}
    </div>
  )
}
