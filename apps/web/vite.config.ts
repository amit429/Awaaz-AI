import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Awaaz',
        short_name: 'Awaaz',
        description: 'Phone calls for people who can’t hear or speak',
        theme_color: '#0F1115',
        background_color: '#0F1115',
        display: 'standalone',
        start_url: '/',
        icons: [],
      },
    }),
  ],
  server: { port: 5173 },
  test: { environment: 'node' },
});
