import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Fonts are bundled and served from our own server (no Google Fonts requests).
import '@fontsource/inter/300.css'
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import '@fontsource/instrument-serif/400.css'
import '@fontsource/instrument-serif/400-italic.css'
import './app/styles/reset.css'
import './app/styles/index.css'
import App from './app/App.jsx'


createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
