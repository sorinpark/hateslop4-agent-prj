/* 운동 목록 데이터 (운동 선택 화면 A).
   dummy.js의 단일 exercise(스쿼트 하드코딩)를 대체한다.

   - id: 백엔드 WS/세션에 넘어가는 식별자(영문 슬러그). schemas/백엔드와 맞춰야 함.
     이미지 파일명(NN_slug.png)의 slug와 동일하게 맞춰 이미지가 자동 매칭되게 한다.
   - name: 화면 표시용 한글.
   - parts: 부위 태그(중복 가능). 부위 필터에 쓰인다.
   - cameraHint: 카메라 가드 안내(운동마다 촬영 각도가 다름).

   이미지: frontend/src/assets/ 안에 NN_slug.png(레퍼런스 일러스트 42종)가 들어있다.
   getExerciseImage(id)가 파일명 slug로 매칭한다. */

// 부위 태그. 순서 = 필터 칩 노출 순서.
export const BODY_PARTS = [
  '가슴',
  '등',
  '하체',
  '어깨',
  '삼두',
  '이두',
  '코어',
  '전완근',
]

// 촬영 각도별 공용 카메라 안내 (운동마다 아래 중 하나를 고른다)
const HINT = {
  // 옆에서 전신 (하체/스쿼트/런지류)
  sideFull:
    '옆(측면)에서 무릎·발목·엉덩이가 다 보이도록 카메라를 두고, 전신이 화면에 들어오게 서주세요.',
  // 옆에서 상체 (푸시업/플랭크/코어 누운 자세)
  sideUpper:
    '옆(측면)에서 상체와 팔이 다 보이도록 카메라를 두고, 몸 전체가 화면에 들어오게 해주세요.',
  // 정면 전신 (팔벌려뛰기/제자리 뛰기류)
  frontFull:
    '정면에서 팔과 다리가 벌어지는 게 다 보이도록 카메라를 두고, 전신이 화면에 들어오게 서주세요.',
  // 정면 상체 (팔/어깨 서서 하는 운동)
  frontUpper:
    '정면에서 팔과 어깨 움직임이 다 보이도록 카메라를 두고, 상체 전체가 화면에 들어오게 서주세요.',
  // 옆에서 바닥 (윗몸일으키기/크런치/레그레이즈 등 바닥 운동)
  sideFloor:
    '옆(측면)에서 상체와 다리가 다 보이도록 카메라를 바닥 높이에 두고, 누운 몸 전체가 화면에 들어오게 해주세요.',
  // 매달리기 (턱걸이/풀업류)
  hang:
    '정면에서 상체와 팔이 다 보이도록 카메라를 두고, 매달린 상태에서 몸 전체가 화면에 들어오게 해주세요.',
}

/* 운동 목록 (레퍼런스 일러스트 42종). 한 번에 하나만 선택.
   parts는 주로 쓰는 부위 기준. cameraHint는 촬영 각도별 공용 문구를 재사용. */
