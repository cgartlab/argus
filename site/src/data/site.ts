export const site = {
  name: 'Argus',
  title: 'Argus — Frontend Design Code Review Agent',
  description:
    'Cross-platform AI coding agent specialized in frontend design review: hardcoded values, design tokens, a11y, dark mode, framework API misuse.',
  version: '0.3.2', // synced with argus repo VERSION
  url: 'https://argus.cgartlab.com',
  github: 'https://github.com/cgartlab/argus',
  appUrl: 'https://github.com/apps/argus-flash',
  docsPrefix: '/docs',
  license: 'MIT',
  creator: 'CGArtLab',
  creatorUrl: 'https://github.com/cgartlab',
  nav: [
    { label: 'Features', href: '/#capabilities' },
    { label: 'Docs', href: '/docs' },
    { label: 'GitHub', href: 'https://github.com/cgartlab/argus' },
  ],
} as const

export type SiteMeta = typeof site