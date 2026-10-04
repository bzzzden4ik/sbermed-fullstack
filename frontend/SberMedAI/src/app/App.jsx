import AppRouter from './router/app-router.jsx'
import { SessionProvider } from '@/entities/session'
import { ToastProvider } from '@/shared/ui/toast.jsx'


function App() {
  return (
    <ToastProvider>
      <SessionProvider>
        <AppRouter />
      </SessionProvider>
    </ToastProvider>
  )
}

export default App
