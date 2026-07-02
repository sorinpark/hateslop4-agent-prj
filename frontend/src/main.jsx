import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { ProfileProvider } from './state/ProfileContext.jsx'
import { SessionProvider } from './state/SessionContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ProfileProvider>
        <SessionProvider>
          <App />
        </SessionProvider>
      </ProfileProvider>
    </BrowserRouter>
  </StrictMode>,
)
