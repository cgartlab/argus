---
name: argus-design-review
description: "Use when reviewing frontend code for design quality — checking design token usage, hardcoded values, dark mode coverage, accessibility compliance, CSS consistency, semantic HTML, or framework API usage. Use when auditing a component, page, or design system for issues. Trigger phrases: '帮我 review 这段代码'、'检查一下这个组件的设计问题'、'看看有没有 hardcoded values'、'dark mode 有没有遗漏'、'无障碍有没有问题'、'帮我做个 design audit'、'让 Argus-Flash 审一下'"
version: 0.3.2
---

# Argus Design Review Skill

When this skill is active, every line of frontend code is audited against the same standards: design tokens used correctly, no hardcoded values, dark mode fully covered, accessibility baseline met, correct API usage per technology stack, and **copy-ready code fixes** provided for every issue.

## Technology Stack Detection

Before reviewing, detect the project's technology stack:

| Indicator | Stack | Documentation |
|-----------|-------|---------------|
| `*.tsx`, `*.jsx` + `react` in package.json | React | https://react.dev, https://reactjs.org/docs |
| `*.vue` | Vue | https://vuejs.org/guide |
| `*.svelte` | Svelte | https://svelte.dev/docs |
| `angular.json` | Angular | https://angular.dev/api |
| `*.astro` | Astro | https://docs.astro.build |
| `lit-*.js` / `*.ts` with lit imports | Lit | https://lit.dev/docs |
| CSS/SCSS files only | Vanilla CSS | https://developer.mozilla.org/docs/Web/CSS |

**Detection workflow:**
1. Check file extensions of files to review
2. Read `package.json` to confirm framework and version
3. Check for config files (vite.config.js, tsconfig.json, etc.)
4. Map stack to official documentation base URL

## Review Dimensions

### 1. Design Tokens

**Rule:** Every color in component rules must be a `var(--ds-*)` reference. No bare `oklch()`, `#hex`, or `rgb()`.

```css
/* WRONG — bare oklch in component rule */
.ds-card {
  background: oklch(99% 0.005 80);
  color: oklch(20% 0.02 60);
}

/* RIGHT — token reference */
.ds-card {
  background: var(--ds-color-surface);
  color: var(--ds-color-fg);
}
```

**Exception:** Token declarations in `:root` and `@keyframes` may use bare oklch/hex.

**Flag:** Any occurrence of bare color value in component rules (CSS or inline `style=`).

### 2. Hardcoded Values

**Rule:** All spacing, radii, and type scale values must use design token scale. No magic numbers.

```css
/* WRONG */
padding: 16px;
border-radius: 8px;

/* RIGHT */
padding: var(--ds-space-4);
border-radius: var(--ds-radius-lg);
```

**Flag:** Any numeric value (not 0) that should be a design token but isn't.

### 3. Dark Mode Coverage

**Rule:** Every color token declared in `:root` must have a `[data-theme="dark"]` override.

```css
/* WRONG — no dark override */
:root {
  --ds-color-bg: oklch(97% 0.012 80);
}

/* RIGHT — override exists */
[data-theme="dark"] {
  --ds-color-bg: oklch(15% 0.008 75);
}
```

**Flag:** Any `:root` color token without a `[data-theme="dark"]` override. This is a silent dark mode break — colors may become unreadable.

### 4. Accessibility

**Rule:** WCAG AA baseline. Mandatory, never demoted to warning.

| Pattern | Requirement |
|---|---|
| Icon-only `<button>` | `aria-label` present |
| `<img>` | `alt` attribute present |
| `<a>` without href | Not used as a button; use `<button>` |
| Focusable elements | Visible focus indicator |
| Color contrast | 4.5:1 for normal text, 3:1 for large text |

**Flag:** Any violation is P1 minimum.

### 5. CSS Quality

- No duplicate rules in same selector block
- No empty `catch {}` blocks
- Valid BEM (no dangling modifiers like `.parent a--active`)
- No invalid HTML `id` duplicates

