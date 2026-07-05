"""SQLite 저장/조회 함수.

schemas.py의 Pydantic 모델(ObservationProfile, FeatureSummary, FeedbackResponse)을
그대로 저장하고 복원한다. "위험/진단" 관련 판단은 이 레이어의 책임이 아니다 -
측정값/텍스트를 그대로 저장하고 돌려줄 뿐이다.
"""
import json
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from schemas import (  # noqa: E402
    FeatureSummary,
    FeedbackMessage,
    FeedbackResponse,
    ObservationProfile,
)

from db.models import ALL_TABLES  # noqa: E402

DB_PATH = _BACKEND_DIR / "data" / "app.db"


@contextmanager
def _connect(db_path: str | Path = DB_PATH):
    if db_path == ":memory:":
        conn = sqlite3.connect(":memory:")
    else:
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str | Path = DB_PATH) -> None:
    """앱 시작 시 1회 호출: 테이블이 없으면 생성한다."""
    with _connect(db_path) as conn:
        for ddl in ALL_TABLES:
            conn.execute(ddl)


def save_profile(profile: ObservationProfile, db_path: str | Path = DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO profiles (user_id, injuries, focus_areas, watch_patterns, disclaimer, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                injuries = excluded.injuries,
                focus_areas = excluded.focus_areas,
                watch_patterns = excluded.watch_patterns,
                disclaimer = excluded.disclaimer
            """,
            (
                profile.user_id,
                json.dumps([i.model_dump() for i in profile.injuries], ensure_ascii=False),
                json.dumps([f.model_dump() for f in profile.focus_areas], ensure_ascii=False),
                json.dumps([p.value for p in profile.watch_patterns], ensure_ascii=False),
                profile.disclaimer,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def get_profile(user_id: str, db_path: str | Path = DB_PATH) -> ObservationProfile | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT user_id, injuries, focus_areas, watch_patterns, disclaimer
            FROM profiles
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    return ObservationProfile(
        user_id=row["user_id"],
        injuries=json.loads(row["injuries"]),
        focus_areas=json.loads(row["focus_areas"]),
        watch_patterns=json.loads(row["watch_patterns"]),
        disclaimer=row["disclaimer"],
    )


def save_session_start(
    session_id: str, user_id: str, exercise: str, db_path: str | Path = DB_PATH
) -> None:
    started_at = datetime.now(timezone.utc).isoformat()
    date = started_at[:10]
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO sessions (session_id, user_id, exercise, date, started_at, ended_at)
            VALUES (?, ?, ?, ?, ?, NULL)
            """,
            (session_id, user_id, exercise, date, started_at),
        )


def save_session_end(session_id: str, db_path: str | Path = DB_PATH) -> None:
    ended_at = datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE sessions SET ended_at = ? WHERE session_id = ?",
            (ended_at, session_id),
        )


def get_session(session_id: str, db_path: str | Path = DB_PATH) -> dict | None:
    """세션 시작/종료 엔드포인트용: session_id 존재 여부 확인 및 타임스탬프 조회."""
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT session_id, user_id, exercise, date, started_at, ended_at
            FROM sessions
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def save_feature_window(summary: FeatureSummary, db_path: str | Path = DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO feature_windows
                (session_id, window_start_s, window_end_s, rep_count, features,
                 confidence_overall, confidence_below_threshold)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary.session_id,
                summary.window.start_s,
                summary.window.end_s,
                summary.window.rep_count,
                json.dumps(summary.features, ensure_ascii=False),
                summary.confidence.overall,
                int(summary.confidence.below_threshold),
            ),
        )


def save_feedback(response: FeedbackResponse, db_path: str | Path = DB_PATH) -> None:
    if not response.messages:
        return
    with _connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO feedback_messages
                (session_id, window_end_s, type, area, text, evidence, note_tag, guardrail_passed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    response.session_id,
                    response.window_end_s,
                    m.type,
                    m.area,
                    m.text,
                    json.dumps(m.evidence, ensure_ascii=False),
                    m.note_tag,
                    int(response.guardrail_passed),
                )
                for m in response.messages
            ],
        )


def get_sessions_by_date_range(
    user_id: str, start_date: str, end_date: str, db_path: str | Path = DB_PATH
) -> list[dict]:
    """캘린더 마커용: [start_date, end_date] 범위(YYYY-MM-DD, 양끝 포함)의 세션 목록."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                sessions.session_id,
                sessions.user_id,
                sessions.exercise,
                sessions.date,
                sessions.started_at,
                sessions.ended_at,
                COALESCE(SUM(feature_windows.rep_count), 0) AS rep_count
            FROM sessions
            LEFT JOIN feature_windows
                ON sessions.session_id = feature_windows.session_id
            WHERE sessions.user_id = ? AND sessions.date BETWEEN ? AND ?
            GROUP BY sessions.session_id
            ORDER BY sessions.date, sessions.started_at
            """,
            (user_id, start_date, end_date),
        ).fetchall()

    sessions = [dict(row) for row in rows]
    for session in sessions:
        if session["ended_at"] is not None:
            started = datetime.fromisoformat(session["started_at"])
            ended = datetime.fromisoformat(session["ended_at"])
            session["duration_s"] = (ended - started).total_seconds()
        else:
            session["duration_s"] = None
    return sessions


def get_feedback_by_session(
    session_id: str, db_path: str | Path = DB_PATH
) -> list[FeedbackMessage]:
    """날짜별 상세 화면용: 세션에 쌓인 피드백 메시지를 시간순으로 복원."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT type, area, text, evidence, note_tag
            FROM feedback_messages
            WHERE session_id = ?
            ORDER BY id
            """,
            (session_id,),
        ).fetchall()
    return [
        FeedbackMessage(
            type=row["type"],
            area=row["area"],
            text=row["text"],
            evidence=json.loads(row["evidence"]),
            note_tag=row["note_tag"],
        )
        for row in rows
    ]
