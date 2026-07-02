"""세 점(A-B-C)으로 관절 각도(도)를 계산하는 범용 유틸.

특정 관절에 종속되지 않음 - 나중에 손목/어깨/목 등을 추가할 때는
JOINTS 딕셔너리에 항목만 추가하면 된다.
"""
import math

# 관절 이름 -> (landmark_idx_a, landmark_idx_b, landmark_idx_c)
# b가 각도의 꼭짓점.
JOINTS = {
    "L_knee": (23, 25, 27),
    "R_knee": (24, 26, 28),
    "L_ankle": (25, 27, 31),
    "R_ankle": (26, 28, 32),
    "L_hip": (11, 23, 25),
    "R_hip": (12, 24, 26),
}


def calculate_angle(a, b, c) -> float:
    """A-B-C 세 점(x, y)에서 B를 꼭짓점으로 하는 각도를 도(degree)로 반환."""
    v1 = (a[0] - b[0], a[1] - b[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    mag1 = math.hypot(*v1)
    mag2 = math.hypot(*v2)
    if mag1 == 0 or mag2 == 0:
        return 0.0
    cos_angle = (v1[0] * v2[0] + v1[1] * v2[1]) / (mag1 * mag2)
    cos_angle = max(-1.0, min(1.0, cos_angle))  # 부동소수점 오차로 인한 acos 도메인 오류 방지
    return math.degrees(math.acos(cos_angle))


def compute_joint_angles(landmarks) -> dict[str, float]:
    """landmarks[idx].x/.y 로 접근 가능한 시퀀스에 대해 JOINTS 전체 각도를 계산."""
    angles = {}
    for name, (ia, ib, ic) in JOINTS.items():
        a, b, c = landmarks[ia], landmarks[ib], landmarks[ic]
        angles[name] = calculate_angle((a.x, a.y), (b.x, b.y), (c.x, c.y))
    return angles