### 6. HTML Structure

- No `<a>` tags without `href` used as interactive elements
- Semantic elements used correctly (`<button>` for actions, `<a>` for links)

### 7. Framework API Usage (Stack-Aware)

**Rule:** Use framework APIs correctly per official documentation. See **Framework Anti-Patterns Library** below for specific patterns per framework.

**React:**
- Check hooks usage: `useState`, `useEffect`, `useCallback`, `useMemo` deps arrays
- Verify `useEffect` cleanup functions present when needed
- Check deprecated API usage (e.g., `React.createClass`, `UNSAFE_` lifecycles)
- Validate `forwardRef`, `memo` usage patterns
- Reference: https://react.dev/reference

```tsx
/* WRONG — missing deps array */
useEffect(() => {
  fetchData(id);
}, []);

/* RIGHT — deps array matches */
useEffect(() => {
  fetchData(id);
}, [id]);
```

**Vue:**
- Check Composition API vs Options API consistency
- Verify `ref` vs `reactive` usage
- Check `watch` vs `watchEffect` proper usage
- Validate lifecycle hook names (`onMounted`, not `mounted`)
- Reference: https://vuejs.org/guide/essentials

**Angular:**
- Check reactive forms vs template-driven forms
- Verify dependency injection patterns
- Check lifecycle hooks (`ngOnInit`, `ngOnDestroy`)
- Validate RxJS subscription cleanup
- Reference: https://angular.dev/guide

**Svelte:**
- Check `$:` reactivity declarations
- Verify store subscriptions (`$store`)
- Check `onMount` cleanup
- Reference: https://svelte.dev/docs

**Astro:**
- Check component directives (`client:*`)
- Verify props typing with `Props` interface
- Check `.astro` vs `.jsx` component boundaries
- Reference: https://docs.astro.build

**General JavaScript/TypeScript:**
- Check `async/await` error handling
- Verify TypeScript type annotations
- Check null/undefined handling
- Reference: https://www.typescriptlang.org/docs/, https://developer.mozilla.org/docs/Web/JavaScript

## Framework Anti-Patterns Library

Comprehensive pattern catalog for each framework with detection rules, examples, and fixes.

### React Anti-Patterns

#### 1. Missing useEffect Dependencies (P1)
**Detection:** `useEffect(` followed by variable without it in deps array
**Reference:** https://react.dev/reference/react/useEffect#specifying-reactive-dependencies

```tsx
// WRONG
useEffect(() => {
  setFullName(`${firstName} ${lastName}`);
}, []); // Missing: firstName, lastName

// RIGHT
useEffect(() => {
  setFullName(`${firstName} ${lastName}`);
}, [firstName, lastName]);
```

#### 2. Async useEffect Without IIFE (P1)
**Detection:** `useEffect(` with `async` keyword before arrow function
**Reference:** https://react.dev/reference/react/useEffect#fetching-data-with-effects

```tsx
// WRONG — useEffect cannot return a promise
useEffect(async () => {
  const data = await fetchUser(id);
  setUser(data);
}, [id]);

// RIGHT — use IIFE or separate function
useEffect(() => {
  const fetchUser = async () => {
    const data = await fetch(`/api/users/${id}`);
    setUser(data);
  };
  fetchUser();
}, [id]);
```

#### 3. Inline Object/Array in JSX (P2)
**Detection:** JSX attribute with inline `{}` object or `[]` array
**Reference:** https://react.dev/learn/keeping-components-pure

```tsx
// WRONG — new object on every render
<div style={{ color: 'red' }} />
<div onClick={{ handle: () => {} }} />

// RIGHT — move outside component or use useMemo
const buttonStyle = { color: 'red' };
<div style={buttonStyle} />
```

#### 4. Missing Key in List (P1)
**Detection:** `.map()` without `key` prop on returned element
**Reference:** https://react.dev/learn/rendering-lists#keeping-list-items-in-order-with-key

