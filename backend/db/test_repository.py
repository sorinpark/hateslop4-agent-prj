"""repository.py 유닛 테스트 (표준 unittest, 실제 Postgres 사용).

SQLite 시절엔 테스트마다 임시 파일로 격리했지만, Postgres는 공유 DB라 그 방식이
안 통한다. 대신 테스트마다 고유 ID(uuid)를 써서 서로 안 겹치게 하고, 끝나면
addCleanup으로 만든 행을 지운다. DATABASE_URL(backend/.env)이 실제로 연결 가능한
Postgres를 가리키고 있어야 실행된다.

실행: cd backend && python -m unittest db.test_repository -v
"""
import sys
import unittest
import uuid
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from schemas import (  # noqa: E402
    Confidence,
    FeedbackMessage,
    FeedbackResponse,
    FeatureSummary,
    FocusArea,
    InjuryInput,
    ObservationProfile,
    Pattern,
    Window,
)

from db import repository  # noqa: E402


class RepositoryTestCase(unittest.TestCase):
    def setUp(self):
        self.conninfo = repository.DATABASE_URL
        if not self.conninfo:
            self.skipTest("DATABASE_URL이 설정되지 않아 Postgres 테스트를 건너뜀")
        repository.init_db(self.conninfo)

        suffix = uuid.uuid4().hex[:8]
        self.session_id = f"session-{suffix}"
        self.exercise = "squat"

        self.profile = ObservationProfile(
            user_id=f"user-{suffix}",
            injuries=[
                InjuryInput(part="발목", side="right", condition=None, discomfort=3),
            ],
            focus_areas=[
                FocusArea(area="오른쪽 발목", category="input", reason="입력된 부상 부위"),
            ],
            watch_patterns=[Pattern.LR_IMBALANCE, Pattern.LOAD_SHIFT],
        )

        self.feature_summary = FeatureSummary(
            session_id=self.session_id,
            exercise=self.exercise,
            window=Window(start_s=0.0, end_s=8.0, rep_count=3),
            features={"lr_angle_diff": {"knee": 12.3}, "instability": {"knee_L": 0.42}},
            confidence=Confidence(overall=0.91, interp_ratio=0.05, below_threshold=False),
        )

        self.feedback_response = FeedbackResponse(
            session_id=self.session_id,
            window_end_s=8.0,
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

        self.addCleanup(self._cleanup)

    def _cleanup(self):
        with repository._connect(self.conninfo) as conn:
            conn.execute(
                "DELETE FROM feedback_messages WHERE session_id = %s", (self.session_id,)
            )
            conn.execute(
                "DELETE FROM feature_windows WHERE session_id = %s", (self.session_id,)
            )
            conn.execute("DELETE FROM sessions WHERE session_id = %s", (self.session_id,))
            conn.execute("DELETE FROM profiles WHERE user_id = %s", (self.profile.user_id,))

    def test_save_and_get_sessions_by_date_range(self):
        repository.save_profile(self.profile, self.conninfo)
        repository.save_session_start(
            self.session_id, self.profile.user_id, self.exercise, self.conninfo
        )
        repository.save_session_end(self.session_id, self.conninfo)

        today = repository.get_sessions_by_date_range(
            self.profile.user_id, "2000-01-01", "2100-01-01", self.conninfo
        )
        self.assertEqual(len(today), 1)
        row = today[0]
        self.assertEqual(row["session_id"], self.session_id)
        self.assertEqual(row["user_id"], self.profile.user_id)
        self.assertEqual(row["exercise"], self.exercise)
        self.assertIsNotNone(row["started_at"])
        self.assertIsNotNone(row["ended_at"])

        none_found = repository.get_sessions_by_date_range(
            "no-such-user", "2000-01-01", "2100-01-01", self.conninfo
        )
        self.assertEqual(none_found, [])

    def test_save_feature_window_roundtrip(self):
        repository.save_session_start(
            self.session_id, self.profile.user_id, self.exercise, self.conninfo
        )
        repository.save_feature_window(self.feature_summary, self.conninfo)

        with repository._connect(self.conninfo) as conn:
            row = conn.execute(
                "SELECT * FROM feature_windows WHERE session_id = %s", (self.session_id,)
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row["rep_count"], self.feature_summary.window.rep_count)
        self.assertIsNone(row["hold_seconds"])
        self.assertEqual(row["confidence_overall"], self.feature_summary.confidence.overall)
        self.assertEqual(row["confidence_below_threshold"], 0)

        import json

        self.assertEqual(json.loads(row["features"]), self.feature_summary.features)

    def test_hold_mode_session_sums_hold_seconds_not_rep_count(self):
        """mode="hold" 카테고리(플랭크/브릿지 등)는 rep_count가 항상 0이고
        hold_seconds로 진행 상황을 잰다 - 이 값이 세션 목록 조회까지 이어지는지 확인."""
        repository.save_profile(self.profile, self.conninfo)
        repository.save_session_start(
            self.session_id, self.profile.user_id, "elbow-plank", self.conninfo
        )
        repository.save_session_end(self.session_id, self.conninfo)

        hold_window = FeatureSummary(
            session_id=self.session_id,
            exercise="elbow-plank",
            window=Window(start_s=0.0, end_s=5.0, rep_count=0, hold_seconds=4.2),
            features={},
            confidence=Confidence(overall=0.9, interp_ratio=0.0, below_threshold=False),
        )
        repository.save_feature_window(hold_window, self.conninfo)
        second_window = hold_window.model_copy(
            update={"window": Window(start_s=5.0, end_s=10.0, rep_count=0, hold_seconds=3.1)}
        )
        repository.save_feature_window(second_window, self.conninfo)

        sessions = repository.get_sessions_by_date_range(
            self.profile.user_id, "2000-01-01", "2100-01-01", self.conninfo
        )
        row = next(s for s in sessions if s["session_id"] == self.session_id)
        self.assertEqual(row["rep_count"], 0)
        self.assertAlmostEqual(row["hold_seconds"], 7.3)

    def test_save_and_get_feedback_by_session(self):
        repository.save_session_start(
            self.session_id, self.profile.user_id, self.exercise, self.conninfo
        )
        repository.save_feedback(self.feedback_response, self.conninfo)

        messages = repository.get_feedback_by_session(self.session_id, self.conninfo)

        self.assertEqual(len(messages), len(self.feedback_response.messages))
        for expected, actual in zip(self.feedback_response.messages, messages):
            self.assertEqual(actual.type, expected.type)
            self.assertEqual(actual.area, expected.area)
            self.assertEqual(actual.text, expected.text)
            self.assertEqual(actual.evidence, expected.evidence)
            self.assertEqual(actual.note_tag, expected.note_tag)

        no_messages = repository.get_feedback_by_session("no-such-session", self.conninfo)
        self.assertEqual(no_messages, [])

    def test_save_profile_upsert_overwrites(self):
        repository.save_profile(self.profile, self.conninfo)
        updated = self.profile.model_copy(
            update={"watch_patterns": [Pattern.INSTABILITY]}
        )
        repository.save_profile(updated, self.conninfo)

        with repository._connect(self.conninfo) as conn:
            rows = conn.execute(
                "SELECT * FROM profiles WHERE user_id = %s", (self.profile.user_id,)
            ).fetchall()

        self.assertEqual(len(rows), 1)

        import json

        self.assertEqual(json.loads(rows[0]["watch_patterns"]), ["instability"])


if __name__ == "__main__":
    unittest.main()
