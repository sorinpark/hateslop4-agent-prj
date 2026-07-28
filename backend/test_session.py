"""세션 시작/종료 엔드포인트 스모크 테스트.

실제 DATABASE_URL(Postgres)에 그대로 붙어서 엔드포인트 코드 경로를 검증한다.
공유 DB라 테스트가 끝나면 이번에 만든 세션 행만 지워서 정리한다.
"""
from fastapi.testclient import TestClient

from db.repository import _connect, get_session
from main import app


def test_session_start_then_end_fills_timestamps():
    session_id = None
    try:
        with TestClient(app) as client:
            start_resp = client.post(
                "/session/start", json={"user_id": "u1", "exercise": "squat"}
            )
            assert start_resp.status_code == 200
            start_body = start_resp.json()
            session_id = start_body["session_id"]
            assert start_body["started_at"]

            end_resp = client.post(f"/session/end/{session_id}")
            assert end_resp.status_code == 200
            end_body = end_resp.json()
            assert end_body["session_id"] == session_id
            assert end_body["ended_at"]

            saved = get_session(session_id)
            assert saved is not None
            assert saved["started_at"] == start_body["started_at"]
            assert saved["ended_at"] == end_body["ended_at"]

            missing_resp = client.post("/session/end/does-not-exist")
            assert missing_resp.status_code == 404
    finally:
        if session_id is not None:
            with _connect() as conn:
                conn.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
