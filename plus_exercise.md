# 운동별 관절 인식 확장 (plus_exercise)

### 테스트 방법
cd backend/vision
python category_tuner.py {운동카테고리 목록}

q 키를 누르면 화면 종료되고, csv파일을 만듦. 이 csv파일을 AI에게 넣어서 임계값을 조정

## 0. 담당자별 운동 목록 + 임계값 조정 관련 정리 (요약)

### A — 등척성 유지형(8개) + 타격형(2개)

**등척성 유지형** — 관찰 관절: 몸통(trunk, 어깨-힙-발목), rep이 아니라 "일직선 유지 시간" 측정
1. 체스트 익스팬션 (chest-expansions)
2. 브릿지 (bridges)
3. 슈퍼맨 (superman)
4. 체스트 스퀴즈 (chest-squeezes)
5. 백 리프트 (back-lifts)
6. 교차 팔다리 플랭크 (alt-arm-leg-plank)
7. 숄더 탭 (shoulder-taps)
8. 엘보 플랭크 (elbow-plank)

**타격형** — 관찰 관절: 팔꿈치(좌우 번갈아 치는 리듬 주의)
1. 백피스트 (backfists)
2. 펀치 (punches)

### B — 복합/전신형(4개) + 팔 밀기형(7개)

**복합/전신형** — 관찰 관절: 여러 관절 조합(운동별로 다를 수 있음, 가장 까다로움)
1. 마운틴 클라이머 (climbers)
2. 겟업 (get-ups)
3. 플랭크 점프 인 (plank-jump-ins)
4. 사이드 투 사이드 찹 (side-to-side-chops)

**팔 밀기형** — 관찰 관절: 팔꿈치
1. 푸시업 (push-ups)
2. 클로즈그립 푸시업 (close-grip-push-ups)
3. 트라이셉 딥스 (tricep-dips)
4. 트라이셉 익스텐션 (tricep-extensions)
5. 파이크 푸시업 (pike-push-ups)
6. 슈도 플란체 (pseudo-planche)
7. 박수 푸시업 (clapping-push-ups)

### C — 팔 당기기형(7개) + 코어 굽힘형(5개)

**팔 당기기형** — 관찰 관절: 팔꿈치 + 어깨
1. 친업/언더그립 턱걸이 (chin-ups)
2. 풀업/턱걸이 (pull-ups)
3. 견갑 슈러그 (scapular-shrugs)
4. 도어프레임 로우 (doorframe-rows)
5. 바디 로우/인버티드 로우 (body-rows)
6. 시티드 풀업 (sitting-pull-ups)
7. 리버스 엔젤 (reverse-angels)

**코어 굽힘형** — 관찰 관절: 몸통-힙 각도
1. 윗몸일으키기 (sit-ups)
2. 리버스 크런치 (reverse-crunches)
3. 바이시클 크런치 (bicycle-crunches)
4. 플러터 킥 (flutter-kicks)
5. 레그 레이즈 (leg-raises)

### 임계값 조정, 카테고리당 한 번이면 되는가?

기본 구조상 `CategoryConfig`(임계값)는 **카테고리당 딱 한 세트**이고, 그 카테고리에 속한 운동들은 전부 같은 값을 공유한다. 따라서 절차는:

1. 카테고리 파일 하나 만들고 임계값 초안 채움
2. 아무 운동 하나로 `category_tuner.py` 돌리면서 rep count/hold 시간이 맞을 때까지 값 반복 조정
3. 값이 맞았다 싶으면, **그 카테고리에 속한 나머지 운동들도 각각 최소 1회씩** `category_tuner.py`로 실측해서, 이 한 세트의 임계값이 카테고리 내 다른 운동에도 통하는지 확인

즉 "임계값 자체를 정하는 작업"은 카테고리당 한 세트를 목표로 하지만, 그 한 세트가 카테고리 내 모든 운동에 맞는지 검증하려면 운동 하나하나를 다 돌려봐야 한다. 다만 문서에 미리 경고된 예외가 있다:
- **복합/전신형(B)**: 운동 4개가 서로 많이 달라 하나의 임계값으로 안 묶일 수 있음 — 안 맞으면 카테고리를 더 쪼개거나 운동별 예외를 둘 것
- **타격형(A)**: 좌우 번갈아 치는 동작이라 "좌우 평균" 방식이 안 맞을 수 있음 — 이 경우 `feature_extractor.py`까지 손대는 예외 로직이 필요할 수 있음

