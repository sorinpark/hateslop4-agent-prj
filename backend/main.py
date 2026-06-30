"""FastAPI 진입점 - 1주차 '끝까지 연결' 단계용 스켈레톤.

지금은 /profile, /feedback이 목(mock) 데이터를 돌려준다.
실제 LLM 연동은 profile.py / llm.py를 만들어 TODO 자리에 연결한다.

실행:  uvicorn main:app --reload
문서:  http://127.0.0.1:8000/docs  (자동 생성되는 API 테스트 페이지)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from schemas import (
    InjuryInput,
    ObservationProfile,
    FocusArea,
    Pattern,
    FeatureSummary,
    FeedbackResponse,
    FeedbackMessage,
)

app = FastAPI(title="부상 이력 기반 운동 피드백 AI Agent")

# React 개발 서버(Vite 기본 포트 5173)에서 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/profile", response_model=ObservationProfile)
def create_profile(injuries: list[InjuryInput]):
    """온보딩 입력 -> 관찰 프로필 생성.

    TODO(B&C): profile.py에서 Gemini(gemini-2.5-flash-lite) 호출로 교체.
    프롬프트 규칙: 병명을 '설명'하지 말 것 / '위험·진단' 단어 금지 /
    focus_areas는 category(input|linked|compensatory)와 reason을 함께 생성.
    아래는 우선 동작 확인용 목 데이터.
    """
    return ObservationProfile(
        user_id="u_demo",
        injuries=injuries,
        focus_areas=[
            FocusArea(area="오른쪽 발목", category="input", reason="직접 입력한 부위"),
            FocusArea(area="오른쪽 발뒤꿈치", category="linked", reason="발목과 함께 부담"),
            FocusArea(area="오른쪽 무릎", category="compensatory", reason="발목 보상 움직임 가능성"),
        ],
        watch_patterns=[Pattern.LR_IMBALANCE, Pattern.INSTABILITY, Pattern.LOAD_SHIFT],
    )


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(summary: FeatureSummary):
    """5~10초 특징 요약 -> 실시간 피드백 생성.

    카메라 가드: 신뢰도 미달이면 피드백을 만들지 않는다.
    TODO(B&C): llm.py에서 관찰 프로필 + summary로 패턴/제안 생성.
    확신형 표현("위험합니다","~하세요") 후처리 필터로 guardrail_passed 판정.
    """
    if summary.confidence.below_threshold:
        return FeedbackResponse(
            session_id=summary.session_id,
            window_end_s=summary.window.end_s,
            messages=[],
            guardrail_passed=True,
        )

    return FeedbackResponse(
        session_id=summary.session_id,
        window_end_s=summary.window.end_s,
        messages=[
            FeedbackMessage(
                type="observation",
                area="오른쪽 발목",
                text="오른쪽 발목에 부담이 쏠리는 패턴이 반복적으로 관찰돼요.",
                evidence=["load_shift", "lr_angle_diff.ankle"],
            ),
            FeedbackMessage(
                type="suggestion",
                text="이런 경우 일반적으로 발 너비를 조금 넓히는 게 도움이 된다고 알려져 있어요.",
                note_tag="참고 정보입니다",
            ),
        ],
        guardrail_passed=True,
    )