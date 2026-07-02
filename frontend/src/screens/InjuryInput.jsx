import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { emptyInjury, sideLabel } from '../dummy.js'

/* 부상 이력 입력 — schemas.InjuryInput 를 만든다.
   필드명: part / side / condition / discomfort  (schemas.py 그대로) */
export default function InjuryInput() {
  const navigate = useNavigate()
  const [injury, setInjury] = useState(emptyInjury)

  const set = (key, value) => setInjury((prev) => ({ ...prev, [key]: value }))

  // part 는 필수 (schemas 에서 not optional)
  const canSubmit = injury.part.trim().length > 0

  const handleNext = () => {
    // condition 은 선택(없으면 null). injuries 는 list[InjuryInput] 이므로 배열로.
    const injuries = [
      {
        part: injury.part.trim(),
        side: injury.side,
        condition: injury.condition.trim() || null,
        discomfort: injury.discomfort,
      },
    ]
    navigate('/profile', { state: { injuries } })
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

        {/* part */}
        <div className="field">
          <label className="field__label">불편한 부위</label>
          <input
            className="input"
            placeholder="예: 발목, 무릎, 손목"
            value={injury.part}
            onChange={(e) => set('part', e.target.value)}
          />
        </div>

        {/* side */}
        <div className="field">
          <label className="field__label">방향</label>
          <div className="segment">
            {['left', 'right', 'both'].map((s) => (
              <button
                key={s}
                type="button"
                className={
                  'segment__btn' + (injury.side === s ? ' segment__btn--on' : '')
                }
                onClick={() => set('side', s)}
              >
                {sideLabel[s]}
              </button>
            ))}
          </div>
        </div>

        {/* condition (선택) */}
        <div className="field">
          <label className="field__label">
            추정 병명 <span className="text-muted">(선택 — 몰라도 돼요)</span>
          </label>
          <input
            className="input"
            placeholder="예: 족저근막염"
            value={injury.condition}
            onChange={(e) => set('condition', e.target.value)}
          />
        </div>

        {/* discomfort 1~5 */}
        <div className="field">
          <label className="field__label">
            불편감 정도 <span className="text-muted">(1 약함 ~ 5 심함)</span>
          </label>
          <div className="segment">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                className={
                  'segment__btn' +
                  (injury.discomfort === n ? ' segment__btn--on' : '')
                }
                onClick={() => set('discomfort', n)}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
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