## 1. 배경 / 필요성

현재 프론트엔드(`frontend/src/exercises.js`)는 42개 운동 중 하나를 골라 실시간 운동 화면(`LiveExercise.jsx`)으로 넘어갈 수 있다. 선택한 운동의 `slug`는 `/session/start`, `/ws/exercise`를 통해 백엔드까지 전달된다.

하지만 실제로 조사해보니, **운동 선택은 지금 라벨(이름표) 역할만 하고 있고, 실질적인 관절 인식/반복 횟수(rep) 판정 로직은 스쿼트 하나만 구현돼 있다.**

- `backend/vision/angles.py`의 `JOINTS` 딕셔너리에는 무릎/발목/힙(좌우) 6개 관절만 정의돼 있다. 어깨·팔꿈치·손목·몸통 각도는 아직 없다.
- `backend/vision/feature_extractor.py`의 `WindowAccumulator._update_rep_count`는 좌우 평균 **무릎 각도**가 `REP_DOWN_THRESHOLD_DEG=100` ↔ `REP_UP_THRESHOLD_DEG=160`을 오가는지로만 rep을 센다. 운동 종류에 따른 분기가 전혀 없다.
- `exercise` 문자열은 `FeatureSummary.exercise`에 그대로 찍혀서 `feedback.py`의 LLM 프롬프트에 "운동: {exercise}"로 들어가긴 하지만, 그 앞에서 계산되는 feature 자체가 항상 무릎/발목/힙 기준이라 운동 이름과 실제 관찰 데이터가 안 맞는 경우가 많다.
- `backend/vision/spike_webcam.py`에도 `EXERCISE = "squat"`가 하드코딩돼 있어, 애초에 스쿼트 하나만 놓고 만들어지고 검증된 상태다.

**결과:** 스쿼트/런지처럼 무릎을 굽혔다 펴는 하체 운동은 그럭저럭 맞게 카운트되지만, 푸시업/턱걸이/플랭크/크런치처럼 무릎 각도와 무관한 나머지 운동들은 rep이 거의 안 세이거나 무의미한 값이 나온다. 에러 없이 조용히 틀리기 때문에 발견하기도 어렵다.

## 2. 목표

42개 운동을 몇 개의 **움직임 카테고리**로 묶고, 카테고리마다 "어떤 관절 각도를 볼지 + 반복(rep) 판정 임계값을 어떻게 잡을지"를 정의해서, 운동 선택이 실제로 관찰 로직에 반영되게 만든다.

참고로 42개 운동은 대략 이렇게 묶인다 (초안, 세부 배정은 1단계에서 표로 확정):

| 카테고리 | 필요한 관절 | 해당 운동 예시 |
|---|---|---|
| 하체 굽힘형 | 무릎 + 힙 (기존 로직 재사용) | 스쿼트, 런지, 스텝업, 하이니 등 |
| 팔 밀기형 | 팔꿈치 | 푸시업, 클로즈그립 푸시업, 딥스, 파이크 푸시업, 박수 푸시업 |
| 팔 당기기형 | 팔꿈치 + 어깨 | 친업, 풀업, 로우류, 시티드 풀업 |
| 코어 굽힘형 | 몸통-힙 각도 | 윗몸일으키기, 크런치류, 레그레이즈 |
| 등척성 유지형 | 카테고리마다 다름, **rep이 아닌 "유지 시간"** | 엘보 플랭크, 슈퍼맨, 체스트 스퀴즈 등 |
| 복합/전신형 | 여러 관절 조합 | 마운틴 클라이머, 겟업, 플랭크 점프인 |
| 타격형 | 팔꿈치(다른 리듬) | 펀치, 백피스트 |

## 3. 진행 방식 — 3단계

### 1단계: 공용 뼈대 구축 (dokong22222가 진행, **병렬 아님**)

