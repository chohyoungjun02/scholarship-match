import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import { AuthHero, TopNav } from '../components/ui.jsx'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const valid = form.name && form.email && form.password.length >= 8

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await register(form)
      navigate('/school?onboarding=1') // 가입 직후 학교 선택 → 내 정보 입력
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-layout">
      <AuthHero />
      <div className="auth-form">
      <div className="app-only"><TopNav /></div>
      <form className="screen no-tab" onSubmit={submit} style={{ paddingTop: 8 }}>
        <h1 className="headline">{'반가워요!\n먼저 계정을 만들어 주세요'}</h1>
        <p className="sub">학교와 내 정보를 입력하면 장학금을 찾아드려요</p>

        <label className="field">
          <span>이름</span>
          <input className="input" required placeholder="홍길동" value={form.name} onChange={set('name')} />
        </label>
        <label className="field">
          <span>이메일</span>
          <input className="input" type="email" required autoComplete="email" placeholder="example@email.com"
            value={form.email} onChange={set('email')} />
        </label>
        <label className="field">
          <span>비밀번호</span>
          <input className="input" type="password" required minLength={8} autoComplete="new-password"
            placeholder="8자 이상" value={form.password} onChange={set('password')} />
        </label>
        {error && <p className="error-text">{error}</p>}

        <div className="bottom-cta">
          <button className="btn" type="submit" disabled={!valid || busy}>{busy ? '가입 중…' : '다음'}</button>
        </div>
      </form>
      </div>
    </div>
  )
}
