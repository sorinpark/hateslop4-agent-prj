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

/* ── 기록 묶음 헬퍼 ────────────────────────────────────────────────────
   세션 데이터는 더 이상 고정 mock 이 아니라, 실제 운동 종료 시 SessionContext 에
   쌓인다(localStorage 영속). 한 세션의 형식:
     { session_id, date(YYYY-MM-DD), exercise, duration_s, rep_count,
       report: FeedbackMessage[] }   // report 본문은 계약③ 형식 재사용
   주의: 세션 저장/리포트 DB 스키마는 schemas.py 에 아직 없다(Phase 2 ③ 담당).
   DB 스키마가 확정되면 이 형식을 그쪽에 맞춰 교체한다. */

// 초 -> "10분 12초"
export function fmtDuration(sec) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return s ? `${m}분 ${s}초` : `${m}분`
}