이 단계를 나누지 않고 먼저 끝내는 이유: `angles.py`의 `JOINTS` 딕셔너리와 `feature_extractor.py`의 `WindowAccumulator`를 여러 명이 동시에 고치면 같은 파일, 같은 함수를 건드리게 돼서 merge conflict가 거의 확정적이다. 이 부분을 먼저 "카테고리별로 파일이 분리되는 구조"로 바꿔두면, 2단계부터는 각자 새 파일만 추가하면 되서 충돌이 사라진다.

**역할:** 이후 3명이 각자 독립적으로 작업할 수 있는 토대를 만드는 것. 임계값을 정확히 맞추는 게 목적이 아니라, "카테고리를 꽂아 넣을 수 있는 구조"를 만드는 것.

### 2단계: 카테고리별 병렬 구현 + 실측 테스트 (3인 병렬)

3명이 각자 카테고리(또는 카테고리 묶음)를 하나씩 맡아서, 자기 브랜치 + 자기 파일에서 작업한다. 실제 웹캠 앞에서 그 운동을 직접 해보면서 임계값을 맞추는 과정이 포함되므로, 이건 코드만으로 끝나지 않고 사람이 직접 테스트해야 한다. 각자 자기 기기의 웹캠으로 하기 때문에 서로 물리적으로 겹치지 않고 동시에 진행 가능하다.

**역할:** 카테고리별로 "쓸만한 rep 판정 로직"을 실제로 완성하는 것.

**추천 분담(3인 기준):** 등척성의 "유지 시간" 로직은 1단계에서 이미 구현해뒀기 때문에(STEP 1 참고), 이제 남은 6개 카테고리 중 진짜 손이 많이 가는 건 **복합/전신형(운동 4개가 서로 많이 달라 하나의 임계값으로 안 묶일 수 있음)** 뿐이다. 그래도 운동 개수(33개)를 3명이 비슷하게 나누도록 배분한다.

| 담당 | 카테고리 | 비고 |
|---|---|---|
| A | 등척성 유지형(8개) + 타격형(2개) | 둘 다 `CategoryConfig` 값만 채우면 되는 단순 튜닝 — 다만 타격형은 좌우 번갈아치는 동작이라 예외 로직이 필요할 수 있음(아래 가이드 참고) |
| B | 복합/전신형(4개) + 팔 밀기형(7개) | 복합형이 이 중 가장 까다로움(운동별로 따로 봐야 할 수도) — 밀기형은 단순해서 균형 맞춤 |
| C | 팔 당기기형(7개) + 코어 굽힘형(5개) | 둘 다 단순 튜닝 |

### 3단계: 통합(merge)

1단계에서 42개 슬러그 → 카테고리 매핑을 이미 다 채워뒀기 때문에, 2단계 각자의 PR은 "자기 카테고리 파일 추가" 정도로 범위가 좁아 충돌이 거의 없다. 순서대로 merge하고, 합친 뒤에는 42개 전체를 대상으로 스모크 테스트(적어도 값이 이상하지 않은지 확인)를 한 번 돈다.

**역할:** 각자 만든 걸 하나로 모으고, 빠진 카테고리/운동이 있는지 확인.

## 4. 단계별 세부 STEP

### STEP 1 — 공용 뼈대 ✅ 완료

- [x] `angles.py`의 `JOINTS`에 팔꿈치(어깨-팔꿈치-손목), 어깨(팔꿈치-어깨-힙), 몸통(어깨-힙-발목) 각도 추가
- [x] `backend/vision/categories/` 디렉토리 생성, 카테고리 모듈 인터페이스 설계
  - `categories/base.py` — `CategoryConfig` dataclass (rep 판정용 관절쌍/임계값 + lr_diff/stability/load_shift용 관절 목록 + `mode`)
  - `categories/squat.py` — 기존 스쿼트 로직을 그대로 옮긴 참조 구현
  - `categories/__init__.py` — `CATEGORIES`(구현된 카테고리) + `SLUG_TO_CATEGORY`(42개 전부 배정) + `get_category()` (미구현 카테고리는 `squat`로 안전하게 폴백)
