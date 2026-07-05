# 부상 이력 기반 개인화 운동 피드백 AI Agent

> 부상 부위별 부하 쏠림 패턴을 실시간으로 관찰하고, 참고 정보형 피드백을 제공하는 AI Agent.

---

## 프로젝트 구조

```
project/
├── frontend/                    # React (Vite)
│   └── src/
│       ├── screens/              # 화면 컴포넌트 (Splash, Disclaimer, InjuryInput,
│       │                          #  ObservationProfile, ProfileEdit, ExerciseHome,
│       │                          #  CameraGuard, LiveExercise, RecordsCalendar,
│       │                          #  SessionDetail, SessionReport)
│       ├── components/           # 공용 컴포넌트 (FeedbackCard, TabLayout)
│       ├── hooks/                # usePoseCamera.js — 브라우저 웹캠 + MediaPipe Tasks Vision 훅
│       ├── state/                # ProfileContext, SessionContext, storage.js
│       ├── api/                  # profile.js, sessions.js — 백엔드 REST 호출
│       └── .env.example          # VITE_API_BASE_URL
├── backend/
│   ├── main.py                   # FastAPI 진입점 — 전체 REST 라우트 + /ws/exercise
│   ├── profile.py                # 관찰 프로필 생성 (POST /profile 로직)
│   ├── feedback.py                # 실시간 피드백 생성 (LLM 호출 + 가드레일 후처리)
│   ├── llm.py                     # Gemini 클라이언트 (재시도/백오프 포함)
│   ├── schemas.py                 # Pydantic 스키마
│   ├── db/                        # SQLite 모델 + CRUD (models.py, repository.py)
│   ├── vision/                    # angles.py, feature_extractor.py (각도/윈도우 특징 추출)
│   │                              #  + spike_webcam.py (개발자 로컬 실험용, 프로덕션 경로 아님 — SPIKE_README.md 참고)
│   ├── data/                      # SQLite 파일(app.db), MediaPipe 모델(.task)
│   ├── requirements.txt
│   └── 백엔드_다음단계.md         # WebSocket 프로토콜 등 상세 진행 상황
├── .env.example                  # 백엔드 환경변수 예시 (GEMINI_API_KEY 등)
├── 기획.md
├── 실행계획_3인.md
└── README.md
```

---

## 시작하기

### 1. 레포 클론

```bash
git clone https://github.com/[레포주소].git
cd [프로젝트폴더]
```

### 2. 백엔드 — Python 가상환경 세팅

```bash
cd backend

# 가상환경 생성
python -m venv venv

# 활성화 (Windows)
venv\Scripts\activate

# 활성화 (Mac/Linux)
source venv/bin/activate
```

### 3. 백엔드 — 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

백엔드와 프론트엔드 둘 다 `.env`가 필요하다.

**백엔드** — 프로젝트 루트의 `.env.example`을 `backend/.env`로 복사:

```bash
cp .env.example backend/.env
```

```
GEMINI_API_KEY=여기에_키_입력
```

> Gemini API 키는 [aistudio.google.com/apikey](https://aistudio.google.com/apikey) 에서 무료로 발급 가능.
> `GEMINI_API_KEY`만 코드에서 실제로 읽는 환경변수다(`backend/llm.py`).
> DB 경로(`backend/db/repository.py`), CORS origin(`backend/main.py`), pose 모델 경로(`backend/vision/spike_webcam.py`)는
> 코드에 하드코딩되어 있어 환경변수 불필요.

**프론트엔드** — `frontend/.env.example`을 `frontend/.env`로 복사:

```bash
cp frontend/.env.example frontend/.env
```

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### 5. 백엔드 실행

```bash
cd backend
uvicorn main:app --reload
```

### 6. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

---

## 기술 스택

| 영역 | 도구 |
|---|---|
| 프론트엔드 | React 19 + Vite, react-router-dom |
| 관절 좌표 추출 (프로덕션, 실시간) | MediaPipe Tasks Vision — 브라우저(JS)에서 웹캠을 직접 열고 랜드마크만 WebSocket으로 전송 |
| 관절 좌표 추출 (개발자 로컬 실험) | MediaPipe Pose (Python, `backend/vision/spike_webcam.py`) — 프로덕션 경로 아님 |
| 특징 추출 | NumPy — `backend/vision/angles.py`, `feature_extractor.py` |
| 백엔드 | FastAPI + Uvicorn (REST + WebSocket) |
| DB | SQLite |
| LLM | Gemini (`google-genai` SDK) — 모델명은 `backend/llm.py`의 `MODEL` 상수 참고 |

---

## 아키텍처 개요

- **온보딩(프로필 생성)**: 부상 이력 입력 → `POST /profile` REST 호출 한 번으로 관찰 프로필(`ObservationProfile`)을 받아 저장.
- **실시간 운동 피드백**: 브라우저가 웹캠을 열고 MediaPipe Tasks Vision(JS)으로 매 프레임 관절 랜드마크를 추출한 뒤 WebSocket(`/ws/exercise`)으로 서버에 전송한다. 서버가 Python으로 로컬 웹캠을 여는 구조가 아니다.
- 서버는 세션(`session_id`)별로 격리된 윈도우 누적기에 랜드마크를 쌓다가 5초치가 모이면 `FeatureSummary`를 만들고, Gemini 기반 `feedback.py`를 호출해 생성된 피드백을 같은 WebSocket으로 돌려준다.
- 나머지 API: `GET /health`, `GET /profile/{user_id}`, `POST /session/start`, `POST /session/end/{id}`, `GET /sessions`, `GET /sessions/{id}/feedback`.
- 연결 파라미터·프레임 메시지 포맷 등 자세한 WebSocket 프로토콜은 [`backend/백엔드_다음단계.md`](backend/백엔드_다음단계.md) 참고.

---

## 개발 환경 버전

> ⚠️ 팀원들 환경 확인 후 채워주세요

| 항목 | 버전 |
|---|---|
| Python | [TODO] |
| Node.js | [TODO] |
| npm | [TODO] |

버전 확인 방법:
```bash
python --version
node --version
npm --version
```

---

## 브랜치 전략

```
main        — 최종 안정 버전 (직접 push 금지)
dev         — 통합 브랜치
feat/[이름] — 기능 개발 브랜치 (예: feat/mediapipe, feat/onboarding-ui)
```

- 작업은 `feat/` 브랜치에서 하고 `dev`로 PR
- 매주 금요일 체크포인트 후 `dev` → `main` 머지

---

## 주의사항

- `.env` 파일은 절대 커밋하지 말 것 (`.gitignore`에 포함되어 있음)
- 데이터 형식(특징 추출 JSON, LLM 응답 형식)이 바뀌면 **반드시 팀원들에게 먼저 공유** — 조용히 바꾸면 다른 사람 작업이 깨짐
- LLM 프롬프트/UI 문구 작업 시 "위험합니다", "~하세요" 같은 확신형 표현 쓰지 않기 (설계 원칙)

---

## 참고 문서

| 문서 | 내용 |
|---|---|
| `기획.md` | 설계 배경, 아키텍처 결정 근거, 개발 원칙 |
| `실행계획_3인.md` | 5주 일정, 주차별 목표, 역할 분담 |
| `backend/백엔드_다음단계.md` | 진행 상황, 남은 작업, WebSocket 프로토콜 상세 |