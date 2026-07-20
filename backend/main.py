"""FastAPI 진입점 - 1주차 '끝까지 연결' 단계용 스켈레톤.

지금은 /profile, /feedback이 목(mock) 데이터를 돌려준다.
실제 LLM 연동은 profile.py / llm.py를 만들어 TODO 자리에 연결한다.

실행:  uvicorn main:app --reload
문서:  http://127.0.0.1:8000/docs  (자동 생성되는 API 테스트 페이지)
"""
import json
import logging
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google.genai import errors as genai_errors
from pydantic import BaseModel, ValidationError

from schemas import (
    InjuryInput,
    ObservationProfile,
    FeatureSummary,
    FeedbackMessage,
    FeedbackResponse,
    ReportSummary,
)
import profile as profile_svc
import feedback as feedback_svc
import report as report_svc
from db import repository as db_repo

# vision/ 은 패키지가 아니라 (angles.py 등을 bare import 하는) 스크립트 모음이라,
# feature_extractor.py 를 그대로 가져오려면 vision/ 자체를 sys.path에 넣어야 한다.
sys.path.insert(0, str(Path(__file__).resolve().parent / "vision"))
from feature_extractor import WindowAccumulator  # noqa: E402
# 개발용 진단(_tuning_info)에서 현재 각도/임계값을 계산하는 데 쓴다.
from angles import compute_joint_angles  # noqa: E402
from categories import get_category  # noqa: E402

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
def create_profile(injuries: list[InjuryInput], user_id: str = "u_demo"):
    """온보딩 입력 -> 관찰 프로필 생성 (Gemini, 모델은 llm.MODEL).

    실제 LLM 호출은 profile.py 가 담당. 프롬프트 규칙(기획.md 10번):
    병명을 '설명'하지 말 것 / '위험·진단' 단어 금지 /
    focus_areas는 category(input|linked|compensatory)와 reason을 함께 생성.
    """
    if not injuries:
        raise HTTPException(status_code=422, detail="injuries가 비어 있어요.")
    try:
        profile = profile_svc.create_profile(injuries, user_id=user_id)
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
        db_repo.save_feature_window(summary)
    except Exception:
        logger.exception("특징 윈도우 저장 실패 (session_id=%s)", summary.session_id)

    try:
        db_repo.save_feedback(response)
    except Exception:
        logger.exception("피드백 저장 실패 (session_id=%s)", response.session_id)

    return response


@app.get("/profile/{user_id}", response_model=ObservationProfile)
def get_profile(user_id: str):
    """온보딩에서 생성된 관찰 프로필 조회. 저장된 적 없으면 404."""
    profile = db_repo.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 user_id예요.")
    return profile


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


class SessionInfo(BaseModel):
    session_id: str
    user_id: str
    exercise: str
    date: str
    started_at: str
    ended_at: str | None
    duration_s: float | None
    rep_count: int


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


@app.get("/sessions", response_model=list[SessionInfo])
def list_sessions(user_id: str, start_date: str, end_date: str):
    """캘린더 마커용: user_id의 [start_date, end_date](YYYY-MM-DD, 양끝 포함) 세션 목록."""
    return db_repo.get_sessions_by_date_range(user_id, start_date, end_date)


@app.get("/sessions/{session_id}/feedback", response_model=list[FeedbackMessage])
def get_session_feedback(session_id: str):
    """날짜별 상세 화면용: 존재하지 않는 session_id면 404, 있으면 피드백 메시지 시간순 반환."""
    if db_repo.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 session_id예요.")
    return db_repo.get_feedback_by_session(session_id)


@app.get("/sessions/{session_id}/report", response_model=ReportSummary)
def get_session_report(session_id: str):
    """세션 리포트 화면용: 세션의 피드백 메시지를 LLM 1회 호출로 총평 + 빈도 정리.

    존재하지 않는 session_id면 404. 메시지가 없으면 LLM을 호출하지 않고
    빈 리포트를 바로 돌려준다(불필요한 호출/쿼터 절약).
    """
    if db_repo.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 session_id예요.")

    messages = db_repo.get_feedback_by_session(session_id)
    if not messages:
        return ReportSummary(
            session_id=session_id,
            summary="이번 세션에서는 특별히 관찰된 패턴이 없었어요.",
            items=[],
        )

    try:
        return report_svc.create_report_summary(session_id, messages)
    except genai_errors.APIError as e:
        # Gemini 과부하(503)/rate limit(429) 등 -> 503으로 전달(프론트가 재시도 안내)
        code = getattr(e, "code", 503) or 503
        raise HTTPException(
            status_code=503 if code in {429, 500, 502, 503, 504} else 502,
            detail="리포트 요약 생성 중 LLM 호출이 일시적으로 실패했어요. 잠시 후 다시 시도해주세요.",
        )


# ── 실시간 운동 WebSocket ──────────────────────────────────────────────
# session_id -> {"accumulator": WindowAccumulator, "exercise": str}
_ws_sessions: dict[str, dict] = {}

EXPECTED_LANDMARK_COUNT = 33


def _to_landmark_objects(raw_list: list[dict]) -> list:
    """클라이언트가 보낸 랜드마크 dict 리스트를
    angles.py/feature_extractor.py가 기대하는 인덱스 접근(landmarks[idx]) +
    속성 접근(.x/.y/.z/.visibility) 가능한 객체 리스트로 변환한다."""
    return [
        SimpleNamespace(
            x=lm.get("x", 0.0),
            y=lm.get("y", 0.0),
            z=lm.get("z", 0.0),
            visibility=lm.get("visibility", 0.0),
        )
        for lm in raw_list
    ]


