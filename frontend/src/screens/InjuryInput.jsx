import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import InjuryAccordion, {
  makeEmptyInjury,
} from '../components/InjuryAccordion.jsx'

/* 부상 이력 입력 — schemas.InjuryInput 여러 건을 만든다 (최대 3개).
   필드명: part / side / condition / discomfort  (schemas.py 그대로) */
export default function InjuryInput() {
  const navigate = useNavigate()
  const [injuries, setInjuries] = useState([makeEmptyInjury()])

  // 부위를 입력한 항목만 유효. 최소 1개는 있어야 다음으로 갈 수 있다.
  const filledInjuries = injuries.filter((inj) => inj.part.trim().length > 0)
  const canSubmit = filledInjuries.length > 0

  const handleNext = () => {
    // condition 은 선택(없으면 null). injuries 는 list[InjuryInput] 이므로 배열로.
    const payload = filledInjuries.map((inj) => ({
      part: inj.part.trim(),
      side: inj.side,
      condition: inj.condition.trim() || null,
      discomfort: inj.discomfort,
    }))
    navigate('/profile', { state: { injuries: payload } })
  }

  return (
    <div className="screen">
      <div className="steps">
        <span className="steps__dot steps__dot--on" />
        <span className="steps__dot steps__dot--on" />
        <span className="steps__dot" />
      </div>

      <div className="screen__scroll">
        <p className="eyebrow">2 / 3 · 부상 이력</p>
        <h2 className="title">어디가 불편하신가요?</h2>
        <p className="subtitle">
          입력하신 부위는 진단이 아니라, 어디를 더 주의 깊게 관찰할지
          정하는 데만 쓰여요.
        </p>

        <InjuryAccordion injuries={injuries} onChange={setInjuries} />
      </div>

      <div className="screen__footer">
        <button
          className="btn btn--primary"
          disabled={!canSubmit}
          onClick={handleNext}
        >
          관찰 프로필 만들기
        </button>
      </div>
    </div>
  )
}
