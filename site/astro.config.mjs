import { defineConfig } from 'astro/config'
import UnoCSS from 'unocss/astro'
import sitemap from '@astrojs/sitemap'
import icon from 'astro-icon'

// https://astro.build/config
export default defineConfig({
  site: 'https://argus.cgartlab.com',
  base: '/',
  output: 'static',
  trailingSlash: 'never',
  prefetch: true,
  integrations: [
    UnoCSS(),
    sitemap(),
    icon(),
  ],
})