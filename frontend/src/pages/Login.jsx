import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import { AuthHero } from '../components/ui.jsx'

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(form.email, form.password)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-layout">
    <AuthHero />
    <form className="screen no-tab auth-form" onSubmit={submit} style={{ paddingTop: 72 }}>
      <h1 className="headline">{'받을 수 있는 장학금,\n'}<span className="accent">놓치지 마세요</span></h1>
      <p className="sub">경기도 대학생 장학금·지원금, 한 번에 모아 봐요</p>

      <label className="field">
        <span>이메일</span>
        <input className="input" type="email" required autoComplete="email" placeholder="example@email.com"
          value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
      </label>
      <label className="field">
        <span>비밀번호</span>
        <input className="input" type="password" required autoComplete="current-password" placeholder="비밀번호 입력"
          value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
      </label>
      {error && <p className="error-text">{error}</p>}

      <div className="bottom-cta">
        <button className="btn" type="submit" disabled={busy || !form.email || !form.password}>
          {busy ? '로그인 중…' : '로그인'}
        </button>
        <div className="center-link">
          <Link to="/register" className="text-btn">처음이신가요? <b style={{ color: 'var(--blue)' }}>회원가입</b></Link>
        </div>
      </div>
    </form>
    </div>
  )
}
