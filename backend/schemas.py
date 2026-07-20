"""데이터 계약 3종 - 단일 진실 공급원(single source of truth).

vision 출력 / backend / frontend 모두 이 스키마 형식을 따른다.
형식을 바꾸려면 이 파일을 고치고 체크포인트 전에 팀에 공유한다.

필드명은 영어(코드 안정성), 값/라벨의 한글 매핑은 프론트엔드에서 처리한다.
  예) Pattern.LR_IMBALANCE -> "좌우 불균형"
"""
from enum import Enum
from pydantic import BaseModel, Field


# ── 공통: 관찰 패턴 어휘 (계약 ②의 feature 키와 1:1로 매칭) ──────────────
class Pattern(str, Enum):
    LR_IMBALANCE = "lr_imbalance"      # 좌우 불균형
    INSTABILITY = "instability"       # 흔들림 증가
    LATE_FATIGUE = "late_fatigue"     # 운동 후반 안정성 감소
    ROM_ASYMMETRY = "rom_asymmetry"   # 좌우 가동범위 차이
    LOAD_SHIFT = "load_shift"         # 부위별 부하 쏠림


# ── 계약 ① 관찰 프로필 (온보딩 -> LLM 생성 -> DB 저장) ────────────────────
class InjuryInput(BaseModel):
    part: str                              # 부위 (예: "발목")
    side: str                              # "left" | "right" | "both"
    condition: str | None = None           # 추정 병명 (선택, 몰라도 됨)
    discomfort: int = Field(ge=1, le=5)    # 불편감 정도 1~5


class FocusArea(BaseModel):
    area: str        # 관찰 부위 (예: "오른쪽 발목")
    category: str    # "input"(입력) | "linked"(연결) | "compensatory"(보상)
    reason: str      # 한 줄 이유


class ObservationProfile(BaseModel):
    user_id: str
    injuries: list[InjuryInput]
    focus_areas: list[FocusArea]
    watch_patterns: list[Pattern]
    disclaimer: str = "의학적 진단이 아닌 사용자 입력 기반 참고 정보"


# ── 계약 ② 특징 요약 (vision/summarizer -> backend, 5~10초마다) ──────────
class Window(BaseModel):
    start_s: float
    end_s: float
    rep_count: int
    # 등척성(hold) 카테고리용 - 이 윈도우 동안 "허용 범위 안에서 자세를 유지한" 누적 초.
    # rep 카테고리는 항상 None(안 쓴다). plus_exercise.md 1단계에서 추가.
    hold_seconds: float | None = None


class Confidence(BaseModel):
    overall: float                 # 0~1 전체 인식 신뢰도
    interp_ratio: float = 0.0      # 보간(추정) 프레임 비율
    below_threshold: bool = False  # 카메라 가드: True면 LLM 호출 스킵


class FeatureSummary(BaseModel):
    session_id: str
    exercise: str
    window: Window
    # features는 개발 중 자유 형식(dict)으로 두고, 안정화되면 구체 모델로 교체.
    # 예: {"lr_angle_diff": {"knee": 12.3}, "instability": {"knee_L": 0.42}, ...}
    features: dict
    confidence: Confidence


# ── 계약 ③ 피드백 메시지 (backend/llm -> frontend) ───────────────────────
class FeedbackMessage(BaseModel):
    type: str                      # "observation"(관찰) | "suggestion"(제안)
    text: str
    area: str | None = None
    evidence: list[str] = []       # 근거가 된 feature 키들
    note_tag: str | None = None    # 제안(suggestion)에만: "참고 정보입니다"


class FeedbackResponse(BaseModel):
    session_id: str
    window_end_s: float
    messages: list[FeedbackMessage]
    guardrail_passed: bool = True  # 확신형 표현 후처리 통과 여부


# ── 계약 ④ 세션 리포트 요약 (backend/report -> frontend, 세션 종료 후 1회) ───
class ReportSummaryItem(BaseModel):
    text: str    # 정리된 관찰/제안 문구 (비슷한 것끼리 묶은 대표 문구)
    count: int   # 세션 중 몇 번 관찰됐는지


class ReportSummary(BaseModel):
    session_id: str
    summary: str                     # 세션 총평 (한두 문장)
    items: list[ReportSummaryItem]    # 빈도순 정리된 패턴 목록