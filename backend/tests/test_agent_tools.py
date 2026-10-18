from schemas import Confidence, FeatureSummary, FocusArea, ObservationProfile, Pattern, Window
from agent_tools import (
    allowed_evidence_keys,
    flatten_feature_keys,
    has_meaningful_signal,
    retrieve_exercise_guidance,
)


def _profile():
    return ObservationProfile(
        user_id="u_test",
        injuries=[],
        focus_areas=[FocusArea(area="오른쪽 발목", category="input", reason="테스트")],
        watch_patterns=[Pattern.LR_IMBALANCE, Pattern.LOAD_SHIFT],
    )


def _summary(features, below_threshold=False):
    return FeatureSummary(
        session_id="s_test",
        exercise="squat",
        window=Window(start_s=0.0, end_s=5.0, rep_count=3),
        features=features,
        confidence=Confidence(overall=0.9, below_threshold=below_threshold),
    )


def test_flatten_feature_keys_keeps_top_level_and_dotted_keys():
    keys = flatten_feature_keys({"lr_angle_diff": {"ankle": 11.2}, "load_shift": {"side_bias": "right"}})

    assert "lr_angle_diff" in keys
    assert "lr_angle_diff.ankle" in keys
    assert "load_shift" in keys
    assert "load_shift.side_bias" in keys


def test_has_meaningful_signal_skips_low_confidence():
    assert not has_meaningful_signal(_summary({"lr_angle_diff": {"ankle": 12}}, below_threshold=True))


def test_has_meaningful_signal_uses_numeric_feature_values():
    assert has_meaningful_signal(_summary({"lr_angle_diff": {"ankle": 12}}))
    assert not has_meaningful_signal(_summary({"lr_angle_diff": {"ankle": 1.5}}))


def test_retrieve_guidance_returns_grounding_docs():
    guidance = retrieve_exercise_guidance(_profile(), _summary({"lr_angle_diff": {"ankle": 12}}))

    assert guidance
    assert any(doc["id"] == "guidance:lr-imbalance" for doc in guidance)


def test_allowed_evidence_keys_includes_features_and_guidance_ids():
    summary = _summary({"lr_angle_diff": {"ankle": 12}})
    guidance = [{"id": "guidance:lr-imbalance", "title": "t", "text": "body"}]

    keys = allowed_evidence_keys(summary, guidance)

    assert "lr_angle_diff.ankle" in keys
    assert "guidance:lr-imbalance" in keys
