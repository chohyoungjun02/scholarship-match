import { useEffect } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import { TabBar, TopHeader, useIsDesktop } from './components/ui.jsx'
import Home from './pages/Home.jsx'
import Login from './pages/Login.jsx'
import Profile from './pages/Profile.jsx'
import Register from './pages/Register.jsx'
import Scholarships from './pages/Scholarships.jsx'
import SelectSchool from './pages/SelectSchool.jsx'

function Private({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="screen"><div className="spinner" style={{ marginTop: 120 }} /></div>
  return user ? children : <Navigate to="/login" replace />
}

const TAB_PATHS = ['/', '/all', '/profile']

export default function App() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [params] = useSearchParams()
  const desktop = useIsDesktop()
  const onboarding = params.get('onboarding') === '1'
  // 앱(모바일): 하단 탭바 / 웹(데스크톱): 상단 내비게이션
  const showTab = !desktop && user && TAB_PATHS.includes(pathname) && !onboarding

  useEffect(() => {
    window.scrollTo(0, 0) // 화면 이동 시 맨 위부터
  }, [pathname])

  return (
    <div className={`app ${desktop ? 'is-web' : 'is-app'}`}>
      {desktop && <TopHeader user={onboarding ? null : user} onLogout={() => { logout(); navigate('/login') }} />}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/school" element={<Private><SelectSchool /></Private>} />
        <Route path="/profile" element={<Private><Profile /></Private>} />
        <Route path="/all" element={<Private><Scholarships /></Private>} />
        <Route path="/" element={<Private><Home /></Private>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      {showTab && <TabBar />}
    </div>
  )
}