export const EXERCISES = [
  { id: '01_sit-ups', name: '윗몸일으키기', parts: ['코어'], cameraHint: HINT.sideFloor },
  { id: '02_lunges', name: '런지', parts: ['하체', '코어'], cameraHint: HINT.sideFull },
  { id: '03_squats', name: '스쿼트', parts: ['하체', '코어'], cameraHint: HINT.sideFull },
  { id: '04_close-grip-push-ups', name: '클로즈그립 푸시업', parts: ['삼두', '가슴', '어깨'], cameraHint: HINT.sideUpper },
  { id: '05_chin-ups', name: '친업(언더그립 턱걸이)', parts: ['등', '이두'], cameraHint: HINT.hang },
  { id: '06_pull-ups', name: '풀업(턱걸이)', parts: ['등', '이두'], cameraHint: HINT.hang },
  { id: '07_push-ups', name: '푸시업', parts: ['가슴', '삼두', '어깨', '코어'], cameraHint: HINT.sideUpper },
  { id: '08_reverse-crunches', name: '리버스 크런치', parts: ['코어'], cameraHint: HINT.sideFloor },
  { id: '09_high-knees', name: '하이 니(무릎 올리기)', parts: ['하체', '코어'], cameraHint: HINT.frontFull },
  { id: '10_donkey-kicks', name: '동키 킥', parts: ['하체', '코어'], cameraHint: HINT.sideFull },
  { id: '11_tricep-dips', name: '트라이셉 딥스', parts: ['삼두', '어깨'], cameraHint: HINT.sideUpper },
  { id: '12_backfists', name: '백피스트', parts: ['어깨', '전완근'], cameraHint: HINT.frontUpper },
  { id: '13_scapular-shrugs', name: '견갑 슈러그', parts: ['등', '어깨'], cameraHint: HINT.frontUpper },
  { id: '14_chest-expansions', name: '체스트 익스팬션', parts: ['가슴', '어깨'], cameraHint: HINT.frontUpper },
  { id: '15_bicycle-crunches', name: '바이시클 크런치', parts: ['코어'], cameraHint: HINT.sideFloor },
  { id: '16_side-kicks', name: '사이드 킥', parts: ['하체', '코어'], cameraHint: HINT.frontFull },
  { id: '17_bridges', name: '브릿지', parts: ['하체', '코어'], cameraHint: HINT.sideFloor },
  { id: '18_tricep-extensions', name: '트라이셉 익스텐션', parts: ['삼두'], cameraHint: HINT.frontUpper },
  { id: '19_doorframe-rows', name: '도어프레임 로우', parts: ['등', '이두'], cameraHint: HINT.frontUpper },
  { id: '20_superman', name: '슈퍼맨', parts: ['등', '코어'], cameraHint: HINT.sideFloor },
  { id: '21_chest-squeezes', name: '체스트 스퀴즈', parts: ['가슴'], cameraHint: HINT.frontUpper },
  { id: '22_flutter-kicks', name: '플러터 킥', parts: ['코어', '하체'], cameraHint: HINT.sideFloor },
  { id: '23_climbers', name: '마운틴 클라이머', parts: ['코어', '하체', '어깨'], cameraHint: HINT.sideUpper },
  { id: '24_jump-knee-tucks', name: '점프 니 턱', parts: ['하체', '코어'], cameraHint: HINT.frontFull },
  { id: '25_get-ups', name: '겟업', parts: ['코어', '하체', '어깨'], cameraHint: HINT.sideFull },
  { id: '26_body-rows', name: '바디 로우(인버티드 로우)', parts: ['등', '이두'], cameraHint: HINT.sideUpper },
  { id: '27_back-lifts', name: '백 리프트', parts: ['등', '코어'], cameraHint: HINT.sideFloor },
  { id: '28_pike-push-ups', name: '파이크 푸시업', parts: ['어깨', '삼두'], cameraHint: HINT.sideUpper },
  { id: '29_leg-raises', name: '레그 레이즈', parts: ['코어'], cameraHint: HINT.sideFloor },
  { id: '30_plank-jump-ins', name: '플랭크 점프 인', parts: ['코어', '하체', '어깨'], cameraHint: HINT.sideUpper },
  { id: '31_fly-steps', name: '플라이 스텝', parts: ['하체', '코어'], cameraHint: HINT.frontFull },
  { id: '32_punches', name: '펀치', parts: ['어깨', '전완근'], cameraHint: HINT.frontUpper },
  { id: '33_sitting-pull-ups', name: '시티드 풀업', parts: ['등', '이두'], cameraHint: HINT.frontUpper },
  { id: '34_alt-arm-leg-plank', name: '교차 팔다리 플랭크', parts: ['코어', '어깨', '등'], cameraHint: HINT.sideUpper },
  { id: '35_shoulder-taps', name: '숄더 탭', parts: ['코어', '어깨'], cameraHint: HINT.sideUpper },
  { id: '36_elbow-plank', name: '엘보 플랭크', parts: ['코어', '어깨'], cameraHint: HINT.sideUpper },
  { id: '37_lunges-step-ups', name: '런지 스텝업', parts: ['하체', '코어'], cameraHint: HINT.sideFull },
  { id: '38_side-leg-raises', name: '사이드 레그 레이즈', parts: ['하체', '코어'], cameraHint: HINT.sideFloor },
  { id: '39_side-to-side-chops', name: '사이드 투 사이드 찹', parts: ['코어', '어깨'], cameraHint: HINT.frontUpper },
  { id: '40_pseudo-planche', name: '슈도 플란체', parts: ['어깨', '가슴', '삼두', '코어'], cameraHint: HINT.sideUpper },
  { id: '41_reverse-angels', name: '리버스 엔젤', parts: ['등', '어깨'], cameraHint: HINT.sideFloor },
  { id: '42_clapping-push-ups', name: '박수 푸시업', parts: ['가슴', '삼두', '어깨'], cameraHint: HINT.sideUpper },
]

/* 각 운동에 slug 부여: id에서 앞 번호(NN_)를 뗀 영문 슬러그.
   백엔드 세션/WS에는 이 slug를 넘긴다(DB에 03_squats 대신 squats 로 깔끔히 저장). */
for (const ex of EXERCISES) {
  ex.slug = ex.id.replace(/^\d+_/, '')
}

// id -> 운동 객체 빠른 조회
export function getExerciseById(id) {
  return EXERCISES.find((e) => e.id === id) ?? null
}

// slug -> 운동 객체 빠른 조회 (백엔드 세션 기록은 slug로 저장됨)
export function getExerciseBySlug(slug) {
  return EXERCISES.find((e) => e.slug === slug) ?? null
}

// 기본 운동(선택 없이 진입했을 때 폴백) = 스쿼트
export const DEFAULT_EXERCISE =
  EXERCISES.find((e) => e.id === '03_squats') ?? EXERCISES[0]

/* 운동 이미지 로더.
   src/assets/ 안의 NN_slug.png(레퍼런스 일러스트)를 Vite가 빌드 타임에 모아온다.
   파일명(확장자 제외)이 곧 id이므로 그대로 매칭한다.
   파일이 없으면 undefined -> 화면에서 플레이스홀더로 처리. */
const imageModules = import.meta.glob(
  './assets/*.{png,jpg,jpeg,webp}',
  { eager: true, query: '?url', import: 'default' },
)

// id -> 이미지 url 맵 (파일명에서 확장자만 떼어 키로)
const imageById = {}
for (const [path, url] of Object.entries(imageModules)) {
  const file = path.split('/').pop() // 03_squats.png
  const base = file.replace(/\.[^.]+$/, '') // 03_squats
  imageById[base] = url
}

export function getExerciseImage(id) {
  return imageById[id]
}
