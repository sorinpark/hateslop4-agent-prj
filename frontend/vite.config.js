import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

// 백엔드 주소(프록시 대상). 기본은 로컬 백엔드.
const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

// 폰 실기기 테스트용: 환경변수 HTTPS=1 로 실행하면 self-signed HTTPS + LAN 노출.
//   npm run dev                          -> http://localhost:5173 (PC 개발)
//   (Windows) set HTTPS=1 && npm run dev -> https + 0.0.0.0, 폰에서 접속 가능
// 폰 브라우저는 HTTPS/localhost에서만 웹캠을 허용하므로 폰 카메라 테스트엔 HTTPS 필요.
//
// API/WebSocket은 dev 서버가 백엔드로 프록시한다. 그래서 프론트는 절대 URL 대신
// 상대경로(/profile, /ws/exercise ...)로 호출하면 되고(=VITE_API_BASE_URL 빈 값),
// 폰이 https://<PC-IP>:5173 하나로 접속해도 mixed-content(https->http) 문제가 없다.
// https://vite.dev/config/
const useHttps = process.env.HTTPS === '1'

// 백엔드로 넘길 경로들 (REST + WebSocket)
const proxyPaths = ['/health', '/profile', '/feedback', '/session', '/sessions', '/ws']
const proxy = Object.fromEntries(
  proxyPaths.map((p) => [
    p,
    { target: BACKEND, changeOrigin: true, ws: p === '/ws' },
  ]),
)

export default defineConfig({
  plugins: [react(), ...(useHttps ? [basicSsl()] : [])],
  server: {
    ...(useHttps ? { host: true } : {}),
    // cloudflared/ngrok 등 터널 도메인(trycloudflare.com 등)에서의 접속 허용.
    // dev 전용이라 모든 호스트 허용(true). 폰 실기기 테스트에 필요.
    allowedHosts: true,
    proxy,
  },
})
