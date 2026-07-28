"""Postgres 스키마 정의(DDL).

실제 테이블 생성은 repository.init_db()가 담당한다.
injuries/focus_areas/watch_patterns/evidence/features는 JSON 문자열(TEXT)로 저장한다.
session_id는 sessions.session_id를 참조한다(FOREIGN KEY로 명시).
"""

CREATE_PROFILES_TABLE = """
CREATE TABLE IF NOT EXISTS profiles (
    user_id TEXT PRIMARY KEY,
    injuries TEXT NOT NULL,
    focus_areas TEXT NOT NULL,
    watch_patterns TEXT NOT NULL,
    disclaimer TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    exercise TEXT NOT NULL,
    date TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT
)
"""

CREATE_FEEDBACK_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS feedback_messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id TEXT NOT NULL,
    window_end_s REAL NOT NULL,
    type TEXT NOT NULL,
    area TEXT,
    text TEXT NOT NULL,
    evidence TEXT NOT NULL,
    note_tag TEXT,
    guardrail_passed INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
)
"""

CREATE_FEATURE_WINDOWS_TABLE = """
CREATE TABLE IF NOT EXISTS feature_windows (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id TEXT NOT NULL,
    window_start_s REAL NOT NULL,
    window_end_s REAL NOT NULL,
    rep_count INTEGER NOT NULL,
    hold_seconds REAL,
    features TEXT NOT NULL,
    confidence_overall REAL NOT NULL,
    confidence_below_threshold INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
)
"""

ALL_TABLES = [
    CREATE_PROFILES_TABLE,
    CREATE_SESSIONS_TABLE,
    CREATE_FEEDBACK_MESSAGES_TABLE,
    CREATE_FEATURE_WINDOWS_TABLE,
]