- [x] `feature_extractor.py`를 이 인터페이스를 사용하도록 리팩토링 — `WindowAccumulator(exercise=...)`로 카테고리를 받아 rep 임계값/관절을 카테고리에서 가져오도록 변경. `main.py`의 `WindowAccumulator(window_seconds=5.0)` 호출에도 `exercise=exercise` 추가
- [x] 42개 운동 슬러그 → 카테고리 배정표 작성 (`categories/__init__.py`의 `SLUG_TO_CATEGORY`, 1차 초안 — 담당자가 실측하며 조정 가능)
- [x] 등척성(유지형) 운동을 위한 "유지 시간" 판정 로직 구현 (초안엔 설계만 하려 했으나, 2단계에서 카테고리 담당자가 코드까지 새로 짜야 하는 부담을 없애기 위해 1단계에서 마저 구현함)
  - `schemas.Window`에 `hold_seconds: float | None = None` 필드 추가(기존 `rep_count`는 그대로 필수 필드로 남아있고, hold 카테고리는 항상 0으로 채워짐 — 하위호환 유지).
  - `CategoryConfig`에 `hold_joint_pair` / `hold_min_deg` / `hold_max_deg` 추가. `WindowAccumulator`가 `mode == "hold"`일 때 이 관절 각도가 `[hold_min_deg, hold_max_deg]` 범위 안에 있는 시간을 프레임 간격만큼 누적해서 `Window.hold_seconds`로 내보낸다.
  - 즉 **등척성 카테고리도 이제 push/pull과 마찬가지로 `CategoryConfig` 값만 채우면 끝** — 코드를 새로 짤 필요 없음 (아래 5절 가이드 업데이트 참고). 가짜 랜드마크로 직접 검증(1.2초간 범위 안 유지 → `hold_seconds=1.2` 정확히 나옴, `rep_count=0` 유지)했다.
- [x] 리팩토링 후 스쿼트가 기존과 동일하게 동작하는지 확인 — `backend/vision/test_features.py` 8개 테스트 전부 통과 (feature 키 구성, rep count, load_shift 값 모두 리팩토링 전과 동일)
- [x] 카테고리 등록 방식을 "파일 추가 시 자동 등록"으로 변경 — 원래는 `categories/__init__.py`의 `CATEGORIES` 딕셔너리에도 한 줄 추가해야 했는데, 이러면 3명이 같은 파일을 건드리게 돼서 폴더 자동 스캔 방식(`pkgutil`)으로 바꿨다. `categories/<이름>.py`에 `CONFIG = CategoryConfig(...)`만 정의하면 그 즉시 적용된다 — `__init__.py`를 더 이상 안 건드려도 된다.
- [x] 카테고리 튜닝 전용 도구 `backend/vision/category_tuner.py` 신설 (아래 5-1절 참고).
- [x] `spike_webcam.py`(세션/프로필/피드백 API까지 호출하는 전체 파이프라인 스파이크)도 스쿼트 고정을 풀어 슬러그 인자를 받게 하고, visibility 점도 그 카테고리가 보는 관절로 뜨도록 일반화. 실시간 각도/임계값 텍스트 같은 새 디버그 오버레이는 안 넣고 원래 있던 것만 유지.

> ⚠️ **현재 상태**: `categories/`엔 아직 `squat.py`만 있다. `SLUG_TO_CATEGORY`는 42개 전부 카테고리 이름표를 붙여뒀지만, 그 이름에 해당하는 `<카테고리>.py` 파일이 없으면 `get_category()`가 `squat`로 폴백한다. **즉 지금은 어떤 운동을 선택해도 실제로는 전부 스쿼트 임계값(무릎 100°/160°)이 적용된다.** 카테고리별로 실제 값이 달라지는 건 2단계에서 `categories/<이름>.py` 파일을 추가하는 순간부터다(추가만 하면 됨, 별도 등록 단계 없음).

### STEP 2 — 카테고리별 구현 (담당자 1명당)