```tsx
// WRONG — missing key
users.map(user => <UserCard name={user.name} />)

// RIGHT — use stable unique id
users.map(user => <UserCard key={user.id} name={user.name} />)
```

#### 5. Stale Closure in Callbacks (P1)
**Detection:** Function referencing state/props without proper dependency
**Reference:** https://react.dev/learn/avoiding-re-renders

```tsx
// WRONG — count is stale
const handleClick = () => {
  setCount(count + 1); // May use stale value
};

// RIGHT — use functional update
const handleClick = () => {
  setCount(prev => prev + 1);
};
```

#### 6. Unnecessary Re-renders (P2)
**Detection:** Component passing new object/function as prop without memoization
**Reference:** https://react.dev/reference/react/memo

```tsx
// WRONG — new function every render
const Parent = () => {
  return <Child onClick={() => console.log(clicked)} />;
};

// RIGHT — memoize callback
const Parent = () => {
  const handleClick = useCallback(() => {
    console.log(clicked);
  }, [clicked]);
  return <Child onClick={handleClick} />;
};
```

#### 7. Missing Cleanup in useEffect (P1)
**Detection:** Event listener or subscription without return cleanup
**Reference:** https://react.dev/reference/react/useEffect#subscribing-to-events

```tsx
// WRONG — memory leak
useEffect(() => {
  window.addEventListener('resize', handleResize);
}, []); // Missing cleanup

// RIGHT — cleanup function
useEffect(() => {
  window.addEventListener('resize', handleResize);
  return () => window.removeEventListener('resize', handleResize);
}, []);
```

#### 8. Boolean State for Toggle (P3)
**Detection:** State initialized with `true`/`false` when null/undefined is valid
**Reference:** https://react.dev/reference/react/useState

```tsx
// WRONG — three states needed
const [isLoading, setIsLoading] = useState(true);
if (isLoading === true) // loading
else if (isLoading === false) // loaded
// But how to handle error?

// RIGHT — use proper state machine
const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
```

#### 9. Derived State Instead of Computed (P2)
**Detection:** `useState` storing value that can be computed from props/state
**Reference:** https://react.dev/learn/queueing-a-series-of-state-updates

```tsx
// WRONG — redundant state
const [fullName, setFullName] = useState('');
useEffect(() => {
  setFullName(`${firstName} ${lastName}`);
}, [firstName, lastName]);

// RIGHT — compute when needed
const fullName = `${firstName} ${lastName}`;
```

#### 10. Prop Drilling (P2)
**Detection:** Multiple components passing same prop through layers
**Reference:** https://react.dev/learn/passing-data-deeply-with-context

```tsx
// WRONG — theme passed through layers
<GrandParent>
  <Parent theme={theme}>
    <Child theme={theme}>
      <Button theme={theme} />
    </Child>
  </Parent>
</GrandParent>

// RIGHT — use context
const ThemeContext = createContext();
<ThemeContext.Provider value={theme}>
  <Child />
</ThemeContext.Provider>
// Then useContext(ThemeContext) in Button
```

---

### Vue Anti-Patterns

#### 1. Mutating Props Directly (P1)
**Detection:** `props:` definition with mutation inside component
**Reference:** https://vuejs.org/guide/components/props#prop-mutations

```vue
// WRONG — mutating prop
<script setup>
const props = defineProps<{ title: string }>();
props.title = 'New Title'; // Error!
</script>

// RIGHT — emit event or use local state
<script setup>
const props = defineProps<{ title: string }>();
const localTitle = ref(props.title);
localTitle.value = 'New Title';
</script>
```

#### 2. Mixing Composition API with Options API (P2)
**Detection:** `setup()` function alongside `data()`, `methods`, `computed`
**Reference:** https://vuejs.org/guide/extras/composition-api-faq#should-i-use-options-api-or-composition-api

```vue
// WRONG — mixing APIs
<script>
export default {
  data() { return { count: 0 } },
  setup() {
    const doubled = computed(() => this.count * 2); // Confusing
  }
}
</script>

// RIGHT — stick to Composition API
<script setup>
const count = ref(0);
const doubled = computed(() => count.value * 2);
</script>
```

