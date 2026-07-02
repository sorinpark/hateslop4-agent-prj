import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

/* 면책 동의 — 앱 최초 진입 시 명시적 동의(체크박스).
   기획.md 9번 UI 배치 원칙: 단순 텍스트 노출보다 명시적 동의 흐름. */
export default function Disclaimer() {
  const navigate = useNavigate()
  const [agreed, setAgreed] = useState(false)

  return (
    <div className="screen">
      <div className="steps">
        <span className="steps__dot steps__dot--on" />
        <span className="steps__dot" />
        <span className="steps__dot" />
      </div>

      <div className="screen__scroll">
        <p className="eyebrow">시작하기 전에</p>
        <h2 className="title">잠깐, 꼭 확인해 주세요</h2>

        <div className="card">
          <p className="subtitle" style={{ margin: 0 }}>
            본 앱은 의료기기가 아니며, 전문의 및 물리치료사의 진단과 처방을
            대체하지 않습니다. 본 앱의 피드백은 패턴 관찰에 기반한 운동 보조
            정보이며, 의학적 진단이 아닙니다. 운동 중 통증이 발생할 경우 즉시
            중단하고 전문가 상담을 권장합니다.
          </p>
        </div>

        <label className="consent">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
          />
          <span className="consent__text">
            위 내용을 확인했으며, 패턴 관찰 기반 참고 정보로 이해하고 사용하는
            데 동의합니다.
          </span>
        </label>
      </div>

      <div className="screen__footer">
        <button
          className="btn btn--primary"
          disabled={!agreed}
          onClick={() => navigate('/injury')}
        >
          동의하고 계속
        </button>
      </div>
    </div>
  )
}
