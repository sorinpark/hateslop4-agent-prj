# 부상 이력 기반 개인화 운동 피드백 AI Agent

> 부상 부위별 부하 쏠림 패턴을 실시간으로 관찰하고, 참고 정보형 피드백을 제공하는 AI Agent.

---

## 프로젝트 구조

```
project/
├── frontend/        # React (담당: A)
├── backend/
│   ├── api/         # FastAPI 라우터
│   ├── vision/      # MediaPipe 특징 추출
│   ├── ai/          # LLM 프롬프트, 관찰 프로필 생성
│   └── db/          # SQLite 모델
├── data/            # 세션 저장 데이터
├── .env.example     # 환경변수 예시 (API 키 등)
├── requirements.txt
└── README.md
```

---

## 시작하기

### 1. 레포 클론

```bash
git clone https://github.com/[레포주소].git
cd [프로젝트폴더]
```

### 2. Python 가상환경 세팅

```bash
# 가상환경 생성
python -m venv venv

# 활성화 (Windows)
venv\Scripts\activate

# 활성화 (Mac/Linux)
source venv/bin/activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

```bash
# .env.example을 복사해서 .env 파일 만들기
cp .env.example .env
```

`.env` 파일을 열고 API 키 입력:

```
GROQ_API_KEY=여기에_키_입력
```

> Groq API 키는 [console.groq.com](https://console.groq.com) 에서 무료로 발급 가능

### 5. 백엔드 실행

```bash
cd backend
uvicorn api.main:app --reload
```

### 6. 프론트엔드 실행

```bash
cd frontend
npm install
npm start
```

---

## 기술 스택

| 영역 | 도구 |
|---|---|
| 관절 좌표 추출 | MediaPipe Pose |
| 특징 추출 / 영상 처리 | NumPy, OpenCV |
| 프론트엔드 | React |
| 백엔드 | FastAPI |
| DB | SQLite |
| LLM (개발/테스트) | Groq — LLaMA 3 (무료) |
| LLM (발표 데모) | Gemini 1.5 Flash (무료 티어) |

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