- [ ] 담당 카테고리 확정 (매핑표 기준)
- [ ] `categories/<카테고리>.py` 파일 생성, `CONFIG = CategoryConfig(...)` 정의 (5절 가이드의 예시를 시작점으로) — 이 파일 하나만 추가하면 그 즉시 적용됨(별도 등록 불필요)
- [ ] `python category_tuner.py <슬러그>`로 실제 운동하면서 화면 숫자 + CSV 로그 확인
- [ ] 임계값 조정 반복 (down/up 각도 또는 hold_min/max, 필요시 visibility 임계값도) — rep count/hold 시간이 실제로 맞을 때까지
- [ ] 담당 카테고리에 속한 운동들 각각 최소 1회 `category_tuner.py`로 실측 확인
- [ ] **실제 앱으로 최종 확인** — 프론트엔드에서 그 운동을 선택해 카메라 준비부터 세션 리포트까지 한 번 끝까지 돌려보고 이상 없는지 확인 (category_tuner.py는 이 부분을 대체하지 않음)
- [ ] PR 생성 (자기 새 파일 하나만 추가하는 것이므로 다른 파일 수정 없음)

### STEP 3 — 통합

- [ ] PR 병합 순서 정하기 (순차 병합 권장 — 한 번에 하나씩)
- [ ] 각 PR 리뷰: 관절 선택이 그 운동에 타당한지, 임계값에 실측 근거가 있는지
- [ ] 전부 merge 후 42개 슬러그 전체 스모크 테스트 (값이 0/이상치로 튀는 카테고리 없는지)
- [ ] 아직 못 채운 카테고리/운동 목록 정리 (다음 라운드로 이월)

## 5. 테스트 방법 + 카테고리별 설정 가이드 (2단계 시작점)

### 5-1. 테스트 도구 2개, 그리고 테스트는 2단계로 나눠서 한다

**도구:**
- `backend/vision/spike_webcam.py` — `/session/start`, `/profile`, `/feedback` API까지 호출해서 전체 파이프라인(LLM 피드백 포함)이 도는지 보는 용도. `python spike_webcam.py <슬러그>`로 실행하면(생략 시 squats) 그 카테고리를 실제로 적용하고, 화면에 찍는 visibility 점도 그 카테고리가 보는 관절로 바뀐다 — 원래는 스쿼트 관절(무릎/발목/힙)에 고정돼 있었는데 카테고리 시스템에 맞춰 일반화했다. `category_tuner.py`와 달리 실시간 각도/임계값 텍스트 오버레이는 없다(원래 있던 visibility 점 + 콘솔 JSON 출력만 유지).
- `backend/vision/category_tuner.py` — **이번에 새로 만든, 카테고리 임계값 튜닝 전용 도구.** `python category_tuner.py <슬러그>` (예: `python category_tuner.py push-ups`)로 실행하면, 백엔드 서버도 프론트엔드도 LLM 호출도 없이 웹캠 창 하나로 끝난다. 화면에 그 카테고리가 보는 관절 + 실시간 각도 + 임계값 + 지금 상태(up/down 또는 IN-RANGE/OUT) + 누적 rep/유지시간이 다 보인다. 그리고 **매 프레임의 시각/각도/상태를 `backend/vision/tuning_logs/<슬러그>_<시각>.csv`로도 저장한다** — 화면으로 눈대중하는 것 말고, 나중에 그 CSV를 열어서 각도가 실제로 어떻게 움직였는지 다시 보거나, AI에게 "이 각도 흐름 보고 임계값 추천해줘"라고 물어볼 때 근거로 쓸 수 있다(이 폴더는 개인 테스트 데이터라 `.gitignore`에 추가해뒀다 — 커밋 안 됨).

