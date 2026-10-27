import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { InstallCard, useToast } from '../components/ui.jsx'
import { useUniversities } from '../universities.js'

const EMPTY = { university_id: '', region: '', department: '', grade: '', gpa: '', last_credits: '', income_bracket: '', flags: [] }

export default function Profile() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [params] = useSearchParams()
  const onboarding = params.get('onboarding') === '1'
  const universities = useUniversities()
  const [form, setForm] = useState(EMPTY)
  const [flagOptions, setFlagOptions] = useState({})
  const [regionOptions, setRegionOptions] = useState([])
  const [error, setError] = useState('')
  const [toast, showToast] = useToast()

  useEffect(() => {
    api('/profile').then((d) => {
      const p = d.profile
      setForm({
        ...EMPTY,
        ...Object.fromEntries(Object.entries(p).map(([k, v]) => [k, v ?? ''])),
        flags: p.flags || [],
      })
      setFlagOptions(d.flag_options)
      setRegionOptions(d.region_options)
    }).catch((e) => setError(e.message))
  }, [])

  const school = universities.find((u) => u.id === form.university_id)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const toggleFlag = (key) =>
    setForm({ ...form, flags: form.flags.includes(key) ? form.flags.filter((f) => f !== key) : [...form.flags, key] })

  const withdraw = async () => {
    if (!window.confirm('정말 탈퇴할까요? 입력한 정보가 모두 삭제돼요.')) return
    try {
      await api('/auth/me', { method: 'DELETE' })
      logout()
      navigate('/login', { replace: true })
    } catch (err) {
      setError(err.message)
    }
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const { university_id, ...rest } = form // 학교는 학교 선택 화면에서만 변경
      await api('/profile', { method: 'PUT', body: rest })
      if (onboarding) navigate('/', { replace: true })
      else showToast('저장했어요')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <form className="screen narrow" onSubmit={submit} style={{ paddingTop: onboarding ? 48 : 24 }}>
      <h1 className="headline">{onboarding ? '거의 다 됐어요!\n내 정보를 알려주세요' : '내 정보'}</h1>
      <p className="sub" style={{ marginBottom: 24 }}>
        {onboarding ? '모르는 항목은 비워 둬도 괜찮아요' : `${user?.name}님 · ${user?.email}`}
      </p>

      <Link to="/school" className="list-row" style={{ background: 'var(--grey-100)', padding: '14px 16px', marginBottom: 28 }}>
        <div className="icon school" style={{ background: '#fff' }}>🏫</div>
        <div className="body">
          <div className="caption">내 학교</div>
          <div className="title">{school ? school.name : '학교를 선택해 주세요'}</div>
        </div>
        <span className="text-btn blue" style={{ padding: 0 }}>변경</span>
      </Link>

      <label className="field">
        <span>사는 곳 (주민등록 주소)</span>
        <select className="select" value={form.region} onChange={set('region')}>
          <option value="">선택 안 함</option>
          {regionOptions.map((r) => <option key={r} value={r}>경기도 {r}</option>)}
        </select>
      </label>

      <label className="field">
        <span>학과</span>
        <input className="input" placeholder="예: 컴퓨터공학과" value={form.department} onChange={set('department')} />
      </label>

      <div className="field">
        <span>학년</span>
        <div className="seg">
          {[1, 2, 3, 4].map((g) => (
            <button type="button" key={g} className={String(form.grade) === String(g) ? 'on' : ''}
              onClick={() => setForm({ ...form, grade: String(form.grade) === String(g) ? '' : g })}>
              {g}학년
            </button>
          ))}
        </div>
      </div>

      <div className="row2">
        <label className="field">
          <span>직전학기 평점</span>
          <input className="input" type="number" inputMode="decimal" step="0.01" min="0" max="4.5" placeholder="4.5 만점"
            value={form.gpa} onChange={set('gpa')} />
        </label>
        <label className="field">
          <span>이수 학점</span>
          <input className="input" type="number" inputMode="numeric" min="0" max="30" placeholder="예: 18"
            value={form.last_credits} onChange={set('last_credits')} />
        </label>
      </div>

      <label className="field">
        <span>학자금 지원구간 (소득분위)</span>
        <select className="select" value={form.income_bracket} onChange={set('income_bracket')}>
          <option value="">모름 / 신청 안 함</option>
          {Array.from({ length: 10 }, (_, i) => i + 1).map((b) => <option key={b} value={b}>{b}구간</option>)}
        </select>
      </label>

      <div className="field">
        <span>해당하는 항목을 모두 골라주세요</span>
        <div className="chips">
          {Object.entries(flagOptions).map(([key, label]) => (
            <button type="button" key={key} className={`chip ${form.flags.includes(key) ? 'on' : ''}`} onClick={() => toggleFlag(key)}>
              {form.flags.includes(key) && '✓ '}{label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}
      {!onboarding && <InstallCard />}
      {!onboarding && (
        <div className="center-link" style={{ marginTop: 32 }}>
          <button type="button" className="text-btn" onClick={() => { logout(); navigate('/login') }}>로그아웃</button>
          <span className="muted"> · </span>
          <button type="button" className="text-btn" onClick={withdraw}>회원 탈퇴</button>
        </div>
      )}

      <div className={`bottom-cta ${onboarding ? '' : 'above-tab'}`}>
        <button className="btn" type="submit">{onboarding ? '내 장학금 보러 가기' : '저장하기'}</button>
      </div>
      {toast}
      {/* 하단 버튼에 가려지지 않도록 여백 */}
      <div style={{ height: 80 }} aria-hidden />
    </form>
  )
}
