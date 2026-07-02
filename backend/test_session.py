"""세션 시작/종료 엔드포인트 스모크 테스트.

기본 DB_PATH(data/app.db)를 그대로 사용해 실제 엔드포인트 코드 경로를 검증하고,
테스트가 끝나면 새로 생성된 DB 파일만 정리한다(원래 있던 파일은 건드리지 않는다).
"""
from fastapi.testclient import TestClient

from db.repository import DB_PATH, get_session
from main import app


def test_session_start_then_end_fills_timestamps():
    db_existed_before = DB_PATH.exists()
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
        if not db_existed_before and DB_PATH.exists():
            DB_PATH.unlink()