**테스트는 왜 2단계로 나눠서 하나:**
1. **1단계(빠른 반복) — `category_tuner.py`로 임계값만 맞추기.** 앱을 열고 운동 목록에서 선택 → 카메라 준비 → 운동 시작... 이 흐름을 매번 반복하면 값 하나 바꿀 때마다 너무 오래 걸린다. `category_tuner.py`는 웹캠만 있으면 되고 재실행이 빨라서, "값 바꾸고 → 몇 번 운동해보고 → 화면/CSV로 확인 → 다시 값 바꾸고"를 빠르게 반복하기 위한 용도다. **여기서 rep count가 실제 횟수랑 맞을 때까지 다듬는다.**
2. **2단계(최종 확인) — 실제 앱으로 한 번 더.** `category_tuner.py`는 관절/rep 판정만 보여주고, 실제 서비스 흐름(카메라 가드 → 운동 화면 → WebSocket → LLM 피드백 → 세션 리포트)까지 검증하진 않는다. 임계값이 어느 정도 맞았다 싶으면, **한 번은 꼭 실제 앱에서 그 운동을 선택해서 끝까지(피드백/리포트까지) 돌려보고 이상 없는지 확인해야 한다.** 이건 생략하면 안 되는 단계 — `category_tuner.py`만 돌리고 끝내면 실제 서비스에서 어떻게 보이는지 확인 안 한 채로 넘어가는 셈이다.

### 5-2. `CategoryConfig` 필드

`categories/base.py`의 `CategoryConfig`는 `mode`에 따라 다른 필드를 쓴다: `mode="rep"`이면 `rep_joint_pair`(rep 판정용 좌우 관절 쌍) + `rep_down/up_threshold_deg`(내려감/올라옴 임계각), `mode="hold"`면 `hold_joint_pair` + `hold_min/max_deg`(허용 각도 범위)를 채운다. 공통으로 `lr_diff_joints`(좌우 비교용 관절), `stability_joints`(흔들림·가동범위용 관절), `load_shift_joint_pair`(쏠림 판정용 관절 쌍, 없으면 `None`)도 채운다.

아래는 카테고리별 시작점 제안이다. **각도 숫자는 전부 추정치이며 실측 전이라 그대로 쓰면 안 된다** — 2단계의 핵심 작업이 바로 이 숫자를 실제로 맞추는 것이다. `angles.py`에 있는 관절 이름(`knee`/`ankle`/`hip`/`elbow`/`shoulder`/`trunk`, 전부 `L_`/`R_` 접두어)만 쓸 수 있다.

### 팔 밀기형 (push)
```python
CONFIG = CategoryConfig(
    name="push",
    rep_joint_pair=("L_elbow", "R_elbow"),
    rep_down_threshold_deg=90.0,   # 팔꿈치 깊게 굽힘 — 튜닝 필요
    rep_up_threshold_deg=160.0,    # 팔 펴짐 — 튜닝 필요
    lr_diff_joints=("elbow", "shoulder"),
    stability_joints=("elbow", "trunk"),   # trunk: 허리/골반 처짐 감지용
    load_shift_joint_pair=("L_shoulder", "R_shoulder"),
)
```

### 팔 당기기형 (pull)
```python
CONFIG = CategoryConfig(
    name="pull",
    rep_joint_pair=("L_elbow", "R_elbow"),
    rep_down_threshold_deg=70.0,   # 턱걸이류는 push보다 더 깊게 굽혀짐 — 튜닝 필요
    rep_up_threshold_deg=160.0,
    lr_diff_joints=("elbow", "shoulder"),
    stability_joints=("elbow", "shoulder"),
    load_shift_joint_pair=("L_shoulder", "R_shoulder"),
)
```

### 코어 굽힘형 (core_flex)
```python
CONFIG = CategoryConfig(
    name="core_flex",
    rep_joint_pair=("L_hip", "R_hip"),  # 스쿼트와 같은 관절이지만 누운 자세라 임계값은 완전히 다름
    rep_down_threshold_deg=130.0,  # 크런치 정점(상체가 많이 말림) — 튜닝 필요
    rep_up_threshold_deg=170.0,    # 누워서 편 상태 — 튜닝 필요
    lr_diff_joints=("hip",),
    stability_joints=("hip",),
    load_shift_joint_pair=None,   # 누운 자세라 좌우 쏠림 신호가 스쿼트만큼 의미 있지 않음
)
```

