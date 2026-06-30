import { useNavigate, useLocation, Outlet } from 'react-router-dom'

/* 메인 앱 셸 — 하단 탭바(운동/기록) + 자식 화면.
   온보딩 화면에는 적용하지 않고, 운동/기록 묶음에만 감싼다. */
const TABS = [
  { to: '/app/exercise', label: '운동', icon: '🏋' },
  { to: '/app/records', label: '기록', icon: '🗓' },
  { to: '/app/profile', label: '프로필', icon: '👤' },
]

export default function TabLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <div className="tabbed">
      <div className="tabbed__body">
        <Outlet />
      </div>
      <nav className="tabbar">
        {TABS.map((t) => {
          const on = location.pathname.startsWith(t.to)
          return (
            <button
              key={t.to}
              className={'tabbar__btn' + (on ? ' tabbar__btn--on' : '')}
              onClick={() => navigate(t.to)}
            >
              <span className="tabbar__icon">{t.icon}</span>
              {t.label}
            </button>
          )
        })}
      </nav>
    </div>
  )
}
