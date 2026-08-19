import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    host: '0.0.0.0', // Слушаем все интерфейсы внутри контейнера
    port: 5173,
    strictPort: true,
    // Разрешаем Vite принимать любые заголовочные Host от Nginx
    allowedHosts: true, 
    hmr: {
      clientPort: 80, // Говорим клиенту, что HMR идет через 80-й порт (Nginx)
    },
  },

})
