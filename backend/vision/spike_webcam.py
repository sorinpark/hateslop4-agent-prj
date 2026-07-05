"""
MediaPipe 포즈 인식 스파이크 - 스쿼트 관절 가시성 확인 + 특징 추출
관심 관절: hip(23,24), knee(25,26), ankle(27,28)
초록 원 = visibility >= 0.6 (잘 인식됨)
빨간 원 = visibility < 0.6 (인식 불량)
5초마다 콘솔에 schemas.FeatureSummary 형식 JSON을 출력한다.
"""

import json
import sys
import time
import urllib.request
from pathlib import Path
import cv2
import mediapipe as mp
import requests
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import numpy as np

from feature_extractor import WindowAccumulator

API_BASE_URL = "http://127.0.0.1:8000"
SESSION_ID = "spike_session"
USER_ID = "u1"
EXERCISE = "squat"

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
MODEL_PATH = Path(__file__).parent.parent / "data" / "pose_landmarker.task"

# 관심 관절 인덱스
JOINTS = {
    "L_hip": 23, "R_hip": 24,
    "L_knee": 25, "R_knee": 26,
    "L_ankle": 27, "R_ankle": 28,
}
VIS_THRESHOLD = 0.6
GREEN = (0, 255, 0)
RED   = (0, 0, 255)


def start_session():
    try:
        resp = requests.post(
            f"{API_BASE_URL}/session/start",
            json={"user_id": USER_ID, "exercise": EXERCISE},
            timeout=3,
        )
        resp.raise_for_status()
        return resp.json()["session_id"]
    except requests.exceptions.RequestException as e:
        print(f"경고: 세션 시작 API 호출 실패 ({e}). 하드코딩된 세션 ID로 진행합니다.")
        return SESSION_ID


def end_session(session_id):
    try:
        resp = requests.post(f"{API_BASE_URL}/session/end/{session_id}", timeout=3)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"경고: 세션 종료 API 호출 실패 ({e}).")


def create_profile():
    injuries = [{"part": "무릎", "side": "right", "discomfort": 3}]
    try:
        resp = requests.post(f"{API_BASE_URL}/profile", json=injuries, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"경고: 프로필 생성 API 호출 실패 ({e}). 이후 피드백 호출은 건너뜁니다.")
        return None


def request_feedback(profile_data, summary):
    try:
        resp = requests.post(
            f"{API_BASE_URL}/feedback",
            json={"profile": profile_data, "summary": summary.model_dump()},
            timeout=3,
        )
        resp.raise_for_status()
        for msg in resp.json().get("messages", []):
            print(f"[피드백] {msg['text']}")
    except requests.exceptions.RequestException as e:
        print(f"경고: 피드백 API 호출 실패 ({e}).")


def download_model():
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"모델 다운로드 중... ({MODEL_URL})")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("다운로드 완료.")


# 콜백에서 결과를 메인 루프로 전달하기 위한 공유 상태
_latest_result = {"landmarks": None}

def _result_callback(result, output_image, timestamp_ms):
    if result.pose_landmarks:
        _latest_result["landmarks"] = result.pose_landmarks[0]
    else:
        _latest_result["landmarks"] = None


def main():
    session_id = start_session()
    profile_data = create_profile()

    if not MODEL_PATH.exists():
        download_model()

    # Windows에서 경로에 한글(비-ASCII) 문자가 있으면 MediaPipe C++ 로더가
    # 모델 파일을 못 여는 알려진 문제가 있어, 경로 대신 바이트로 읽어 전달한다.
    model_bytes = MODEL_PATH.read_bytes()
    base_options = mp_python.BaseOptions(model_asset_buffer=model_bytes)
    options = mp_vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.LIVE_STREAM,
        result_callback=_result_callback,
        num_poses=1,
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        sys.exit("웹캠을 열 수 없습니다. 카메라 연결/권한을 확인하세요.")

    accumulator = WindowAccumulator(window_seconds=5.0)
    start_time = time.time()

    with mp_vision.PoseLandmarker.create_from_options(options) as landmarker:
        timestamp = 0
        print("스페이스바: 없음 / q: 종료")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            landmarker.detect_async(mp_image, timestamp)
            timestamp += 1

            h, w = frame.shape[:2]
            landmarks = _latest_result["landmarks"]
            vis_values = []

            if landmarks:
                for name, idx in JOINTS.items():
                    lm = landmarks[idx]
                    vis = lm.visibility if lm.visibility is not None else 0.0
                    vis_values.append(vis)
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    color = GREEN if vis >= VIS_THRESHOLD else RED
                    cv2.circle(frame, (cx, cy), 8, color, -1)
                    cv2.putText(frame, f"{name[:2]}{idx}", (cx + 10, cy),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

                avg_vis = float(np.mean(vis_values))
                print(f"\r평균 visibility: {avg_vis:.2f}  ", end="", flush=True)
                cv2.putText(frame, f"avg vis: {avg_vis:.2f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

                accumulator.add_frame(landmarks, time.time() - start_time)
                summary = accumulator.get_summary_if_ready(session_id, EXERCISE)
                if summary is not None:
                    print("\n" + json.dumps(summary.model_dump(), indent=2, ensure_ascii=False))
                    if profile_data is not None:
                        request_feedback(profile_data, summary)
            else:
                print("\r사람 미감지          ", end="", flush=True)
                cv2.putText(frame, "No person detected", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

            cv2.imshow("Squat Joint Spike", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()
    end_session(session_id)
    print()


if __name__ == "__main__":
    main()
