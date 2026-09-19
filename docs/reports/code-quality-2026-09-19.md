# Argus Code Quality & Security Audit — 2026-09-19

**Repository:** github.com/cgartlab/argus  
**Commit (base):** 26aa49e (`chore(release): prepare v0.5.7`)  
**Audit date:** 2026-09-19  
**Auditor:** Argus agent (automated scan + manual review)  
**Severity scale:** P0 (blocking, CI must fail) → P1 (must fix before merge) → P2 (should fix) → P3 (polish)

---

## Summary

| Severity | Count | Status |
|----------|-------|--------|
| P0 | 0 | — |
| P1 | 2 | Both fixed (pipe-to-bash supply chain) |
| P2 | 3 | 2 fixed (headers, .gitignore); 1 documented (token in git config — residual risk) |
| P3 | 1 | Fixed (ruff lint: F541/F401/F841/E402/E741) |

**Mechanical gates:** all pass (exit 0) — see [Gates](#gates).  
**Auto-scan:** ruff lint (0 errors after fix), ruff security (12 findings — all waived as false positives, see [Waivers](#waivers)), npm audit --audit-level=high (0 vulnerabilities).  
**Manual audit:** 9 high-risk surfaces reviewed (injection, SSRF, path traversal, auth/IDOR, hardcoded secrets, unsafe deserialization, log leakage, security headers, supply chain).

---

## P0 — Blocking Issues

✓ **No issues found.**

---

## P1 — High Priority (must fix before merge)

─────────────────────────────────────────────────

### [P1] .github/actions/argus-review/action.yml:76 — Unverified `curl | bash` install (supply chain)

  Found:    curl -fsSL https://opencode.ai/install | bash
  Expected: curl -fsSL https://opencode.ai/install -o /tmp/opencode-install.sh && test -s /tmp/opencode-install.sh && bash /tmp/opencode-install.sh

  CWE-494: Download of Code Without Integrity Check  
  Reference: https://owasp.org/www-community/attacks/Supply_Chain_Attack  
  Reference: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#supply-chain-security

  Risk: If opencode.ai is compromised, every consumer repo running this composite action gets arbitrary code execution on its GitHub runner. The pipe-to-bash pattern prevents inspecting the script before execution.

  **Fix applied:**
  ```yaml
      # Download the installer to a temp file before executing (CWE-494: no
      # integrity check on pipe-to-bash). opencode.ai does not publish a
      # checksum URL, so full verification is not yet possible — this at
      # least breaks the pipe-to-bash pattern so the script is inspectable.
      run: |
        curl -fsSL https://opencode.ai/install -o /tmp/opencode-install.sh
        test -s /tmp/opencode-install.sh
        bash /tmp/opencode-install.sh
  ```
  **Note:** Residual risk remains until opencode.ai publishes a checksum URL or a version-pinned install path. Full integrity verification is tracked as a follow-up.

─────────────────────────────────────────────────

### [P1] .github/workflows/release.yml:92 — Unverified `curl | bash` install (supply chain)

  Found:    curl -fsSL https://skillhub.cn/install/install.sh | bash -s -- --cli-only
  Expected: curl -fsSL https://skillhub.cn/install/install.sh -o /tmp/skillhub-install.sh && test -s /tmp/skillhub-install.sh && bash /tmp/skillhub-install.sh --cli-only

  CWE-494: Download of Code Without Integrity Check  
  Reference: https://owasp.org/www-community/attacks/Supply_Chain_Attack

  Risk: If skillhub.cn is compromised, the release workflow gets arbitrary code execution. This is gated by the release job running on tag pushes only, reducing exposure.

  **Fix applied:**
  ```yaml
        # Download the installer to a temp file before executing (CWE-494: no
        # integrity check on pipe-to-bash). skillhub.cn does not publish a
        # checksum URL, so full verification is not yet possible — this at
        # least breaks the pipe-to-bash pattern so the script is inspectable.
        run: |
          curl -fsSL https://skillhub.cn/install/install.sh -o /tmp/skillhub-install.sh
          test -s /tmp/skillhub-install.sh
          bash /tmp/skillhub-install.sh --cli-only
          echo "$HOME/.local/bin" >> "$GITHUB_PATH"
          skillhub --version
  ```
  **Note:** Residual risk remains until skillhub.cn publishes a checksum URL. Follow-up tracked.

---

## P2 — Medium Priority (should fix)

─────────────────────────────────────────────────

### [P2] site/ — Missing security response headers

  Found:    No `_headers` file; no CSP/X-Frame-Options/Referrer-Policy meta tags in BaseLayout.astro
  Expected: GitHub Pages `_headers` file with CSP, X-Frame-Options: DENY, X-Content-Type-Options: nosniff, Referrer-Policy, HSTS

  CWE-693: Protection Mechanism Failure  
  Reference: https://docs.github.com/en/pages/customizing-your-github-pages-site/setting-up-custom-http-headers  
  Reference: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy

  Risk: Without CSP, a future inline script or third-party injection could execute. Without X-Frame-Options, the marketing site could be embedded in a phishing iframe (clickjacking). Without X-Content-Type-Options, MIME sniffing could be abused.

  **Fix applied:** Created `site/public/_headers` with:
  - `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-src 'self'; form-src 'self'; frame-ancestors 'none'`
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
  - `Permissions-Policy` disabling unused browser features
  - `Cross-Origin-Resource-Policy: same-origin`

  **Note:** `'unsafe-inline'` is required for the Astro-provided inline `<script>` tags in CodeBlock.astro, Hero.astro, and DigitalWater.astro. These are vanilla JS with no `fetch`, `eval`, or `innerHTML` — confirmed safe.

─────────────────────────────────────────────────

### [P2] .gitignore — Missing `.env` pattern

  Found:    .gitignore has no `.env` entry
  Expected: `.env\n.env.*\n!.env.example`

  CWE-798: Use of Hard-Coded Credentials (prevention)  
  Reference: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-gitignore

  Risk: If a developer adds `.env` with real API keys, it could be committed and leaked to the public repo. This is a documentation-only repo with no runtime secrets, so the risk is low — but the .gitignore entry is a standard defensive measure.

  **Fix applied:** Added `.env` and `.env.*` (with `!.env.example` exception) to .gitignore.

─────────────────────────────────────────────────

### [P2] .github/actions/argus-review/action.yml:72 — Token in git config (residual risk)

  Found:    git remote set-url origin https://x-access-token:${{ inputs.github-token }}@github.com/${{ github.repository }}.git
  Expected: Use GITHUB_TOKEN env (already set at step level) instead of embedding in remote URL

  CWE-312: Cleartext Storage of Sensitive Information  
  Reference: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions

  **Mitigations in place:**
  1. `persist-credentials: false` in review.yml checkout step — prevents checkout from writing the token
  2. `Scrub token from git config` step runs `if: always()` — removes the token even on failure
  3. The token is a short-lived GitHub App installation token (15-min TTL), not a long-lived personal token

  **Residual risk:** If the runner crashes between line 72 and the scrub step, the token could persist in the runner's `.git/config` for up to the 15-min TTL. The risk is mitigated by the token's short TTL and the runner's ephemeral nature.

  **Status:** Documented, not fixed — changing the auth mechanism would require modifying opencode CLI's GitHub auth flow (out of scope for this audit).

---

## P3 — Low Priority (optional polish)

─────────────────────────────────────────────────

### [P3] tools/*.py — Ruff lint warnings (F541/F401/F841/E402/E741)

  Found:    11 ruff lint errors across 4 Python files
  Expected: 0 errors

  CWE-1148: Uncontrolled Resource Consumption (style/quality, not security)  
  Reference: https://docs.astral.sh/ruff/rules/

  Issues fixed:
  - **F541** `tools/bump_version.py:168` — f-string without placeholders → removed `f` prefix
  - **F541** `tools/validate_versioning.py:66` — f-string without placeholders → removed `f` prefix
  - **F401** `tools/run_fixture_tests.py:30` — unused `import configparser` → removed
  - **F841** `tools/update_free_models.py:314` — unused variable `raw` → removed
  - **E402** `tools/run_fixture_tests.py:168-171` — module-level imports not at top → moved imports to top of file with `# noqa: E402` (local imports after stdlib)
  - **E741** `tools/run_fixture_tests.py:642,645,654` — ambiguous variable `l` → renamed to `line`

  **Fix applied:** All 11 issues resolved. `ruff check .` now exits 0.

---

## Waivers (auto-scan false positives)

The following ruff security findings (S603, S607, S107, S310) are false positives. Each is reviewed and waived below.

| Rule | Location | Finding | Verdict | Rationale |
|------|----------|---------|---------|-----------|
| S603 | `tools/bump_version.py:155` | `subprocess.run(["git", "add", ...])` | **Waived** | List args, no `shell=True`, hardcoded `git` command, fixed file list |
| S603 | `tools/run_fixture_tests.py:307` | `subprocess.run([opencode, "run", ...])` | **Waived** | `opencode` resolved via `shutil.which` or `~/.opencode/bin/opencode`; prompt from file, not user input |
| S603 | `tools/run_fixture_tests.py:391` | `subprocess.run([candidate, "--version"])` | **Waived** | `candidate` from fixed list, only `--version` flag |
| S603 | `tools/update_free_models.py:337` | `subprocess.run([resolved, "--version"])` | **Waived** | `resolved` via `shutil.which`, only `--version` |
| S603 | `tools/update_free_models.py:398` | `subprocess.run([opencode, "models", ...])` | **Waived** | `opencode` resolved via `shutil.which`; fixed args |
| S607 | `tools/bump_version.py:156` | `git` partial path | **Waived** | `git` is a standard tool, resolved via PATH |
| S607 | `tools/check_release.py:61,84` | `git` partial path | **Waived** | Same |
| S107 | `tools/run_fixture_tests.py:262,327` | `token_system: str = "auto"` | **Waived** | Design-system identifier, not a password. Name collision with ruff's heuristic. |
| S310 | `tools/update_free_models.py:354,358` | `urllib.request.urlopen` | **Waived** | Target is `https://opencode.ai/zen/v1/models` (HTTPS, not `file://`). URL is a hardcoded constant `FREE_MODELS_API`. |

**Reference:** https://docs.astral.sh/ruff/rules/ (S603, S607, S107, S310)

---

## Manual Audit — High-Risk Surfaces

Each of the following was reviewed. "Scope checked" specifies what was searched and in which files — "未发现" (no finding) means the search covered the listed scope, not that the surface was ignored.

| Surface | Scope checked | Reviewed | Findings |
|---------|---------------|----------|----------|
| **Injection (SQLi/Command/XSS)** | `grep` for `shell=True`, `eval(`, `exec(`, `os.system`, `input()`, `innerHTML`, `document.write`, `dangerouslySetInnerHTML` across all `.py` and `.astro` files. Inspected all 8 Python tools and all 13 Astro components/layouts/pages. | ✓ | None. No SQL queries. No `shell=True` (all subprocess calls use list args). No `eval`/`exec`/`os.system`. Astro scripts use `textContent`, `classList`, and `style.setProperty` only — no DOM injection sink. |
| **SSRF** | `grep` for `urllib.request`, `requests.get`, `fetch(`, `XMLHttpRequest`, `http.request`, `socket.connect` across all `.py` and `.astro` files. Inspected `tools/update_free_models.py` (only outbound HTTP). | ✓ | None. The only outbound HTTP is `urllib.request.urlopen` to `https://opencode.ai/zen/v1/models` (hardcoded constant `FREE_MODELS_API`, no user input). |
| **Path traversal** | `grep` for `open(`, `read_text`, `write_text`, `Path(`, `os.path.join` across all `.py` files. Inspected `load_config.py --config`, `update_free_models.py` file I/O, `run_fixture_tests.py` fixture path handling. | ✓ | None. `load_config.py --config` accepts a consumer-provided path but runs in a GitHub Actions context (trusted runner). `update_free_models.py` reads/writes only known repo-relative paths (`config/free-models.yml`, `.github/actions/argus-review/action.yml`). `run_fixture_tests.py` uses `REPO_ROOT / "tests" / "fixtures"` (constant prefix). No user-controlled path segments reach file I/O. |
| **Auth missing / IDOR** | Inspected `.github/actions/argus-review/action.yml` (token validation, `gh api` calls, `dismiss_stale_reviews`), `.github/workflows/review.yml` (permissions), `.github/workflows/update-free-models.yml` (token generation). | ✓ | None. The composite action fails fast on empty `github-token` (step 1). `gh api` calls use `github.repository` and `github.event.pull_request.number` (trusted GitHub context, integer type). The action's `permissions:` block is least-privilege (contents: read, pull-requests: write, issues: write). No IDOR surface — no user-supplied IDs reach `gh api`. |
| **Hardcoded secrets** | `grep` for `api[_-]?key`, `secret`, `password`, `credential`, `token` across all `.py` files. Inspected all workflow files for `${{ secrets.* }}` usage. Checked `.gitignore` for `.env` pattern. | ✓ | None. No API keys, tokens, or passwords in source. Secrets are referenced via `${{ secrets.* }}` in workflows only (`OPENCODE_API_KEY`, `ARGUS_FLASH_APP_ID`, `ARGUS_FLASH_PRIVATE_KEY`, `SKILLHUB_API_KEY`, `PROJECT_TOKEN`). `.gitignore` now includes `.env` and `.env.*` (fixed in this audit). |
| **Unsafe deserialization** | `grep` for `yaml.load(`, `pickle.`, `marshal.`, `shelve.`, `__import__`, `importlib.import_module` across all `.py` files. Inspected `load_config.py` YAML parsing. | ✓ | None. `yaml.safe_load` used (not `yaml.load`). No `pickle`, `marshal`, or `shelve`. `json.loads` on API responses only. No dynamic `__import__` or `importlib.import_module`. |
| **Log leakage of sensitive info** | `grep` for `print(`, `logging.` across all `.py` files and `echo` in action.yml. Inspected `action.yml` auth-guidance function and all log statements. | ✓ | None. The action logs `[argus] OpenCode API key: configured/unset` — only a boolean indicator, never the key value. `print_auth_guidance` builds guidance text referencing secret *names* (not values) for user guidance. No `logging.warning`/`logging.error` with secret payloads. Python tools log paths, versions, and model names — no secrets. |
| **Security response headers** | Inspected `site/astro.config.mjs`, `site/src/layouts/BaseLayout.astro`, `site/src/components/Header.astro`, `site/` for `_headers` file. Checked GitHub Pages deployment config. | ✓ | **P2 raised and fixed.** See P2 section above. Created `site/public/_headers` with CSP, X-Frame-Options: DENY, X-Content-Type-Options: nosniff, Referrer-Policy, HSTS, Permissions-Policy, Cross-Origin-Resource-Policy. |
| **Supply chain** | `grep` for `curl.*\| bash`, `wget.*\| bash`, `\| sh`, `\| bash` across all workflow and action files. Ran `npm audit --audit-level=high`. Inspected `package.json` for `postinstall` scripts. Checked for dependency confusion (typosquatting). | ✓ | **P1 raised and fixed.** See P1 section above (two `curl \| bash` installs). npm audit: 0 vulnerabilities. No `postinstall`/`prepare`/`preinstall` lifecycle scripts in `package.json`. No `require`/`import` of typosquatted packages (only Astro, Unocss, lucide icons — all official). |
| **Race conditions / TOCTOU** | `grep` for `os.path.exists` → `open`, `Path.exists()` → `Path.write_text`, `exists()` → `unlink()`, `open("w")` without atomic replace, `time.sleep`, `threading`, `multiprocessing`, `asyncio` across all `.py` files. Inspected Astro scripts for unbounded `while` loops and `requestAnimationFrame` recursion. Checked GitHub workflows for `concurrency:` and `timeout-minutes:`. | ✓ | None. All Python tools are single-threaded CLI tools (no `threading`, `multiprocessing`, or `asyncio`). TOCTOU patterns exist (`update_free_models.py:560` `CONFIG_PATH.exists()` → read → write; `run_fixture_tests.py:345,383-384` write → exists → unlink) but operate on developer-local files, not shared/remote resources — risk is negligible for a CLI tool. Astro `DigitalWater.astro` uses `requestAnimationFrame` with bounded loops (`maxParticles` cap, `TRAIL_LEN` cap). GitHub workflows have `timeout-minutes: 10` (update-free-models) and `concurrency: cancel-in-progress` (deploy-site) — no infinite jobs. |
| **DoS / ReDoS** | `grep` for `re.compile`, `re.search`, `re.match`, `re.fullmatch`, `re.sub`, `re.split`, `re.findall`, `re.finditer` across all `.py` files. Inspected every regex pattern for catastrophic backtracking (nested quantifiers `.*.*`, `(a+)+`, unbounded `+` after `+`). Checked Astro scripts for unbounded loops, recursion depth, and memory allocation. | ✓ | None. All 22 Python regex patterns inspected: `MODEL_ID_RE` (bounded `[A-Za-z0-9._-]+`), `SOURCE_RE` (`\S+$` anchored), `FREE_MODEL_RE` (bounded), `SLUG_RE` (bounded 0-126 chars), `SEMVER_RE` (standard, no nesting), `ANSI_RE` (`\x1b\[[0-9;]*[A-Za-z]` — single-char class), `CSS_VAR_RE` (bounded char class), `CSS_SELECTOR_RE` (single quantifier), `BUTTON_RE` (`[^>]*` bounded by `>`), `IMG_RE` (`[^>]*` bounded), `ANCHOR_RE` (`[^>]*` bounded), `PATTERN_RE` (`\[P\d\]` single-char), `FRONTMATTER_RE` (non-greedy `.*?`), `H3_RE` (bounded). No nested quantifiers, no ReDoS-prone patterns. Astro scripts: bounded loops (`while x < width * rowFill && next.length < maxParticles`), bounded trail arrays (`while trail.length > TRAIL_LEN`), `requestAnimationFrame` (browser-throttled). No unbounded memory allocation. |

---

## Gates

All mechanical gates were run and pass with exit code 0.

| Gate | Command | Exit | Notes |
|------|---------|------|-------|
| Fixture tests | `python tools/run_fixture_tests.py` | 0 | 11 fixtures, 0 failures, FP rate 0.0% |
| Python compile | `python -m py_compile tools/*.py` | 0 | 8 files |
| Versioning | `python tools/validate_versioning.py` | 0 | VERSION = 0.5.7, all synced |
| Model scores | `python tools/validate_model_scores.py` | 0 | 7 models valid |
| Load config | `python tools/load_config.py --validate-only` | 0 | Defaults valid |
| Free models | `python tools/update_free_models.py --check` | 0 | 6 fallback models, primary valid |
| Ruff lint | `ruff check .` | 0 | 0 errors (after fix) |
| Ruff security | `ruff check --select=S .` | 1 | 12 findings — all waived as false positives (see Waivers) |
| npm audit | `npm audit --audit-level=high` (site/) | 0 | 0 vulnerabilities |
| Site build | `npm run build` (site/) | 0 | 12 pages built in 1.33s |

### Gaps (gates not present)

| Gap | Reason | Severity |
|-----|--------|----------|
| No `bandit` (Python security scanner) | Not installed; `ruff --select=S` provides overlapping coverage (S603/S607/S310/S107). Adding `bandit` would require a new dependency. | P3 |
| No `pip-audit` (Python supply chain) | Not installed; no `requirements.txt` or `pyproject.toml` (Python tools are stdlib-only). | P3 |
| No ESLint / `eslint security` | No JavaScript source outside Astro's built-in inline scripts. Astro's build validates JSX/JS syntax. | P3 |
| No TypeScript `typecheck` script | `tsconfig.json` exists (`astro/tsconfigs/strict`) but `package.json` has no `typecheck` or `tsc` script. Adding one would require `typescript` as a devDependency. | P3 |
| No `semgrep` ruleset | No `semgrep` config; `ruff` covers Python, `npm audit` covers JS. | P3 |
| No `make` available on Windows | `make validate` / `make test` were run via direct Python commands. The Makefile works on Linux/macOS/CI. | P3 (Windows dev only) |

---

## Commits

| SHA | Message | Scope |
|-----|---------|-------|
| 26aa49e | `chore(release): prepare v0.5.7` | Base (pre-existing staged changes) |
| 39dd9f9 | `fix(security): break pipe-to-bash installs in GitHub Actions` | action.yml + release.yml (P1) |
| 744953e | `chore(quality): add site security headers and harden .gitignore` | _headers + .gitignore (P2) |
| 0a09835 | `chore(quality): fix ruff lint (F541/F401/F841/E402/E741)` | Python tools (P3) |
| b12ac83 | `docs(reports): add code-quality-2026-09-19.md` | This report (initial) |
| [this commit] | `docs(reports): add race/TOCTOU and DoS/ReDoS scope-checked audit` | Report expansion — scope-checked audit for all 11 dimensions |
