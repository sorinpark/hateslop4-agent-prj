import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { ProfileProvider } from './state/ProfileContext.jsx'
import { SessionProvider } from './state/SessionContext.jsx'
import { ExerciseProvider } from './state/ExerciseContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ProfileProvider>
        <SessionProvider>
          <ExerciseProvider>
            <App />
          </ExerciseProvider>
        </SessionProvider>
      </ProfileProvider>
    </BrowserRouter>
  </StrictMode>,
)