async def _handle_init(websocket: WebSocket, state: dict, data: dict) -> None:
    try:
        profile = ObservationProfile(**data.get("profile", {}))
    except ValidationError:
        await websocket.send_json({"error": "invalid profile"})
        return
    state["profile"] = profile
    await websocket.send_json({"ack": True, "profile_loaded": True})


def _tuning_info(state: dict, landmarks) -> dict:
    """폰에서 임계값을 튜닝할 수 있도록, 매 프레임의 판정 근거를 만들어 준다.

    category_tuner.py(PC 웹캠 전용)가 화면에 띄우는 것과 같은 정보를 앱으로도
    보기 위한 개발용 진단 데이터다. 실측 튜닝이 끝나면 이 함수와 호출부,
    프론트 오버레이를 같이 제거하면 된다(plus_exercise.md 2단계).

    hold 모드면 지금 각도가 허용 범위 안(IN-RANGE)인지, rep 모드면 down/up 중
    어느 상태인지를 실시간으로 알려준다.
    """
    category = get_category(state["exercise"])
    angles = compute_joint_angles(landmarks)

    pair = category.hold_joint_pair if category.mode == "hold" else category.rep_joint_pair
    if not pair:
        return {}

    values = [angles[j] for j in pair if j in angles]
    if not values:
        return {}
    angle = sum(values) / len(values)

    info = {
        "category": category.name,
        "mode": category.mode,
        # 좌우 평균 각도(판정에 실제로 쓰이는 값)
        "angle": round(angle, 1),
        # 어떤 관절을 보고 있는지 ("L_trunk" -> "trunk")
        "joint": pair[0][2:],
    }
    if category.mode == "hold":
        info["min"] = category.hold_min_deg
        info["max"] = category.hold_max_deg
        info["in_range"] = category.hold_min_deg <= angle <= category.hold_max_deg
    else:
        info["down"] = category.rep_down_threshold_deg
        info["up"] = category.rep_up_threshold_deg
    return info


async def _handle_frame(websocket: WebSocket, session_id: str, state: dict, data: dict) -> None:
    raw_landmarks = data.get("landmarks")
    if not isinstance(raw_landmarks, list) or len(raw_landmarks) != EXPECTED_LANDMARK_COUNT:
        await websocket.send_json({"ack": True})
        return

    landmarks = _to_landmark_objects(raw_landmarks)
    state["accumulator"].add_frame(landmarks, data["timestamp_s"])

    # 개발용: 매 프레임 판정 근거(각도/상태)를 함께 보내 폰에서 튜닝할 수 있게 한다.
    try:
        tuning = _tuning_info(state, landmarks)
    except Exception:
        tuning = {}

    summary = state["accumulator"].get_summary_if_ready(session_id, state["exercise"])
    if summary is None:
        await websocket.send_json({"ack": True, "tuning": tuning})
        return

    print(json.dumps(summary.model_dump(), indent=2, ensure_ascii=False))

    try:
        db_repo.save_feature_window(summary)
    except Exception:
        logger.exception("특징 윈도우 저장 실패 (session_id=%s)", session_id)

    profile = state.get("profile")
    if profile is None:
        await websocket.send_json({"error": "profile not loaded yet"})
        return

    if summary.confidence.below_threshold:
        response = FeedbackResponse(
            session_id=summary.session_id,
            window_end_s=summary.window.end_s,
            messages=[],
            guardrail_passed=True,
        )
    else:
        try:
            response = feedback_svc.create_feedback(profile, summary)
        except genai_errors.APIError:
            await websocket.send_json({"error": "llm_temporarily_unavailable"})
            return

    try:
        db_repo.save_feedback(response)
    except Exception:
        logger.exception("피드백 저장 실패 (session_id=%s)", response.session_id)

    await websocket.send_json({
        "window_ready": True,
        "messages": [m.model_dump() for m in response.messages],
        "guardrail_passed": response.guardrail_passed,
        "rep_count": summary.window.rep_count,
        # 개발용 진단(폰 튜닝): 이 윈도우의 유지 시간까지 함께 보낸다.
        "hold_seconds": summary.window.hold_seconds,
        "tuning": tuning,
    })


@app.websocket("/ws/exercise")
async def ws_exercise(websocket: WebSocket, session_id: str, exercise: str = "squat"):
    await websocket.accept()
    print(f"[ws] 연결됨 session_id={session_id}", flush=True)
    _ws_sessions[session_id] = {
        "accumulator": WindowAccumulator(window_seconds=5.0, exercise=exercise),
        "exercise": exercise,
        "profile": None,
    }

    try:
        while True:
            data = await websocket.receive_json()
            state = _ws_sessions[session_id]
            msg_type = data.get("type")

            if msg_type == "init":
                await _handle_init(websocket, state, data)
            elif msg_type == "frame":
                await _handle_frame(websocket, session_id, state, data)
            else:
                await websocket.send_json({"ack": True})
    except WebSocketDisconnect:
        print(f"[ws] 연결 종료 session_id={session_id}", flush=True)
    finally:
        _ws_sessions.pop(session_id, None)