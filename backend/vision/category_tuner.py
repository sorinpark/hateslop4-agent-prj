"""카테고리 임계값 튜닝 도구 (plus_exercise.md 2단계용).

spike_webcam.py(스쿼트 전용 스파이크, 세션/프로필/피드백 API까지 호출하는
원래 목적의 스크립트)는 그대로 두고, 이건 카테고리 개발자가 "이 운동은 어떤
관절을 얼마나 굽혔다 펴야 rep으로 볼지"를 빠르게 반복 확인하기 위한 별도 도구다.
백엔드 서버(uvicorn)나 프론트엔드, LLM 호출 없이 이 스크립트 하나로 끝난다.

사용법 (backend/vision 디렉토리에서):
    python category_tuner.py <운동 슬러그>
    예: python category_tuner.py push-ups
    슬러그를 생략하면 기본값 squats.

화면에 표시되는 것:
  - 이 카테고리가 실제로 보는 관절들(초록 점=인식 잘 됨 / 빨강 점=인식 불량)
  - rep 판정에 쓰는 관절의 실시간 평균 각도 + 지금 상태(up/down) + 지금까지 rep 수
    (mode="hold"인 카테고리는 각도 대신 hold_min/max 범위 안인지를 보여준다)
  - 카테고리 파일(categories/<이름>.py)에 적힌 임계값

기록: 실행 중 매 프레임의 시각/각도/상태를 tuning_logs/<슬러그>_<시각>.csv 로
저장한다. 화면 숫자를 눈으로 보는 것 외에, 나중에 이 CSV를 열어서(엑셀/파이썬)
각도가 실제로 어떻게 분포하는지 그래프로 보거나, AI에게 "이 각도 흐름을 보고
적절한 임계값을 추천해줘"라고 물어볼 때 근거 데이터로 쓸 수 있다.

튜닝 흐름:
  1. categories/<카테고리>.py 를 열어 임계값을 대충 추정치로 채운다.
  2. 이 스크립트를 그 슬러그로 실행하고, 실제로 운동하면서 화면의 각도 숫자를 본다
     - 동작의 "가장 굽혀진 지점"/"가장 편 지점"에서 각도가 얼마나 나오는지 몇 번
       반복해서 확인한다. CSV 로그도 남으니 나중에 다시 봐도 된다.
  3. categories/<카테고리>.py의 숫자를 그 값에 맞게 수정한다(파일 저장 후
     스크립트 재실행 - 코드 재시작이 빨라서 반복하기 편하다).
  4. rep count가 실제로 한 것과 맞게 세이는지, state(up/down)가 움직이는
     타이밍과 맞게 바뀌는지 확인될 때까지 2~3회 반복.

q: 종료
"""
import csv
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from angles import JOINTS as ALL_JOINTS, compute_joint_angles
from categories import get_category
from feature_extractor import REP_VIS_THRESHOLD, WindowAccumulator

DEFAULT_EXERCISE = "squats"

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
MODEL_PATH = Path(__file__).parent.parent / "data" / "pose_landmarker.task"
LOG_DIR = Path(__file__).parent / "tuning_logs"

VIS_THRESHOLD = 0.6
GREEN = (0, 255, 0)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)
CYAN = (255, 255, 0)

# JOINTS의 3점(A,B,C) 중 각도의 꼭짓점(B)만 화면 표시용으로 쓴다.
_LANDMARK_OF_JOINT = {name: idxs[1] for name, idxs in ALL_JOINTS.items()}


def download_model():
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"모델 다운로드 중... ({MODEL_URL})")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("다운로드 완료.")


_latest_result = {"landmarks": None}


def _result_callback(result, output_image, timestamp_ms):
    _latest_result["landmarks"] = result.pose_landmarks[0] if result.pose_landmarks else None


