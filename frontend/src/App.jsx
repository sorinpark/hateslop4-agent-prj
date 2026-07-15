import { Routes, Route, Navigate } from 'react-router-dom'
import Splash from './screens/Splash.jsx'
import Disclaimer from './screens/Disclaimer.jsx'
import InjuryInput from './screens/InjuryInput.jsx'
import ObservationProfile from './screens/ObservationProfile.jsx'
import TabLayout from './components/TabLayout.jsx'
import ExerciseHome from './screens/ExerciseHome.jsx'
import ExerciseSelect from './screens/ExerciseSelect.jsx'
import CameraGuard from './screens/CameraGuard.jsx'
import LiveExercise from './screens/LiveExercise.jsx'
import RecordsCalendar from './screens/RecordsCalendar.jsx'
import SessionReport from './screens/SessionReport.jsx'
import SessionDetail from './screens/SessionDetail.jsx'
import ProfileEdit from './screens/ProfileEdit.jsx'
import './onboarding.css'
import './exercise.css'
import './records.css'

/* 라우팅 (team_plan.md Phase 1).
   온보딩 묶음: 스플래시 → 면책 동의 → 부상 이력 입력 → 관찰 프로필
   운동 묶음(/app, 하단 탭바): 운동 홈 → 카메라 가드 → 실시간 운동
   기록 묶음(/app/records): 캘린더 → 날짜별 상세 / 세션 리포트 */
export default function App() {
  return (
    <div className="app-frame">
      <Routes>
        {/* 온보딩 (탭바 없음) */}
        <Route path="/" element={<Splash />} />
        <Route path="/disclaimer" element={<Disclaimer />} />
        <Route path="/injury" element={<InjuryInput />} />
        <Route path="/profile" element={<ObservationProfile />} />

        {/* 실시간 운동은 몰입 화면 — 탭바 밖(전체화면) */}
        <Route path="/app/exercise/live" element={<LiveExercise />} />

        {/* 메인 앱 (하단 탭바) */}
        <Route path="/app" element={<TabLayout />}>
          <Route index element={<Navigate to="exercise" replace />} />
          <Route path="exercise" element={<ExerciseHome />} />
          <Route path="exercise/select" element={<ExerciseSelect />} />
          <Route path="exercise/camera" element={<CameraGuard />} />
          <Route path="records" element={<RecordsCalendar />} />
          <Route path="records/report" element={<SessionReport />} />
          <Route path="records/:date" element={<SessionDetail />} />
          <Route path="profile" element={<ProfileEdit />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}