#### 3. Watching Objects Instead of Properties (P2)
**Detection:** `watch(obj, ...)` instead of `watch(() => obj.prop, ...)`
**Reference:** https://vuejs.org/guide/essentials/watchers#watching-reactive-state

```vue
// WRONG — watches entire object
watch(user, (newUser) => {
  console.log(newUser.name); // Won't trigger on name change
});

// RIGHT — watch specific property
watch(() => user.name, (newName) => {
  console.log(newName);
});
```

#### 4. Not Using reactive for Objects (P2)
**Detection:** Using `ref()` for objects without `.value` access everywhere
**Reference:** https://vuejs.org/guide/essentials/reactivity-fundamentals#reactive-objects

```vue
// WRONG — ref for object
const user = ref({ name: 'John' });
console.log(user.value.name); // Verbose

// RIGHT — reactive for objects
const user = reactive({ name: 'John' });
console.log(user.name); // Cleaner
```

#### 5. Side Effects in Computed (P1)
**Detection:** `computed()` with mutation, async, or side effect
**Reference:** https://vuejs.org/guide/essentials/computed#computed-properties

```vue
// WRONG — side effect in computed
const fullName = computed(() => {
  fetchUser(); // Side effect!
  return `${user.firstName} ${user.lastName}`;
});

// RIGHT — use watch or method instead
const fullName = computed(() => `${user.firstName} ${user.lastName}`);
```

#### 6. Missing Cleanup in onMounted (P1)
**Detection:** Subscription/timer in `onMounted` without `onUnmounted`
**Reference:** https://vuejs.org/guide/essentials/lifecycle#lifecycle-diagram

```vue
// WRONG
onMounted(() => {
  interval = setInterval(fetchData, 5000);
}); // No cleanup!

// RIGHT
onMounted(() => {
  interval = setInterval(fetchData, 5000);
});
onUnmounted(() => clearInterval(interval));
```

#### 7. Using Index as Key (P2)
**Detection:** `:key="index"` in v-for
**Reference:** https://vuejs.org/guide/essentials/list#maintaining-state-with-key

```vue
// WRONG — key changes when array order changes
<div v-for="(item, index) in items" :key="index">

// RIGHT — use stable unique id
<div v-for="item in items" :key="item.id">
```

#### 8. Modifying Array Directly (P2)
**Detection:** Push/splice on reactive array instead of spread/filter
**Reference:** https://vuejs.org/guide/essentials/reactivity-fundamentals#mutating-methods

```vue
// WRONG — mutation
items.push(newItem);

// RIGHT — immutable pattern
items = [...items, newItem];
// Or: items.value.push(newItem) if using ref
```

---

### Svelte Anti-Patterns

#### 1. Not Unsubscribing from Stores (P1)
**Detection:** `$store` usage without understanding subscription lifecycle
**Reference:** https://svelte.dev/docs/svelte-store#auto-subscription

```svelte
// WRONG — memory leak
<script>
  import { count } from './stores';
  onMount(() => {
    // Using $count but not understanding subscription
  });
</script>

// RIGHT — Svelte auto-subscribes with $ prefix
<script>
  import { count } from './stores';
  // $count is automatically subscribed and unsubscribed
</script>
<p>{$count}</p>
```

#### 2. Overusing Reactive Statements (P3)
**Detection:** Multiple `$:` that could be combined into one
**Reference:** https://svelte.dev/docs/svelte-components#script-3-advanced-styles

```svelte
// WRONG — too many reactive statements
$: doubled = count * 2;
$: quadrupled = doubled * 2;
$: console.log(quadrupled);

// RIGHT — compute once
$: quadrupled = count * 4;
```

#### 3. Mutating Props in Reactive Statements (P1)
**Detection:** `export let` followed by reassignment
**Reference:** https://svelte.dev/docs/svelte-components#script