### 등척성 유지형 (isometric)
```python
CONFIG = CategoryConfig(
    name="isometric",
    mode="hold",
    hold_joint_pair=("L_trunk", "R_trunk"),
    hold_min_deg=160.0,   # 몸통(어깨-힙-발목) 일직선에 가까운 범위 — 튜닝 필요
    hold_max_deg=185.0,
    lr_diff_joints=("trunk",),
    stability_joints=("trunk",),   # 처짐/피케 감지
    load_shift_joint_pair=None,
)
```
1단계에서 "유지 시간" 판정 로직 자체는 이미 구현해뒀다(위 STEP 1 참고) — 이 카테고리도 이제 다른 카테고리들처럼 `CategoryConfig` 값만 채우면 된다. `hold_min/max_deg`(몸통이 얼마나 일직선이어야 "유지 중"으로 볼지)를 실측으로 맞추는 게 이 카테고리의 핵심 작업. `category_tuner.py`로 실행하면 화면에 IN-RANGE/OUT 상태가 실시간으로 뜨니 그걸 보고 범위를 좁혀가면 된다.

### 복합/전신형 (compound) — ⚠️ 운동별로 따로 봐야 할 수 있음
```python
CONFIG = CategoryConfig(
    name="compound",
    rep_joint_pair=("L_knee", "R_knee"),  # 시작점일 뿐 — 운동 4개(마운틴클라이머/겟업/플랭크점프인/사이드투사이드찹)가 서로 많이 다름
    rep_down_threshold_deg=110.0,
    rep_up_threshold_deg=160.0,
    lr_diff_joints=("knee", "shoulder"),
    stability_joints=("knee", "trunk"),
    load_shift_joint_pair=("L_hip", "R_hip"),
)
```
실측해보고 하나의 임계값으로 4개 운동이 다 안 맞으면, 이 카테고리를 더 쪼개거나 운동별 예외를 두는 것도 고려할 것.

### 타격형 (strike) — ⚠️ 좌우 번갈아 치는 동작 주의
```python
CONFIG = CategoryConfig(
    name="strike",
    rep_joint_pair=("L_elbow", "R_elbow"),  # 좌우 평균이라, 한쪽씩 번갈아 칠 땐 안 맞을 수 있음
    rep_down_threshold_deg=100.0,
    rep_up_threshold_deg=160.0,
    lr_diff_joints=("elbow", "shoulder"),
    stability_joints=("elbow",),
    load_shift_joint_pair=("L_shoulder", "R_shoulder"),
)
```
펀치/백피스트가 양팔 동시가 아니라 한쪽씩 번갈아 치는 동작이면, "좌우 평균" 방식(`rep_joint_pair`)으로는 rep이 잘 안 잡힐 수 있다. 실측해보고 안 맞으면 좌우 중 하나만 보거나, `_update_rep_count`에 "둘 중 하나라도 임계값을 넘으면" 같은 예외 로직이 필요할 수 있다(이 경우 `feature_extractor.py`도 같이 손대야 하니 미리 얘기하고 진행할 것).

## 6. 셋이 어떻게 합치는지 정리

- **브랜치 전략:** 1단계 뼈대를 먼저 main(또는 기준 브랜치)에 merge한 뒤, 그 지점에서 3명이 각자 `feature/category-<이름>` 브랜치를 딴다.
- **작업 범위 분리:** 각자 브랜치에서 **자기 카테고리 파일만** 새로 만들고 수정한다. 기존 공용 파일(`angles.py`, `feature_extractor.py`, 매핑표)은 1단계에서 이미 완성돼 있으므로 2단계에서는 손대지 않는 게 원칙이다.
- **PR 단위:** 카테고리 1개(또는 묶음) = PR 1개. 리뷰도 그 카테고리 로직이 타당한지 위주로 본다.
- **병합 순서:** 충돌 여지가 거의 없긴 하지만, 안전하게 한 명씩 순서대로 merge하고 나서 다음 사람 PR을 최신 기준 브랜치로 리베이스/머지하는 방식을 권장한다.
- **통합 후 확인:** 3개 PR이 다 들어간 뒤, 42개 전체 운동 리스트를 놓고 한 번 더 스모크 테스트를 돌려 빠진 부분이나 서로 충돌하는 가정(예: 같은 운동이 두 카테고리에 잘못 배정된 경우)이 없는지 확인한다.
