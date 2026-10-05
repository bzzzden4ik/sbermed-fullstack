import { useEffect } from 'react'
import AppRouter from './router/app-router.jsx'
import { SessionProvider, useSession } from '@/entities/session'
import { ToastProvider } from '@/shared/ui/toast.jsx'
import { hideSplash } from './splash.js'


/** Removes the SIRIUS splash once the app has rendered and the sign-in check is finished. */
function SplashGate() {
  const { isLoading } = useSession()
  useEffect(() => {
    if (!isLoading) hideSplash()
  }, [isLoading])
  return null
}

function App() {
  return (
    <ToastProvider>
      <SessionProvider>
        <AppRouter />
        <SplashGate />
      </SessionProvider>
    </ToastProvider>
  )
}

export default App
