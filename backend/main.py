"""FastAPI 진입점 - 1주차 '끝까지 연결' 단계용 스켈레톤.

지금은 /profile, /feedback이 목(mock) 데이터를 돌려준다.
실제 LLM 연동은 profile.py / llm.py를 만들어 TODO 자리에 연결한다.

실행:  uvicorn main:app --reload
문서:  http://127.0.0.1:8000/docs  (자동 생성되는 API 테스트 페이지)
"""
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.genai import errors as genai_errors
from pydantic import BaseModel

from schemas import (
    InjuryInput,
    ObservationProfile,
    FeatureSummary,
    FeedbackResponse,
)
import profile as profile_svc
import feedback as feedback_svc
from db import repository as db_repo

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_repo.init_db()
    yield


app = FastAPI(title="부상 이력 기반 운동 피드백 AI Agent", lifespan=lifespan)

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
    """온보딩 입력 -> 관찰 프로필 생성 (Gemini, 모델은 llm.MODEL).

    실제 LLM 호출은 profile.py 가 담당. 프롬프트 규칙(기획.md 10번):
    병명을 '설명'하지 말 것 / '위험·진단' 단어 금지 /
    focus_areas는 category(input|linked|compensatory)와 reason을 함께 생성.
    """
    if not injuries:
        raise HTTPException(status_code=422, detail="injuries가 비어 있어요.")
    try:
        profile = profile_svc.create_profile(injuries)
    except genai_errors.APIError as e:
        # Gemini 과부하(503)/rate limit(429) 등 -> 503으로 전달(프론트가 재시도 안내)
        code = getattr(e, "code", 503) or 503
        raise HTTPException(
            status_code=503 if code in {429, 500, 502, 503, 504} else 502,
            detail="관찰 프로필 생성 중 LLM 호출이 일시적으로 실패했어요. 잠시 후 다시 시도해주세요.",
        )

    try:
        db_repo.save_profile(profile)
    except Exception:
        logger.exception("프로필 저장 실패 (user_id=%s)", profile.user_id)

    return profile


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(profile: ObservationProfile, summary: FeatureSummary):
    """관찰 프로필 + 5~10초 특징 요약 -> 실시간 피드백 생성 (Gemini, feedback.py 담당).

    카메라 가드: 신뢰도 미달이면 LLM을 호출하지 않고 빈 피드백을 반환한다.
    확신형 표현("위험합니다","~하세요")은 feedback.py의 후처리 필터로 guardrail_passed 판정.
    """
    if summary.confidence.below_threshold:
        return FeedbackResponse(
            session_id=summary.session_id,
            window_end_s=summary.window.end_s,
            messages=[],
            guardrail_passed=True,
        )

    try:
        response = feedback_svc.create_feedback(profile, summary)
    except genai_errors.APIError as e:
        # Gemini 과부하(503)/rate limit(429) 등 -> 503으로 전달(프론트가 재시도 안내)
        code = getattr(e, "code", 503) or 503
        raise HTTPException(
            status_code=503 if code in {429, 500, 502, 503, 504} else 502,
            detail="피드백 생성 중 LLM 호출이 일시적으로 실패했어요. 잠시 후 다시 시도해주세요.",
        )

    try:
        db_repo.save_feedback(response)
    except Exception:
        logger.exception("피드백 저장 실패 (session_id=%s)", response.session_id)

    return response


# ── 세션 시작/종료 (schemas.py 계약 3종과 무관한 부가 API라 요청/응답 모델은 로컬에 정의) ──
class SessionStartRequest(BaseModel):
    user_id: str
    exercise: str


class SessionStartResponse(BaseModel):
    session_id: str
    started_at: str


class SessionEndResponse(BaseModel):
    session_id: str
    ended_at: str


@app.post("/session/start", response_model=SessionStartResponse)
def start_session(body: SessionStartRequest):
    """운동 세션 시작 기록. session_id는 서버가 발급해 이후 /feedback 등에서 참조한다.

    /profile, /feedback과 달리 이 엔드포인트는 '저장' 자체가 응답의 목적이므로
    (돌려줄 session_id/started_at이 저장 결과에서 나온다) 저장 실패를 삼키지 않고
    500으로 명확히 알린다 - 조용히 넘기면 프론트가 존재하지 않는 세션으로 이후
    요청을 계속 보내게 된다.
    """
    session_id = str(uuid.uuid4())
    try:
        db_repo.save_session_start(session_id, body.user_id, body.exercise)
        session = db_repo.get_session(session_id)
    except Exception:
        logger.exception("세션 시작 저장 실패 (user_id=%s)", body.user_id)
        raise HTTPException(status_code=500, detail="세션 시작 저장에 실패했어요.")

    return SessionStartResponse(session_id=session_id, started_at=session["started_at"])


@app.post("/session/end/{session_id}", response_model=SessionEndResponse)
def end_session(session_id: str):
    """운동 세션 종료 기록. 존재하지 않는 session_id면 404."""
    existing = db_repo.get_session(session_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 session_id예요.")

    try:
        db_repo.save_session_end(session_id)
        session = db_repo.get_session(session_id)
    except Exception:
        logger.exception("세션 종료 저장 실패 (session_id=%s)", session_id)
        raise HTTPException(status_code=500, detail="세션 종료 저장에 실패했어요.")

    return SessionEndResponse(session_id=session_id, ended_at=session["ended_at"])