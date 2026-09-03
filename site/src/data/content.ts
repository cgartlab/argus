// Landing page display data. All copy is English (project language).

export interface Capability {
  title: string
  desc: string
  icon: string // lucide icon name (rendered via astro-icon)
}

export const capabilities: Capability[] = [
  {
    title: 'Design Token Audit',
    desc: 'Detects bare oklch(), hex, and rgb() colors outside :root declarations and flags every component rule that should reference a var(--ds-*) token.',
    icon: 'palette',
  },
  {
    title: 'Hardcoded Value Detection',
    desc: 'Catches magic numbers in spacing, radii, and type scale — any numeric value that should be a design token but is not.',
    icon: 'ruler',
  },
  {
    title: 'Accessibility Review',
    desc: 'Enforces the WCAG AA baseline: aria-label on icon buttons, alt text on images, visible focus indicators, and contrast-safe colors.',
    icon: 'accessibility',
  },
  {
    title: 'Dark Mode Coverage',
    desc: 'Verifies every color token declared in :root has a [data-theme="dark"] override so themes never silently break.',
    icon: 'moon-star',
  },
  {
    title: 'CSS Consistency',
    desc: 'Checks for duplicate rules, invalid BEM selectors, and empty catch blocks that erode long-term maintainability.',
    icon: 'shield-check',
  },
  {
    title: 'HTML Structure Validation',
    desc: 'Confirms semantic elements are used correctly — buttons for actions, links for navigation, no misuse of interactive elements.',
    icon: 'layout',
  },
  {
    title: 'Framework API Usage',
    desc: 'Stack-aware validation against official docs for React, Vue, Angular, Svelte, and Astro — hooks, directives, lifecycles, and anti-patterns.',
    icon: 'layers',
  },
]

export interface QuickStartStep {
  title: string
  desc: string
  code?: string
}

export const quickstartSteps: QuickStartStep[] = [
  {
    title: 'Install the App',
    desc: 'Install argus-flash from the GitHub Marketplace and grant it access to the repositories you want reviewed.',
    code: 'github.com/apps/argus-flash',
  },
  {
    title: 'Add Secrets',
    desc: 'Store your GitHub App ID and private key in your repository Actions secrets.',
    code: 'secrets.YOUR_APP_ID',
  },
  {
    title: 'Create a Workflow',
    desc: 'Add a minimal review workflow that calls the argus-review composite action. Every PR gets a design review comment.',
    code: 'cgartlab/argus/.github/actions/argus-review@main',
  },
]

export interface ArchitectureNode {
  id: string
  label: string
  desc: string
}

export const architectureNodes: ArchitectureNode[] = [
  {
    id: 'app',
    label: 'argus-flash App',
    desc: 'github.com/apps/argus-flash',
  },
  {
    id: 'workflow',
    label: 'Workflow',
    desc: 'review.yml in your repository',
  },
  {
    id: 'action',
    label: 'Composite Action',
    desc: 'cgartlab/argus/.github/actions/argus-review@main',
  },
  {
    id: 'rules',
    label: 'Rules',
    desc: 'AGENTS.md + SKILL.md injected at runtime',
  },
  {
    id: 'result',
    label: 'Review Result',
    desc: 'PR comment from argus-flash[bot]',
  },
]