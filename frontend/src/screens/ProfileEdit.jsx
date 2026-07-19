import { useState } from 'react'
import { useProfile, useProfileOrFallback } from '../state/ProfileContext.jsx'
import InjuryAccordion, {
  makeEmptyInjury,
} from '../components/InjuryAccordion.jsx'
import { sideLabel, patternLabel } from '../dummy.js'

/* 프로필 탭 — 부상 이력 조회/수정 (최대 3건).
   기본은 보기 모드(읽기 전용)이고, 우측 상단 "수정하기"를 눌러야 편집 폼이
   열린다. 현재 관찰 프로필의 injuries 를 폼 초기값으로 채우고, 저장 시
   updateInjuries 로 반영(localStorage 영속). 이 정보는 운동/리포트로 흐르고,
   백엔드 연동 시에도 POST /profile 의 입력으로 그대로 쓰인다.
   필드명은 schemas.InjuryInput 그대로: part / side / condition / discomfort. */
export default function ProfileEdit() {
  const { updateInjuries } = useProfile()
  const profile = useProfileOrFallback()

  const makeFormState = () =>
    profile.injuries.length > 0
      ? profile.injuries.map((inj) => ({
          part: inj.part ?? '',
          side: inj.side ?? 'right',
          condition: inj.condition ?? '',
          discomfort: inj.discomfort ?? 3,
        }))
      : [makeEmptyInjury()]

  const [mode, setMode] = useState('view') // 'view' | 'edit'
  const [injuries, setInjuries] = useState(makeFormState)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)

  const filledInjuries = injuries.filter((inj) => inj.part.trim().length > 0)
  const canSave = filledInjuries.length > 0

  const startEdit = () => {
    setInjuries(makeFormState())
    setSaveError(null)
    setMode('edit')
  }

  const cancelEdit = () => {
    setInjuries(makeFormState())
    setSaveError(null)
    setMode('view')
  }

  const handleSave = async () => {
    setSaving(true)
    setSaveError(null)
    try {
      await updateInjuries(
        filledInjuries.map((inj) => ({
          part: inj.part.trim(),
          side: inj.side,
          condition: inj.condition.trim() || null,
          discomfort: inj.discomfort,
        })),
      )
      setSaving(false)
      setMode('view')
    } catch (err) {
      setSaveError(err.message)
      setSaving(false)
    }
  }

  return (
    <div className="screen">
      <div className="screen__scroll">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
          }}
        >
          <div>
            <p className="eyebrow">프로필</p>
            <h2 className="title">부상 이력</h2>
          </div>
          {mode === 'view' ? (
            <button
              type="button"
              className="btn btn--ghost"
              style={{ marginTop: 4, width: 'auto', padding: '8px 16px' }}
              onClick={startEdit}
            >
              수정하기
            </button>
          ) : (
            <button
              type="button"
              className="btn btn--ghost"
              style={{ marginTop: 4, width: 'auto', padding: '8px 16px' }}
              onClick={cancelEdit}
            >
              취소
            </button>
          )}
        </div>

        {mode === 'view' ? (
          <>
            <p className="subtitle">현재 등록된 부상 정보예요.</p>

            {profile.injuries.map((inj, i) => (
              <div key={i} style={{ marginBottom: 16 }}>
                {profile.injuries.length > 1 && (
                  <h3 className="field__label" style={{ marginTop: 0 }}>
                    부상 {i + 1}
                  </h3>
                )}
                <div className="info-grid" style={{ marginBottom: 0 }}>
                  <div className="info-grid__item">
                    <div className="info-grid__label">불편한 부위</div>
                    <div className="info-grid__value">
                      {inj.part || '미입력'}
                    </div>
                  </div>
                  <div className="info-grid__item">
                    <div className="info-grid__label">방향</div>
                    <div className="info-grid__value">
                      {sideLabel[inj.side] ?? inj.side}
                    </div>
                  </div>
                  <div className="info-grid__item">
                    <div className="info-grid__label">추정 병명</div>
                    <div className="info-grid__value">
                      {inj.condition || '미입력'}
                    </div>
                  </div>
                  <div className="info-grid__item">
                    <div className="info-grid__label">불편감 정도</div>
                    <div className="info-grid__value">
                      {inj.discomfort} / 5
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </>
        ) : (
          <>
            <p className="subtitle">
              여기서 부상 정보를 바꾸면 운동 중 관찰 기준과 리포트에 바로 반영돼요.
            </p>

            <InjuryAccordion injuries={injuries} onChange={setInjuries} />
          </>
        )}

        {/* 현재 관찰 프로필 요약(반영 결과) */}
        <h3 className="field__label" style={{ marginTop: 8 }}>
          현재 관찰 패턴
        </h3>
        <div className="tags">
          {profile.watch_patterns.map((p) => (
            <span className="tag" key={p}>
              {patternLabel[p] ?? p}
            </span>
          ))}
        </div>
        <span className="note-tag">{profile.disclaimer}</span>
      </div>

      {mode === 'edit' && (
        <div className="screen__footer">
          {saveError && (
            <p
              className="text-muted"
              style={{ textAlign: 'center', marginBottom: 10 }}
            >
              {saveError}
            </p>
          )}
          <button
            className="btn btn--primary"
            disabled={!canSave || saving}
            onClick={handleSave}
          >
            {saving ? '저장 중...' : '저장하기'}
          </button>
        </div>
      )}
    </div>
  )
}
