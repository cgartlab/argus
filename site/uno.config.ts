import { defineConfig, presetUno, presetTypography } from 'unocss'

// Design tokens are defined as CSS custom properties in src/styles/global.css
// (:root for light, [data-theme="dark"] for dark). UnoCSS color utilities map
// to those variables — components never use bare color values.
export default defineConfig({
  presets: [
    presetUno(),
    presetTypography(),
  ],
  content: {
    filesystem: ['src/**/*.{astro,md,ts,html}'],
  },
  shortcuts: {
    'container-site': 'mx-auto max-w-6xl px-6',
    'btn-primary': 'inline-flex items-center gap-2 rounded-lg bg-accent text-fg-invert px-5 py-2.5 text-sm font-medium transition-colors hover:bg-accent-strong',
    'btn-secondary': 'inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-5 py-2.5 text-sm font-medium transition-colors hover:bg-surface-2',
    'card': 'rounded-xl border border-border bg-surface p-6',
  },
  theme: {
    colors: {
      // Mapped to CSS custom properties defined in global.css
      bg: 'var(--color-bg)',
      surface: 'var(--color-surface)',
      'surface-2': 'var(--color-surface-2)',
      fg: 'var(--color-fg)',
      'fg-muted': 'var(--color-fg-muted)',
      'fg-invert': 'var(--color-fg-invert)',
      border: 'var(--color-border)',
      accent: 'var(--color-accent)',
      'accent-strong': 'var(--color-accent-strong)',
      'accent-soft': 'var(--color-accent-soft)',
    },
  },
})