```svelte
// WRONG
<script>
  export let name;
  $: name = name.toUpperCase(); // Error!
</script>

// RIGHT — create derived value
<script>
  export let name;
  $: displayName = name?.toUpperCase();
</script>
<p>{displayName}</p>
```

#### 4. Not Cleaning Up in onDestroy (P1)
**Detection:** Subscription or timer without `onDestroy` cleanup
**Reference:** https://svelte.dev/docs/svelte#ondestroy

```svelte
// WRONG
<script>
  import { onMount } from 'svelte';
  let timer;
  onMount(() => {
    timer = setInterval(() => count++, 1000);
  }); // Memory leak!
</script>

// RIGHT
<script>
  import { onMount, onDestroy } from 'svelte';
  let timer;
  onMount(() => {
    timer = setInterval(() => count++, 1000);
  });
  onDestroy(() => clearInterval(timer));
</script>
```

#### 5. Using Reassignment Instead of Store Methods (P3)
**Detection:** `$count++` when store has update method
**Reference:** https://svelte.dev/docs/svelte-store#writable-stores

```svelte
// OK but not ideal for complex state
count.update(n => n + 1);

// RIGHT — if store exposes specific methods
userStore.incrementAge();
```

---

### Angular Anti-Patterns

#### 1. Subscribing Without Unsubscribe (P1)
**Detection:** `.subscribe()` without `.unsubscribe()` or `takeUntilDestroyed`
**Reference:** https://angular.dev/guide/subscribe#unsubscribing

```typescript
// WRONG — memory leak
@Component({...})
export class UserComponent {
  ngOnInit() {
    this.userService.getUser().subscribe(user => {
      this.user = user;
    });
  }
}

// RIGHT — use takeUntilDestroyed or async pipe
@Component({...})
export class UserComponent implements OnDestroy {
  private destroy$ = destroyRegistry();
  
  ngOnInit() {
    this.userService.getUser()
      .pipe(takeUntilDestroyed(this.destroy$))
      .subscribe(user => this.user = user);
  }
}

// BEST — use async pipe in template
@Component({...})
export class UserComponent {
  user$ = this.userService.getUser();
}
```

#### 2. Changing Values in ngOnInit (P1)
**Detection:** Form control or state mutation in `ngOnInit`
**Reference:** https://angular.dev/guide/lifecycle-hooks

```typescript
// WRONG — should be in constructor or ngDoCheck
@Component({...})
export class ProfileComponent implements OnInit {
  ngOnInit() {
    this.form.setValue({...}); // Too late for initial render
  }
}

// RIGHT — initialize in constructor
@Component({...})
export class ProfileComponent {
  form = new FormGroup({
    name: new FormControl(')
  });
}
```

#### 3. Using ngIf with Hidden Elements (P2)
**Detection:** `*ngIf="false"` followed by `display: none` or `[hidden]`
**Reference:** https://angular.dev/api/common/NgIf

```html
<!-- WRONG — double handling -->
<div *ngIf="show" [hidden]="!show" class="content">
  Content
</div>

<!-- RIGHT — choose one -->
<div *ngIf="show" class="content">
  Content
</div>
```

#### 4. Not Using trackBy in ngFor (P2)
**Detection:** `*ngFor` without `trackBy` function
**Reference:** https://angular.dev/api/common/NgFor

```html
<!-- WRONG — expensive re-renders -->
<div *ngFor="let item of items">
  {{ item.name }}
</div>

<!-- RIGHT -->
<div *ngFor="let item of items; trackBy: trackById">
  {{ item.name }}
</div>
```

```typescript
trackById(index: number, item: Item): string {
  return item.id;
}
```

#### 5. HTTP Calls in Constructor (P1)
**Detection:** HTTP call in constructor instead of ngOnInit
**Reference:** https://angular.dev/guide/di