def main():
    exercise = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EXERCISE
    category = get_category(exercise)
    print(f"운동: {exercise} -> 카테고리: {category.name} (mode={category.mode})")

    tracked_pair = category.hold_joint_pair if category.mode == "hold" else category.rep_joint_pair
    if tracked_pair is None:
        print("경고: 이 카테고리는 rep_joint_pair/hold_joint_pair가 아직 없어서 각도를 못 보여줍니다.")

    # 이 카테고리가 실제로 쓰는 관절만 화면에 표시(설정이 맞는지 눈으로 확인용)
    watch_bases = set(category.lr_diff_joints) | set(category.stability_joints)
    watch_joints = {f"{side}_{base}" for base in watch_bases for side in ("L", "R")}
    if tracked_pair:
        watch_joints |= set(tracked_pair)

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

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{exercise}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    log_file = open(log_path, "w", newline="", encoding="utf-8")
    log_writer = csv.writer(log_file)
    log_writer.writerow(["t_s", "angle_deg", "left_deg", "right_deg", "rep_state_or_in_range", "total_reps_or_hold_s", "vis"])
    print(f"각도 로그 저장 위치: {log_path}")

    accumulator = WindowAccumulator(window_seconds=5.0, exercise=exercise)
    total_reps = 0
    total_hold_s = 0.0
    start_time = time.time()

    try:
        with mp_vision.PoseLandmarker.create_from_options(options) as landmarker:
            timestamp = 0
            print("q: 종료")

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

                if landmarks:
                    for name in watch_joints:
                        idx = _LANDMARK_OF_JOINT[name]
                        lm = landmarks[idx]
                        vis = lm.visibility if lm.visibility is not None else 0.0
                        color = GREEN if vis >= VIS_THRESHOLD else RED
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        cv2.circle(frame, (cx, cy), 8, color, -1)
                        cv2.putText(frame, name, (cx + 10, cy),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

                    live_angles = compute_joint_angles(landmarks)
                    now_s = time.time() - start_time

                    # 이 프레임을 먼저 반영해야 아래 표시되는 state/vis가 지금 이 프레임
                    # 기준이 된다(기존엔 add_frame을 맨 뒤에서 불러서 한 프레임 밀려 보였음).
                    accumulator.add_frame(landmarks, now_s)
                    vis = accumulator.last_vis

                    y = 30
                    cv2.putText(frame, f"exercise={exercise} category={category.name}",
                                (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, CYAN, 2)
                    y += 28

                    if tracked_pair:
                        left_v = live_angles[tracked_pair[0]]
                        right_v = live_angles[tracked_pair[1]]
                        avg = (left_v + right_v) / 2

                        if category.mode == "hold":
                            in_range = (
                                category.hold_min_deg is not None
                                and category.hold_max_deg is not None
                                and category.hold_min_deg <= avg <= category.hold_max_deg
                            )
                            status = "IN-RANGE" if in_range else "OUT"
                            cv2.putText(
                                frame,
                                f"angle={avg:5.1f}deg  range=[{category.hold_min_deg},{category.hold_max_deg}]  {status}",
                                (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, YELLOW, 2,
                            )
                            log_writer.writerow([f"{now_s:.2f}", f"{avg:.2f}", f"{left_v:.2f}", f"{right_v:.2f}", status, f"{total_hold_s:.2f}", f"{vis:.3f}"])
                        else:
                            cv2.putText(
                                frame,
                                f"angle={avg:5.1f}deg L={left_v:5.1f} R={right_v:5.1f}  down<{category.rep_down_threshold_deg} "
                                f"up>{category.rep_up_threshold_deg}  state={accumulator.rep_state}",
                                (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, YELLOW, 2,
                            )
                            log_writer.writerow([f"{now_s:.2f}", f"{avg:.2f}", f"{left_v:.2f}", f"{right_v:.2f}", accumulator.rep_state, total_reps, f"{vis:.3f}"])
                        y += 28
                        vis_color = GREEN if vis >= REP_VIS_THRESHOLD else RED
                        cv2.putText(
                            frame,
                            f"vis(confidence gate)={vis:.2f}  (REP_VIS_THRESHOLD={REP_VIS_THRESHOLD})",
                            (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, vis_color, 2,
                        )
                        y += 28

                    cv2.putText(
                        frame,
                        f"total reps: {total_reps}   total hold: {total_hold_s:.1f}s",
                        (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, YELLOW, 2,
                    )

                    summary = accumulator.get_summary_if_ready("tuner_session", exercise)
                    if summary is not None:
                        total_reps += summary.window.rep_count
                        if summary.window.hold_seconds:
                            total_hold_s += summary.window.hold_seconds
                else:
                    cv2.putText(frame, "No person detected", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

                cv2.imshow(f"Category tuner: {exercise}", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        log_file.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
