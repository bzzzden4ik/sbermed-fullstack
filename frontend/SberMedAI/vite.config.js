import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import path from 'path';
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  server: {
    host: "127.0.0.1",
    port: 5173
  },
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
})
