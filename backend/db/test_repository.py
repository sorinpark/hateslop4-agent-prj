"""repository.py 유닛 테스트 (표준 unittest, 임시 SQLite 파일 사용).

_connect()는 호출마다 새 커넥션을 여는 구조라 ":memory:"는 호출 사이에 데이터가
사라진다. 그래서 여기서는 스펙이 허용한 두 옵션 중 임시 파일 쪽을 쓴다.

실행: cd backend && python -m unittest db.test_repository -v
"""
import sys
import tempfile
import unittest
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
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = Path(tmp.name)
        self.addCleanup(lambda: self.db_path.unlink(missing_ok=True))
        repository.init_db(self.db_path)

        self.profile = ObservationProfile(
            user_id="user-1",
            injuries=[
                InjuryInput(part="발목", side="right", condition=None, discomfort=3),
            ],
            focus_areas=[
                FocusArea(area="오른쪽 발목", category="input", reason="입력된 부상 부위"),
            ],
            watch_patterns=[Pattern.LR_IMBALANCE, Pattern.LOAD_SHIFT],
        )

        self.session_id = "session-1"
        self.exercise = "squat"

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

    def test_save_and_get_sessions_by_date_range(self):
        repository.save_profile(self.profile, self.db_path)
        repository.save_session_start(
            self.session_id, self.profile.user_id, self.exercise, self.db_path
        )
        repository.save_session_end(self.session_id, self.db_path)

        today = repository.get_sessions_by_date_range(
            self.profile.user_id, "2000-01-01", "2100-01-01", self.db_path
        )
        self.assertEqual(len(today), 1)
        row = today[0]
        self.assertEqual(row["session_id"], self.session_id)
        self.assertEqual(row["user_id"], self.profile.user_id)
        self.assertEqual(row["exercise"], self.exercise)
        self.assertIsNotNone(row["started_at"])
        self.assertIsNotNone(row["ended_at"])

        none_found = repository.get_sessions_by_date_range(
            "no-such-user", "2000-01-01", "2100-01-01", self.db_path
        )
        self.assertEqual(none_found, [])

    def test_save_feature_window_roundtrip(self):
        repository.save_session_start(
            self.session_id, self.profile.user_id, self.exercise, self.db_path
        )
        repository.save_feature_window(self.feature_summary, self.db_path)

        with repository._connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM feature_windows WHERE session_id = ?", (self.session_id,)
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row["rep_count"], self.feature_summary.window.rep_count)
        self.assertEqual(row["confidence_overall"], self.feature_summary.confidence.overall)
        self.assertEqual(row["confidence_below_threshold"], 0)

        import json

        self.assertEqual(json.loads(row["features"]), self.feature_summary.features)

    def test_save_and_get_feedback_by_session(self):
        repository.save_session_start(
            self.session_id, self.profile.user_id, self.exercise, self.db_path
        )
        repository.save_feedback(self.feedback_response, self.db_path)

        messages = repository.get_feedback_by_session(self.session_id, self.db_path)

        self.assertEqual(len(messages), len(self.feedback_response.messages))
        for expected, actual in zip(self.feedback_response.messages, messages):
            self.assertEqual(actual.type, expected.type)
            self.assertEqual(actual.area, expected.area)
            self.assertEqual(actual.text, expected.text)
            self.assertEqual(actual.evidence, expected.evidence)
            self.assertEqual(actual.note_tag, expected.note_tag)

        no_messages = repository.get_feedback_by_session("no-such-session", self.db_path)
        self.assertEqual(no_messages, [])

    def test_save_profile_upsert_overwrites(self):
        repository.save_profile(self.profile, self.db_path)
        updated = self.profile.model_copy(
            update={"watch_patterns": [Pattern.INSTABILITY]}
        )
        repository.save_profile(updated, self.db_path)

        with repository._connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM profiles WHERE user_id = ?", (self.profile.user_id,)
            ).fetchall()

        self.assertEqual(len(rows), 1)

        import json

        self.assertEqual(json.loads(rows[0]["watch_patterns"]), ["instability"])


if __name__ == "__main__":
    unittest.main()
