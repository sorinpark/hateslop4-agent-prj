# Agentic V2 고도화 설계

이 브랜치는 기존 실시간 피드백 파이프라인을 유지하면서, HATESLOP에서 다룬 Agent/RAG/검증 개념을 실제 서비스 문제에 맞게 접목한 버전이다.

## 기존 구조

```text
MediaPipe landmark
-> FeatureSummary
-> Gemini 단일 호출
-> FeedbackResponse
```

기존 구조는 빠르고 단순하지만 매번 같은 경로를 탄다. 현재 윈도우가 피드백할 만한지, 최근에 같은 말을 했는지, 제안에 근거가 있는지 판단하는 별도 단계가 부족했다.

## Agentic V2 구조

```text
FeatureSummary + ObservationProfile
-> retrieve_context Tool
-> route Node
   -> skip: 낮은 신뢰도/의미 없는 변화면 LLM 호출 생략
   -> generate: RAG Tool 호출
-> retrieve_guidance Tool
-> Gemini structured generation
-> verifier Node
-> FeedbackResponse
```

## HATESLOP 학습 내용과 연결

| 학습 주제 | 적용 방식 |
|---|---|
| Prompt / Context Engineering | 부상 프로필, 현재 feature, 최근 history, guidance를 구분해 LLM 입력 구성 |
| RAG | 작은 로컬 운동 guidance corpus에서 현재 feature와 부위에 맞는 근거 문서 검색 |
| LLM Agent / LangGraph | StateGraph로 상태, Tool 호출, 조건 분기, 검증 단계를 명시 |
| Structured Output | google-genai response_schema로 messages JSON 강제 |
| Guardrail | 의료적 단정, 명령형 표현, 근거 없는 suggestion 제거 |
| Multi-Agent Orchestration | 이번 버전은 멀티 Agent 대신 단일 Orchestrator + Tool 구조로 지연/비용을 통제 |
| MCP / Docker | Tool 경계를 함수로 먼저 분리했다. 안정화 후 history/guidance Tool을 MCP 서버로 분리 가능 |
| Model Serving | 현재는 Gemini API 사용. vLLM 서빙은 별도 로컬 모델 실험이 필요할 때 후순위로 둔다 |

## 추가된 파일

- `backend/agent_tools.py`
  - `get_recent_feedback_context`: 같은 사용자/운동의 최근 피드백 조회 Tool
  - `retrieve_exercise_guidance`: 로컬 guidance RAG Tool
  - `has_meaningful_signal`: 낮은 가치의 윈도우 gate
  - `allowed_evidence_keys`: verifier용 근거 key 계산

- `backend/agentic_feedback.py`
  - LangGraph 기반 Agent flow
  - fallback runner 포함: langgraph 미설치 환경에서도 순차 실행 가능

- `backend/tests/test_agent_tools.py`
  - DB/LLM 없이 Tool 레이어 검증

## 실행 옵션

기본값은 Agentic V2 사용이다.

```bash
USE_AGENTIC_FEEDBACK=1
```

기존 baseline만 쓰고 싶으면 다음처럼 실행한다.

```bash
USE_AGENTIC_FEEDBACK=0
```

Agentic V2가 예외를 내면 `feedback.create_feedback()`이 자동으로 기존 baseline에 fallback한다.

## 포트폴리오/자소서용 한 문장

초기에는 실시간 자세 특징을 5초마다 단일 LLM 호출로 피드백화했지만, 반복 호출에 따른 비용과 맥락 단절을 줄이기 위해 LangGraph 기반 상태 관리, 히스토리 Tool, RAG 근거 검색, 검증 노드를 추가해 상태 기반 AI Agent 구조로 고도화했다.
