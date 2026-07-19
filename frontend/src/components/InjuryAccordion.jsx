import { useState } from 'react'
import { emptyInjury, sideLabel } from '../dummy.js'

export const MAX_INJURIES = 3

export function makeEmptyInjury() {
  return { ...emptyInjury }
}

/* 부상 이력 여러 건을 아코디언 카드로 입력/수정.
   injuries: InjuryInput[] (최소 1개), onChange(nextInjuries) 로 부모 상태를 갱신.
   한 번에 하나의 카드만 펼쳐져서, 3개를 추가해도 화면이 과하게 길어지지 않는다. */
export default function InjuryAccordion({ injuries, onChange }) {
  const [openIndex, setOpenIndex] = useState(0)

  const setField = (index, key, value) => {
    onChange(
      injuries.map((inj, i) => (i === index ? { ...inj, [key]: value } : inj)),
    )
  }

  const addInjury = () => {
    if (injuries.length >= MAX_INJURIES) return
    onChange([...injuries, makeEmptyInjury()])
    setOpenIndex(injuries.length)
  }

  const removeInjury = (index) => {
    if (injuries.length <= 1) return
    onChange(injuries.filter((_, i) => i !== index))
    setOpenIndex((prev) => {
      if (prev === index) return null
      if (prev > index) return prev - 1
      return prev
    })
  }

  return (
    <div className="field">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 8,
        }}
      >
        <label className="field__label" style={{ margin: 0 }}>
          부상 이력
        </label>
        <span className="text-muted">최대 3개까지 입력 가능</span>
      </div>

      {injuries.map((injury, index) => {
        const isOpen = openIndex === index
        const summary = injury.part
          ? `${sideLabel[injury.side]} ${injury.part}${
              injury.condition ? ` · ${injury.condition}` : ''
            } · 불편감 ${injury.discomfort}/5`
          : '아직 입력하지 않았어요'

        return (
          <div className="card" style={{ padding: 0 }} key={index}>
            <button
              type="button"
              onClick={() => setOpenIndex(isOpen ? null : index)}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                width: '100%',
                background: 'none',
                border: 'none',
                padding: 14,
                cursor: 'pointer',
                textAlign: 'left',
                font: 'inherit',
                color: 'inherit',
              }}
            >
              <div>
                <div className="focus-area">부상 {index + 1}</div>
                <div className="focus-reason">{summary}</div>
              </div>
              <span
                style={{
                  transform: isOpen ? 'rotate(180deg)' : 'none',
                  transition: 'transform .15s',
                  color: 'var(--text-muted)',
                  flexShrink: 0,
                  marginLeft: 10,
                }}
              >
                ⌄
              </span>
            </button>

            {isOpen && (
              <div style={{ padding: '0 14px 16px' }}>
                <div className="field">
                  <label className="field__label">불편한 부위</label>
                  <input
                    className="input"
                    placeholder="예: 발목, 무릎, 손목"
                    value={injury.part}
                    onChange={(e) => setField(index, 'part', e.target.value)}
                  />
                </div>

                <div className="field">
                  <label className="field__label">방향</label>
                  <div className="segment">
                    {['left', 'right', 'both'].map((s) => (
                      <button
                        key={s}
                        type="button"
                        className={
                          'segment__btn' +
                          (injury.side === s ? ' segment__btn--on' : '')
                        }
                        onClick={() => setField(index, 'side', s)}
                      >
                        {sideLabel[s]}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="field">
                  <label className="field__label">
                    추정 병명 <span className="text-muted">(선택)</span>
                  </label>
                  <input
                    className="input"
                    placeholder="예: 족저근막염"
                    value={injury.condition}
                    onChange={(e) =>
                      setField(index, 'condition', e.target.value)
                    }
                  />
                </div>

                <div
                  className="field"
                  style={{ marginBottom: injuries.length > 1 ? 12 : 0 }}
                >
                  <label className="field__label">
                    불편감 정도{' '}
                    <span className="text-muted">(1 약함 ~ 5 심함)</span>
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
                        onClick={() => setField(index, 'discomfort', n)}
                      >
                        {n}
                      </button>
                    ))}
                  </div>
                </div>

                {injuries.length > 1 && (
                  <button
                    type="button"
                    className="btn btn--ghost"
                    style={{ padding: '10px 16px', fontSize: 14 }}
                    onClick={() => removeInjury(index)}
                  >
                    이 부상 삭제
                  </button>
                )}
              </div>
            )}
          </div>
        )
      })}

      {injuries.length < MAX_INJURIES && (
        <button type="button" className="btn btn--ghost" onClick={addInjury}>
          + 부상 부위 추가
        </button>
      )}
    </div>
  )
}
