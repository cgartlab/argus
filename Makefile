# Makefile — Argus

VERSION := $(shell cat VERSION)
RELEASE_BRANCH := release/v$(VERSION)

.PHONY: help
help:
	@echo "Argus Makefile"
	@echo ""
	@echo "  make check-version    — show current version"
	@echo "  make bump-patch       — bump PATCH (e.g. 0.2.0 → 0.2.1)"
	@echo "  make bump-minor       — bump MINOR (e.g. 0.2.0 → 0.3.0)"
	@echo "  make bump-major       — bump MAJOR (e.g. 0.2.0 → 1.0.0)"
	@echo "  make validate         — run all quality checks (SKILL.md, CHANGELOG, files)"
	@echo "  make test-fixtures    — run fixture regression tests (static heuristic mode)"
	@echo "  make test             — validate + test-fixtures (full pre-release check)"
	@echo "  make release          — commit, tag and push a release"
	@echo "  make package          — create release archive"
	@echo "  make clean            — remove generated files"

.PHONY: check-version
check-version:
	@echo "Current version: $(VERSION)"

# ─── Version bumping ─────────────────────────────────────────────
.PHONY: bump-patch bump-minor bump-major
bump-patch bump-minor bump-major: BUMP_KIND=$(notdir $(firstword $(MAKECMDGOALS)))
bump-patch bump-minor bump-major:
	@python3 tools/bump_version.py $(BUMP_KIND)
	@echo ""
	@echo "Files staged. Review, then: make test && make release"

# ─── Validation ──────────────────────────────────────────────────
.PHONY: validate
validate:
	@echo "── Validate: SKILL.md trigger phrases ──"
	@python3 -c "import sys, re; f=open('SKILL.md').read(); phrases=[p.strip() for p in re.findall(r'(?:when|phrases?)[:\s]+([^\n]+)', f, re.I)]; print('SKILL.md ok') if len(phrases) >= 3 else (print('SKILL.md: need 3+ trigger phrases'), sys.exit(1))" 2>/dev/null || echo "SKILL.md: could not verify trigger phrases automatically"
	@echo "── Validate: VERSION matches CHANGELOG ──"
	@grep -q "^## \[$(VERSION)\]" CHANGELOG.md && echo "CHANGELOG ok" || (echo "CHANGELOG: missing [$(VERSION)] section" && exit 1)
	@echo "── Validate: required files ──"
	@for f in AGENTS.md SKILL.md README.md VERSION CHANGELOG.md \
	           tools/run_fixture_tests.py tools/load_config.py \
	           docs/argus-config-schema.md \
	           .github/actions/argus-review/action.yml \
	           tests/fixtures/README.md; do \
	    test -f "$$f" && echo "$$f ok" || (echo "$$f missing" && exit 1); \
	done
	@echo "── Validate: Python tool syntax ──"
	@python3 -m py_compile tools/run_fixture_tests.py && echo "run_fixture_tests.py ok"
	@python3 -m py_compile tools/load_config.py && echo "load_config.py ok"
	@echo "── Validate: load_config defaults ──"
	@python3 tools/load_config.py --validate-only
	@echo ""
	@echo "All validation checks passed ✓"

# ─── Fixture regression tests ─────────────────────────────────────
.PHONY: test-fixtures
test-fixtures:
	@echo "── Fixture Tests (static heuristic mode) ──"
	@python3 tools/run_fixture_tests.py
	@echo ""

# Full mode: requires OpenCode CLI + configured model
.PHONY: test-fixtures-llm
test-fixtures-llm:
	@echo "── Fixture Tests (LLM mode) ──"
	@python3 tools/run_fixture_tests.py --model $(or $(MODEL),opencode/deepseek-v4-flash-free)
	@echo ""

# ─── Combined pre-release check ──────────────────────────────────
.PHONY: test
test: validate test-fixtures
	@echo ""
	@echo "All checks passed — ready to release ✓"

# ─── Release ─────────────────────────────────────────────────────
.PHONY: release
release: validate
	@echo "Checking for staged changes..."
	@git diff --quiet --cached \
	  || { echo "Uncommitted changes found. Commit or stash first."; exit 1; }
	@echo "Creating commit and tag for v$(VERSION)..."
	@git commit -m "chore(release): v$(VERSION)" || { echo "Nothing to commit"; exit 0; }
	@git tag v$(VERSION)
	@echo "Pushing main and tag..."
	@git push origin main && git push origin tags/v$(VERSION)
	@echo ""
	@echo "Released v$(VERSION) — GitHub Actions will create the Release page"

# ─── Package ─────────────────────────────────────────────────────
.PHONY: package
package:
	@mkdir -p dist
	@tar --exclude='.git' --exclude='dist' -czf dist/argus-v$(VERSION).tar.gz .
	@zip -q dist/argus-v$(VERSION).zip . -r -x '.git/*' -x 'dist/*'
	@echo "Packages created: dist/argus-v$(VERSION).tar.gz dist/argus-v$(VERSION).zip"

# ─── Clean ───────────────────────────────────────────────────────
.PHONY: clean
clean:
	@rm -rf dist
	@echo "Cleaned"
