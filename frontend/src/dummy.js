/* 더미 데이터 — API 연동 전 화면 동작 확인용.
   필드명은 backend/schemas.py를 그대로 따른다 (임의 변경 금지).

   InjuryInput        : { part, side, condition, discomfort }
   FocusArea          : { area, category, reason }
   ObservationProfile : { user_id, injuries, focus_areas, watch_patterns, disclaimer }
   Pattern(enum 값)   : lr_imbalance | instability | late_fatigue | rom_asymmetry | load_shift
*/

// 부상 이력 입력 화면의 초기값 (InjuryInput 1건)
export const emptyInjury = {
  part: '',
  side: 'right', // "left" | "right" | "both"
  condition: '',
  discomfort: 3, // 1~5
}

// Pattern enum -> 한글 라벨 (라벨 매핑은 프론트 책임, schemas.py 주석 참고)
export const patternLabel = {
  lr_imbalance: '좌우 불균형',
  instability: '흔들림 증가',
  late_fatigue: '운동 후반 안정성 감소',
  rom_asymmetry: '좌우 가동범위 차이',
  load_shift: '부위별 부하 쏠림',
}

// FocusArea.category -> 한글 라벨
export const categoryLabel = {
  input: '입력',
  linked: '연결',
  compensatory: '보상 가능',
}

// side -> 한글 라벨
export const sideLabel = {
  left: '왼쪽',
  right: '오른쪽',
  both: '양쪽',
}

/* 관찰 프로필 화면이 받는 더미 ObservationProfile.
   실제로는 부상 입력 -> POST /profile -> LLM 생성 결과로 교체된다.
   여기서는 입력된 injuries를 받아 그대로 끼워 넣고 나머지는 고정 더미. */
export function makeDummyProfile(injuries) {
  return {
    user_id: 'u_demo',
    injuries,
    focus_areas: [
      { area: '오른쪽 발목', category: 'input', reason: '직접 입력한 부위' },
      { area: '오른쪽 발뒤꿈치', category: 'linked', reason: '발목과 함께 부담' },
      {
        area: '오른쪽 무릎',
        category: 'compensatory',
        reason: '발목 보상 움직임 가능성',
      },
    ],
    watch_patterns: ['lr_imbalance', 'instability', 'load_shift'],
    disclaimer: '의학적 진단이 아닌 사용자 입력 기반 참고 정보',
  }
}

/* ── 운동 묶음 ─────────────────────────────────────────────────────────
   MVP 운동 1종은 스쿼트 (기획.md / 실행계획_3인.md 결정). */
export const exercise = {
  id: 'squat',
  name: '스쿼트',
  // 카메라 가드 안내 (기획.md 4-7-가: 운동별 안내 문구)
  cameraHint: '무릎과 발목이 잘 보이도록 카메라를 옆(측면)에 두고, 전신이 화면에 들어오게 서주세요.',
}

/* 카메라 가드용 더미 Confidence (schemas.Confidence).
   overall 0~1, below_threshold=true 면 피드백을 시작하지 않는다. */
export const dummyConfidence = {
  overall: 0.92,
  interp_ratio: 0.0,
  below_threshold: false,
}

/* 실시간 화면이 시간순으로 받는 더미 FeedbackResponse 목록.
   각 항목은 schemas.FeedbackResponse 형식:
     { session_id, window_end_s, messages[], guardrail_passed }
   messages[] 는 schemas.FeedbackMessage:
     { type: "observation"|"suggestion", text, area?, evidence[], note_tag? }
   note_tag 는 suggestion 에만 붙는다 (기획.md 9번: 제안에만 참고 정보 태그). */