```typescript
// WRONG — too early, may not have all dependencies
constructor(private http: HttpClient) {
  this.http.get('/api/user').subscribe();
}

// RIGHT — wait for component initialization
constructor(private http: HttpClient) {}

ngOnInit() {
  this.http.get('/api/user').subscribe();
}
```

---

### Astro Anti-Patterns

#### 1. Client-Side Data Fetching When Server-Side Possible (P2)
**Detection:** `fetch()` inside component without checking if static possible
**Reference:** https://docs.astro.build/en/recipes/build-time-data-fetching

```astro
// WRONG — fetching at runtime when build-time is possible
---
const data = await fetch('https://api.example.com/data').then(r => r.json());
---
<script>
// Or in client-side script
const data = await fetch('https://api.example.com/data').then(r => r.json());
</script>

// RIGHT — fetch at build time
---
// In frontmatter (runs at build)
const data = await fetch('https://api.example.com/data').then(r => r.json());
---
```

#### 2. Improper Prop Typing (P2)
**Detection:** Missing or incorrect `Props` interface
**Reference:** https://docs.astro.build/en/guides/typescript#component-props

```astro
// WRONG — no typing
---
const { title, count } = Astro.props;
// No TypeScript validation
---

// RIGHT — proper interface
---
interface Props {
  title: string;
  count?: number;
}
const { title, count = 0 } = Astro.props as Props;
---
```

#### 3. Mixing Component Types (P2)
**Detection:** Using `.astro` component in client script without directive
**Reference:** https://docs.astro.build/en/concepts/islands

```astro
// WRONG — client component without directive
import ReactButton from './ReactButton.jsx';

// RIGHT — use client directive
import ReactButton from './ReactButton.jsx';
<ReactButton client:load />
```

#### 4. Unnecessary Client Directive (P2)
**Detection:** `client:*` on static components
**Reference:** https://docs.astro.build/en/reference/directives-reference#client-directives

```astro
// WRONG — static component doesn't need client directive
<StaticHeader client:load />

// RIGHT — only when interactivity needed
<InteractiveButton client:visible />
```

#### 5. Missing Props Validation (P2)
**Detection:** No TypeScript interface for component props
**Reference:** https://docs.astro.build/en/guides/typescript/#component-props

```astro
// WRONG
---
const { title, items } = Astro.props;
// What if title is undefined?
---

// RIGHT
---
interface Props {
  title: string;
  items: string[];
}
const { title, items } = Astro.props as Props;
---
```

---

### General JS/TS Anti-Patterns

#### 1. Not Handling Async Errors (P1)
**Detection:** `async` function without try/catch or `.catch()`
**Reference:** https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function

```typescript
// WRONG
async function fetchUser(id: string) {
  const response = await fetch(`/api/users/${id}`);
  return response.json(); // Unhandled rejection on error!
}

// RIGHT
async function fetchUser(id: string) {
  try {
    const response = await fetch(`/api/users/${id}`);
    if (!response.ok) throw new Error('User not found');
    return response.json();
  } catch (error) {
    console.error('Failed to fetch user', error);
    throw error;
  }
}
```

#### 2. Using `any` Instead of Proper Types (P2)
**Detection:** Type annotation with `any`
**Reference:** https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#any

```typescript
// WRONG
function processData(data: any) {
  return data.name; // No type safety!
}

// RIGHT
interface User {
  name: string;
  age: number;
}
function processData(data: User) {
  return data.name;
}
```

#### 3. Mutating Parameters (P3)
**Detection:** Assignment to function parameters
**Reference:** https://www.typescriptlang.org/docs/handbook/2/functions.html#parameter-destructuring

```typescript
// WRONG
function processUser(user: User) {
  user.name = 'Modified'; // Mutates original!
}

// RIGHT
function processUser(user: User): User {
  return { ...user, name: 'Modified' };
}
```

#### 4. Creating Objects in Render (P2)
**Detection:** Object/array creation inside render/return
**Reference:** https://www.typescriptlang.org/docs/handbook/2/functions.html#rest-parameters

