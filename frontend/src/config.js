// VITE_API_BASE가 설정되어 있으면 그걸 그대로 backend 주소로 쓴다.
// (cloudflared로 frontend/backend를 각각 다른 주소로 터널링할 때 필요 — 같은 호스트:8000 가정이 깨지기 때문)
// 설정 안 하면 기존 방식대로 접속한 host의 8000번 포트를 그대로 가리킨다 (localhost, 같은 네트워크 IP 등).
const explicitApiBase = import.meta.env.VITE_API_BASE

export const API_BASE = explicitApiBase || `http://${window.location.hostname}:8000`
export const WS_BASE = explicitApiBase
  ? explicitApiBase.replace(/^http/, 'ws')
  : `ws://${window.location.hostname}:8000`
