import { readFileSync } from 'node:fs';
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// Per-home settings live in ../config.json (start from config.example.json).
let config = {};
try {
  config = JSON.parse(readFileSync(new URL('../config.json', import.meta.url), 'utf8'));
} catch {}
const guideUrls = config.guide_urls ?? [];

export default defineConfig({
  plugins: [svelte()],
  define: { __GUIDE_URLS__: JSON.stringify(guideUrls) },
  server: {
    host: true,
    // In dev, relay /api to the server that the guide comes from.
    proxy: guideUrls[0] ? { '/api': new URL(guideUrls[0]).origin } : undefined,
  },
});
