"""Gemini(LLM) 연동 - 연결 확인용 최소 모듈.

이 프로젝트의 LLM은 Gemini 2.5-flash-lite (기획.md / team_plan.md 결정).
SDK: google-genai (requirements.txt에 포함). 사용법:
    from google import genai
    client = genai.Client(api_key=...)
    resp = client.models.generate_content(model=..., contents=...)
    resp.text

지금 단계 목표는 "키/의존성/네트워크가 실제로 동작하는지" 1회 호출로 확인하는 것.
관찰 프로필 생성(profile.py) / 실시간 피드백 프롬프트는 이 모듈이 검증된 뒤에 얹는다.

직접 실행:  (backend 폴더에서)  python llm.py
"""
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors

# .env는 backend/(이 파일과 같은 폴더)에 둔다. 실행 위치와 무관하게 항상 그 파일을
# 읽도록 이 파일 기준으로 경로를 잡는다. 프로젝트 루트에 .env를 두는 경우도 있을 수
# 있어 backend/.env가 없으면 상위 폴더(루트)의 .env로 폴백한다.
_BACKEND_ENV = Path(__file__).resolve().parent / ".env"
_ROOT_ENV = Path(__file__).resolve().parents[1] / ".env"
ROOT_ENV = _BACKEND_ENV if _BACKEND_ENV.exists() else _ROOT_ENV
load_dotenv(ROOT_ENV)

# 기획/계획상 모델은 gemini-2.5-flash-lite 였으나, 무료 티어에서 flash-lite는
# 분당 요청 한도(RPM)가 빡빡해 429가 자주 발생함(연속 호출 시 거의 전부 429).
# gemini-2.5-flash는 같은 키로 훨씬 안정적이라 데모 안정성(기획 6번) 위해 채택.
# 한도 여유가 생기거나 유료 키로 바꾸면 flash-lite로 되돌려도 됨.
MODEL = "gemini-2.5-flash"

# 재시도 대상 HTTP 코드: 429(rate limit), 5xx(일시적 과부하/장애)
_RETRYABLE = {429, 500, 502, 503, 504}


# 클라이언트는 한 번만 만들어 재사용한다(싱글톤). 매 호출마다 새로 만들면
# 이전 Client가 GC되며 내부 httpx 커넥션이 닫혀 "client has been closed" 에러가 난다.
_client: genai.Client | None = None


def get_client() -> genai.Client:
    """환경변수 GEMINI_API_KEY로 만든 Gemini 클라이언트(싱글톤)를 반환.

    키가 없으면 명확한 메시지로 막는다(빈 키로 호출하면 모호한 에러가 남).
    """
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY가 비어 있습니다. 프로젝트 루트의 .env에 키를 채워주세요. "
                "(발급: https://aistudio.google.com/apikey)"
            )
        _client = genai.Client(api_key=api_key)
    return _client


def generate(*, contents, config=None, model: str = MODEL, max_retries: int = 3):
    """generate_content 호출 + 일시적 에러(429/5xx) 지수 백오프 재시도.

    Gemini는 'high demand' 503을 종종 내므로, 데모 안정성(기획 6번)을 위해
    LLM 호출은 전부 이 함수를 통해 한다. 재시도해도 안 되면 마지막 에러를 올린다.
    """
    client = get_client()
    delay = 1.0
    last_exc = None
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=model, contents=contents, config=config
            )
        except errors.APIError as e:  # ServerError/ClientError 공통 부모
            code = getattr(e, "code", None)
            if code in _RETRYABLE and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2  # 1s -> 2s -> 4s
                last_exc = e
                continue
            raise
    raise last_exc  # 도달 불가지만 방어


def ping(prompt: str = "한 단어로만 답해줘: 연결 확인되면 'OK'") -> str:
    """Gemini 호출 1회. 응답 텍스트를 반환한다(연결 확인용)."""
    resp = generate(contents=prompt)
    return (resp.text or "").strip()


if __name__ == "__main__":
    # Windows 콘솔(cp949)에서도 한글/기호가 깨지지 않도록 출력 인코딩을 UTF-8로.
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - 재설정 불가 환경이면 그냥 진행
        pass

    # 직접 실행 시: 키 확인 -> 1회 호출 -> 결과 출력
    try:
        print(f"[llm] 모델: {MODEL}")
        answer = ping()
        print(f"[llm] 응답: {answer!r}")
        print("[llm] Gemini 연결 성공")
    except Exception as e:  # noqa: BLE001 - 연결 확인 단계라 모든 예외를 사용자에게 보여줌
        print(f"[llm] 실패: {type(e).__name__}: {e}")
        raise SystemExit(1)
