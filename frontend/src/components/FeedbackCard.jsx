/* 계약③ FeedbackMessage 한 건을 카드로 렌더.
   { type:"observation"|"suggestion", text, area?, evidence[], note_tag? }
   note_tag 는 suggestion 에만 붙는다 (기획.md 9번).
   실시간 화면과 리포트/상세 화면이 같은 표현을 쓰도록 공용화. */
function evidenceLabel(item) {
  if (item.startsWith('guidance:')) return `가이드 ${item.replace('guidance:', '')}`
  return `관찰값 ${item}`
}

export default function FeedbackCard({ msg }) {
  const evidence = msg.evidence ?? []

  return (
    <div className={'fb' + (msg.type === 'suggestion' ? ' fb--suggestion' : '')}>
      <div className="fb__head">
        <span className="fb__kind">
          {msg.type === 'suggestion' ? '제안' : '관찰'}
        </span>
        {msg.area && <span className="fb__area">· {msg.area}</span>}
      </div>
      <p className="fb__text">{msg.text}</p>
      {evidence.length > 0 && (
        <div className="fb__evidence">
          <span className="fb__evidence-label">근거</span>
          <div className="fb__evidence-list">
            {evidence.map((item) => (
              <span className="fb__evidence-chip" key={item}>
                {evidenceLabel(item)}
              </span>
            ))}
          </div>
        </div>
      )}
      {msg.note_tag && <span className="note-tag">{msg.note_tag}</span>}
    </div>
  )
}