```tsx
// WRONG — new array every render
const Child = ({ items }) => (
  items.map(item => <div key={{ id: item.id }}>{item.name}</div>)
);

// RIGHT — stable key
const Child = ({ items }) => (
  items.map(item => <div key={item.id}>{item.name}</div>)
);
```

#### 5. Not Using Optional Chaining (P2)
**Detection:** Manual null check before accessing nested property
**Reference:** https://www.typescriptlang.org/docs/handbook/2/functions.html#optional-parameters

```typescript
// WRONG — verbose null checks
const name = user && user.profile && user.profile.name;

// RIGHT — optional chaining
const name = user?.profile?.name;
```

#### 6. Null vs Undefined Confusion (P3)
**Detection:** Inconsistent use of null and undefined
**Reference:** https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#null-and-undefined

```typescript
// WRONG — mixing null and undefined
function createUser(name: string, age?: number | null) {
  // Confusing when to use which
}

// RIGHT — consistent approach
function createUser(name: string, age?: number) {
  // Use undefined for optional, value for required
}
```

---

## Issue Severity

| Severity | Meaning | Examples |
|---|---|---|
| **P0** | Blocking — CI will fail | Bare oklch in component rule, broken dark mode override, critical API misuse |
| **P1** | High — must fix | Missing aria-label, invalid BEM, hardcoded spacing, hook deps missing |
| **P2** | Medium — should fix | Duplicate rules, empty catch blocks, semantic violations |
| **P3** | Low — polish | Code style, cosmetic issues |

## Output Format

### Summary Header

```
## Argus Design Review Summary
- Total Issues: N (P0: X | P1: X | P2: X | P3: X)
- Files Reviewed: N
- Technology Stack: {detected stack}
- Documentation: {official docs URL}
```

### Severity Groups

Issues are grouped under headers in order: P0 → P1 → P2 → P3.

```
## P0 — Blocking Issues (must fix, CI will fail)

## P1 — High Priority (must fix before merge)

## P2 — Medium Priority (should fix)

## P3 — Low Priority (optional polish)
```

### Issue Block (repeats per issue)

```
[P{severity}] {file}:{line} — {short description}

  Found:    {current code snippet}
  Expected: {correct code snippet}

  Fix:
  ```{extension}
  {copy-ready fix code}
  ```

  Token:    {design token to use, if applicable}
  Reference: {official docs URL for this API}
  Note:     {optional context or explanation}
```

### Format Rules

- Each issue block starts with a `─────────────────────────────────────────────────` separator line
- Code snippets are shown inline, truncated to relevant portion (max 80 chars per line)
- **Fix code block is mandatory** — always provide the exact fix to copy
- Empty `Note:` line is omitted if not needed
- No issue = output `✓ No issues found` under each severity group
- Always include `Reference:` link when flagging framework API issues

## Review Workflow

1. **Detect stack** — scan file extensions and package.json
2. Read the codebase — understand the design token system in use
3. Scan for bare color values (oklch/hex/rgb outside :root declarations)
4. Scan for magic numbers in spacing, radii, font sizes
5. Verify dark mode coverage for every color token
6. Check accessibility — buttons, images, semantic HTML
7. Check CSS quality — duplicates, BEM, empty catch blocks
8. **Stack-specific API checks** — verify hooks, directives, lifecycle usage against Framework Anti-Patterns Library
9. **Generate fixes** — provide copy-ready code for every issue found
10. Report findings grouped by severity

**In automated PR review mode:** The composite action at `.github/actions/argus-review/action.yml` reads `AGENTS.md` + `SKILL.md` from the argus repo at runtime and injects their contents into the LLM prompt. The review is performed by the `argus-flash` GitHub App, which comments findings directly on the PR.

## Non-Blocking Context

Do NOT flag issues in:
- Third-party resets or normalize.css
- Generated boilerplate that will be replaced
- Test fixtures and mock data files
- `node_modules/` (ignore entirely)
- Workflow YAML files (`.github/workflows/`, `.github/actions/`)
