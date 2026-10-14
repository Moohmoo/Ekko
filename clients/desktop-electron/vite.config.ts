import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import electron from 'vite-plugin-electron/simple';

export default defineConfig(({ mode }) => {
  const isProd = mode === 'production';

  return {
    esbuild: {
      drop: isProd ? ['console', 'debugger'] : [],
    },
    build: {
      sourcemap: !isProd,
    },
    plugins: [
      react(),
      electron({
        main: {
          entry: 'electron/main.ts',
        },
        preload: {
          input: 'electron/preload.ts',
          vite: {
            build: {
              sourcemap: !isProd,
              rollupOptions: {
                output: {
                  entryFileNames: 'preload.cjs',
                },
              },
            },
          },
        },
      }),
    ],
    server: {
      port: 5173,
    },
  };
});