export const dummyFeedbackStream = [
  {
    session_id: 's_demo',
    window_end_s: 8,
    guardrail_passed: true,
    messages: [
      {
        type: 'observation',
        area: '오른쪽 발목',
        text: '오른쪽 발목에 부담이 쏠리는 패턴이 반복적으로 관찰돼요.',
        evidence: ['load_shift', 'lr_angle_diff.ankle'],
      },
    ],
  },
  {
    session_id: 's_demo',
    window_end_s: 16,
    guardrail_passed: true,
    messages: [
      {
        type: 'observation',
        area: '무릎',
        text: '왼쪽 무릎이 안쪽으로 쏠리는 움직임이 늘어나는 편이에요.',
        evidence: ['lr_imbalance', 'knee_valgus'],
      },
      {
        type: 'suggestion',
        text: '이런 경우 일반적으로 발 너비를 조금 넓히는 게 도움이 된다고 알려져 있어요. 본인에게 맞는지는 전문가와 상담을 권장해요.',
        note_tag: '참고 정보입니다',
      },
    ],
  },
  {
    session_id: 's_demo',
    window_end_s: 24,
    guardrail_passed: true,
    messages: [
      {
        type: 'observation',
        area: '오른쪽 발목',
        text: '후반부로 갈수록 흔들림이 조금씩 커지는 패턴이 보여요.',
        evidence: ['instability', 'late_fatigue'],
      },
    ],
  },
]

/* 실시간 화면 종료 시 만드는 더미 세션 요약 (기록 묶음에서 재사용 예정).
   실제로는 세션 종료 -> 누적 데이터 -> 리포트 LLM 호출로 생성된다. */
export function makeDummySession(durationSec, feedbackCount) {
  return {
    session_id: 's_demo',
    exercise: exercise.id,
    duration_s: durationSec,
    rep_count: 12,
    feedback_count: feedbackCount,
  }
}

/* ── 기록 묶음 ─────────────────────────────────────────────────────────
   주의: 세션 저장/리포트 DB 스키마는 schemas.py 에 아직 없다(Phase 2 ③ 담당).
   그래서 아래 세션/리포트 형식은 "확정 계약"이 아니라 화면용 잠정 더미다.
   리포트 본문 메시지만은 기존 계약③(FeedbackMessage: type/text/area/note_tag)을
   그대로 재사용한다 — 임의 필드명 신설을 피하기 위함.
   DB 스키마가 확정되면 이 더미를 그 형식으로 교체한다. */

// 한 세션 = 메타 + 그 세션의 리포트 메시지(FeedbackMessage[] 형식)
export const dummySessions = [
  {
    session_id: 's_0628',
    date: '2026-06-28',
    exercise: 'squat',
    duration_s: 612,
    rep_count: 24,
    // 세션 종료 후 리포트 LLM 이 만든 요약 메시지 (계약③ 형식 재사용)
    report: [
      {
        type: 'observation',
        area: '오른쪽 발목',
        text: '이번 세션에서 오른쪽 발목 쪽으로 부담이 쏠리는 패턴이 자주 보였어요.',
        evidence: ['load_shift'],
      },
      {
        type: 'observation',
        area: '무릎',
        text: '2세트 이후부터 왼쪽 무릎 흔들림이 조금 늘었어요.',
        evidence: ['instability', 'late_fatigue'],
      },
      {
        type: 'suggestion',
        text: '다음엔 세트 사이 휴식을 조금 늘려보는 것도 도움이 된다고 알려져 있어요. 본인에게 맞는지는 전문가와 상담을 권장해요.',
        note_tag: '참고 정보입니다',
      },
    ],
  },
  {
    session_id: 's_0629',
    date: '2026-06-29',
    exercise: 'squat',
    duration_s: 540,
    rep_count: 20,
    report: [
      {
        type: 'observation',
        area: '오른쪽 발목',
        text: '지난번과 비슷하게 오른쪽 발목 쏠림이 반복적으로 관찰됐어요.',
        evidence: ['load_shift', 'lr_imbalance'],
      },
      {
        type: 'suggestion',
        text: '발 너비를 약간 넓혀서 서보면 쏠림이 줄어드는 경우가 있다고 알려져 있어요. 전문가 상담을 권장해요.',
        note_tag: '참고 정보입니다',
      },
    ],
  },
]

// 날짜(YYYY-MM-DD) -> 세션 빠른 조회
export function sessionByDate(date) {
  return dummySessions.find((s) => s.date === date) ?? null
}

// 운동 기록이 있는 날짜 집합 (캘린더 마커용)
export const sessionDates = dummySessions.map((s) => s.date)

// 초 -> "10분 12초"
export function fmtDuration(sec) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return s ? `${m}분 ${s}초` : `${m}분`
}
