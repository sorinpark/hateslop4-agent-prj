import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  EXERCISES,
  BODY_PARTS,
  getExerciseImage,
} from '../exercises.js'
import { useExercise } from '../state/ExerciseContext.jsx'

/* 운동 선택 화면 (축 A).
   부위 필터(중복 선택)로 운동을 좁히고, 하나를 골라 시작한다.
   레퍼런스처럼 각 운동에 이미지(없으면 플레이스홀더)를 보여준다. */
export default function ExerciseSelect() {
  const navigate = useNavigate()
  const { exerciseId, selectExercise } = useExercise()

  // 선택된 부위 필터(복수). 비어 있으면 전체.
  const [activeParts, setActiveParts] = useState([])
  // 운동명 검색어
  const [query, setQuery] = useState('')
  // 이 화면에서 임시로 고른 운동(아직 확정 전). 기존 선택을 초기값으로.
  const [picked, setPicked] = useState(exerciseId)

  const togglePart = (part) =>
    setActiveParts((prev) =>
      prev.includes(part) ? prev.filter((p) => p !== part) : [...prev, part],
    )

  // 검색어 정규화(공백/대소문자 무시)
  const q = query.trim().toLowerCase()

  // 부위 필터 + 검색어 필터 동시 적용.
  // 검색은 한글명(name)과 영문 슬러그(slug) 둘 다에서 부분일치.
  const visible = EXERCISES.filter((ex) => {
    const partOk =
      activeParts.length === 0 || ex.parts.some((p) => activeParts.includes(p))
    const queryOk =
      q === '' ||
      ex.name.toLowerCase().includes(q) ||
      ex.slug.toLowerCase().includes(q)
    return partOk && queryOk
  })

  const start = () => {
    if (!picked) return
    selectExercise(picked)
    navigate('/app/exercise') // 선택 후 운동 홈으로
  }

  const pickedEx = picked ? EXERCISES.find((e) => e.id === picked) : null

  return (
    <div className="screen ex-select">
      <div className="screen__scroll">
        <p className="eyebrow">운동 선택</p>
        <h2 className="title">어떤 운동을 해볼까요?</h2>

        {/* 운동명 검색 */}
        <div className="ex-search">
          <span className="ex-search__icon" aria-hidden="true">🔍</span>
          <input
            className="ex-search__input"
            type="search"
            inputMode="search"
            placeholder="운동 이름 검색 (예: 스쿼트, 푸시업)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {query && (
            <button
              type="button"
              className="ex-search__clear"
              onClick={() => setQuery('')}
              aria-label="검색어 지우기"
            >
              
            </button>
          )}
        </div>

        {/* 부위 필터 (중복 선택) */}
        <div className="part-filter">
          {BODY_PARTS.map((part) => (
            <button
              key={part}
              type="button"
              className={
                'part-chip' + (activeParts.includes(part) ? ' part-chip--on' : '')
              }
              onClick={() => togglePart(part)}
            >
              {part}
            </button>
          ))}
        </div>

        {/* 운동 리스트 */}
        <div className="ex-list">
          {visible.map((ex) => {
            const img = getExerciseImage(ex.id)
            const on = picked === ex.id
            return (
              <button
                key={ex.id}
                type="button"
                className={'ex-item' + (on ? ' ex-item--on' : '')}
                onClick={() => setPicked(ex.id)}
              >
                <span className="ex-item__thumb">
                  {img ? (
                    <img src={img} alt={ex.name} />
                  ) : (
                    <span className="ex-item__thumb-ph">{ex.name}</span>
                  )}
                </span>
                <span className="ex-item__body">
                  <span className="ex-item__name">{ex.name}</span>
                  <span className="ex-item__parts">
                    {ex.parts.map((p) => (
                      <span className="ex-item__part" key={p}>
                        {p}
                      </span>
                    ))}
                  </span>
                </span>
                {on && <span className="ex-item__check">✓</span>}
              </button>
            )
          })}
          {visible.length === 0 && (
            <p className="text-muted" style={{ textAlign: 'center' }}>
              {q ? `'${query}' 검색 결과가 없어요.` : '해당 부위 운동이 아직 없어요.'}
            </p>
          )}
        </div>
      </div>

      {/* 운동을 고르면 navbar 위에 반투명 고정 바로 떠오른다(스크롤 불필요) */}
      <div className={'ex-startbar' + (picked ? ' ex-startbar--on' : '')}>
        {pickedEx && (
          <span className="ex-startbar__label">
            선택: <b>{pickedEx.name}</b>
          </span>
        )}
        <button
          className="btn btn--primary"
          disabled={!picked}
          onClick={start}
        >
          이 운동으로 시작
        </button>
      </div>
    </div>
  )
}
