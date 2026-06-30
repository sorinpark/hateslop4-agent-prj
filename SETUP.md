# 프로젝트 세팅 (Windows / PowerShell 기준)

현재 폴더 구조:
```
hateslop4-final-proj/
├── frontend/      (React)
├── backend/       (FastAPI + 비전: MediaPipe·특징추출 = 파이썬 네이티브)
├── data/          (SQLite db / pose_landmarker.task 모델 / 데모 데이터)
├── .gitignore
└── *.md
```
> 비전(MediaPipe) 코드는 파이썬이라 `backend/` 안에 `vision/` 하위 폴더로 두면 됩니다.
> (A안: 실시간 웹캠 루프를 파이썬이 직접 돌림)

---

## 1. backend 세팅

`schemas.py`, `main.py`, `requirements.txt`, `.env.example`를 **backend/ 폴더에** 넣은 뒤:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> 만약 `Activate.ps1` 실행이 막히면(보안 정책), 이 창에서만 허용:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env      # 그 뒤 .env 열어서 GEMINI_API_KEY 채우기
uvicorn main:app --reload
```

띄워지면 브라우저에서 http://127.0.0.1:8000/docs 열기 → `/profile`, `/feedback`을
바로 테스트할 수 있습니다(지금은 목 데이터 반환).

> 파이썬은 3.11 권장 (mediapipe 휠 호환). `python --version`으로 확인.

---

## 2. frontend 세팅

```powershell
cd ..\frontend
npm create vite@latest . -- --template react
npm install
npm run dev
```

> `npm create vite@latest .` 는 현재 폴더에 생성합니다. 폴더가 비어있지 않다는
> 경고가 나오면 "Ignore files and continue" 선택.
> 띄워지면 http://localhost:5173 (백엔드 CORS가 이 포트로 열려 있음).

---

## 3. data 폴더

- MediaPipe 스쿼트용 모델 `pose_landmarker.task`를 다운로드해 여기 둡니다
  (ai.google.dev Pose Landmarker 문서의 Models 섹션).
- 이후 SQLite db 파일, 데모 시나리오 데이터도 여기.
- `.gitignore`에 `*.task`, `*.db`가 들어있는지 확인(무거운 파일/DB 커밋 방지).

---

## 4. git 첫 커밋

```powershell
cd ..
git add .
git commit -m "chore: 프로젝트 스캐폴딩 (backend 스켈레톤 + 데이터 계약)"
git push
```

팀원 모두 `git clone` 후 위 1·2번까지 실행