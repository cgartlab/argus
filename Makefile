# Makefile — Argus

# Strip CR/LF/space so Windows (CRLF checkouts) and POSIX behave identically.
VERSION := $(shell tr -d '\r\n ' < VERSION)
RELEASE_BRANCH := release/v$(VERSION)

.PHONY: help
help:
	@echo "Argus Makefile"
	@echo ""
	@echo "  make check-version    — show current version + release status"
	@echo "  make bump-patch       — bump PATCH (e.g. 0.3.0 → 0.3.1)"
	@echo "  make bump-minor       — bump MINOR (e.g. 0.3.0 → 0.4.0)"
	@echo "  make bump-major       — bump MAJOR (e.g. 0.3.0 → 1.0.0)"
	@echo "  make validate         — run all quality checks (SKILL.md, CHANGELOG, files)"
	@echo "  make test-fixtures    — run fixture regression tests (static heuristic mode)"
	@echo "  make test             — validate + test-fixtures (full pre-release check)"
	@echo "  make release          — release-gate → verify → tag → push (triggers release workflow)"
	@echo "  make package-skill    — create skill package (argus-skill-v{VERSION}.zip)"
	@echo "  make package          — create all release archives"
	@echo "  make prepare-skillhub — prepare SkillHub publish directory from skill package"
	@echo "  make clean            — remove generated files"

.PHONY: check-version
check-version:
	@echo "Current version: $(VERSION)"
	@echo "── Release status ──"
	@python3 tools/check_release.py

# ─── Version bumping ─────────────────────────────────────────────
.PHONY: bump-patch bump-minor bump-major
bump-patch bump-minor bump-major: BUMP_KIND=$(notdir $(firstword $(MAKECMDGOALS)))
bump-patch bump-minor bump-major:
	@python3 tools/bump_version.py $(BUMP_KIND)
	@echo ""
	@echo "Files staged. Fill in the new CHANGELOG section, review, then:"
	@echo "  git commit -m \"chore(release): prepare v$(VERSION)\""
	@echo "  make test && make release"

# ─── Validation ──────────────────────────────────────────────────
.PHONY: validate
validate:
	@echo "── Validate: SKILL.md trigger phrases ──"
	@if command -v python3 >/dev/null 2>&1; then python3 -c "import sys, re; f=open('SKILL.md').read(); phrases=[p.strip() for p in re.findall(r'(?:when|phrases?)[:\s]+([^\n]+)', f, re.I)]; print('SKILL.md ok') if len(phrases) >= 3 else (print('SKILL.md: need 3+ trigger phrases'), sys.exit(1))"; else echo "SKILL.md: python3 not available — trigger phrase check skipped (warning)"; fi
	@echo "── Validate: VERSION matches CHANGELOG ──"
	@grep -q "^## \[$(VERSION)\]" CHANGELOG.md && echo "CHANGELOG ok" || (echo "CHANGELOG: missing [$(VERSION)] section" && exit 1)
	@echo "── Validate: versioning consistency (VERSION ↔ CHANGELOG) ──"
	@if command -v python3 >/dev/null 2>&1; then python3 tools/validate_versioning.py; else echo "validate_versioning: python3 not available — versioning check skipped (warning)"; fi
	@echo "── Validate: required files ──"
	@for f in AGENTS.md SKILL.md README.md VERSION CHANGELOG.md \
	           CONTRIBUTING.md Makefile \
	           tools/run_fixture_tests.py tools/load_config.py \
	           tools/update_free_models.py tools/bump_version.py \
	           tools/validate_versioning.py tools/validate_model_scores.py \
	           tools/check_release.py tools/publish_skillhub.py tools/validate_argus_schema.py \
	           config/free-models.yml config/argus-config.schema.json config/argus.example.yml \
	           docs/argus-config-schema.md \
	           .github/actions/argus-review/action.yml \
	           .github/workflows/update-free-models.yml \
	           .github/workflows/pr-automation.yml \
	           tests/fixtures/README.md; do \
	    test -f "$$f" && echo "$$f ok" || (echo "$$f missing" && exit 1); \
	done
	@echo "── Validate: Python tool syntax ──"
	@python3 -m py_compile tools/run_fixture_tests.py && echo "run_fixture_tests.py ok"
	@python3 -m py_compile tools/load_config.py && echo "load_config.py ok"
	@python3 -m py_compile tools/update_free_models.py && echo "update_free_models.py ok"
	@python3 -m py_compile tools/validate_model_scores.py && echo "validate_model_scores.py ok"
	@python3 -m py_compile tools/check_release.py && echo "check_release.py ok"
	@python3 -m py_compile tools/publish_skillhub.py && echo "publish_skillhub.py ok"
	@python3 -m py_compile tools/validate_argus_schema.py && echo "validate_argus_schema.py ok"
	@echo "── Validate: free model list ──"
	@python3 tools/update_free_models.py --check
	@echo "── Validate: model-scores.yml schema ──"
	@python3 tools/validate_model_scores.py
	@echo "── Validate: load_config defaults ──"
	@python3 tools/load_config.py --validate-only
	@echo "── Validate: argus-config.schema.json + example config ──"
	@python3 tools/validate_argus_schema.py --check-schema
	@python3 tools/validate_argus_schema.py --config config/argus.example.yml
	@echo ""
	@echo "All validation checks passed ✓"

# ─── Config schema validation ────────────────────────────────────
.PHONY: validate-schema
validate-schema:
	@echo "── Validate: argus-config.schema.json (well-formed JSON) ──"
	@python3 tools/validate_argus_schema.py --check-schema
	@echo "── Validate: config/argus.example.yml conforms to schema ──"
	@python3 tools/validate_argus_schema.py --config config/argus.example.yml
	@echo "Config schema validation passed ✓"

# ─── Fixture regression tests ─────────────────────────────────────
.PHONY: test-fixtures
test-fixtures:
	@echo "── Fixture Tests (static heuristic mode) ──"
	@python3 tools/run_fixture_tests.py
	@echo ""

# Full mode: requires OpenCode CLI + configured model (primary resolved from
# config/free-models.yml at runtime by run_fixture_tests.py)
.PHONY: test-fixtures-llm
test-fixtures-llm:
	@echo "── Fixture Tests (LLM mode) ──"
	@python3 tools/run_fixture_tests.py $(if $(MODEL),--model $(MODEL)) $(if $(FALLBACK_MODELS),--fallback-models "$(FALLBACK_MODELS)")
	@echo ""

# ─── Combined pre-release check ──────────────────────────────────
.PHONY: test
test: validate test-fixtures
	@echo ""
	@echo "All checks passed — ready to release ✓"

# ─── Release ─────────────────────────────────────────────────────
.PHONY: release
release: validate
	@echo "── Release gate ──"
	@python3 tools/check_release.py --expect-unreleased
	@echo "── Verify version files are committed at HEAD ──"
	@git diff --quiet --exit-code -- VERSION CHANGELOG.md AGENTS.md SKILL.md manifest.yaml site/src/data/site.ts site/src/content/docs/index.md && git diff --cached --quiet --exit-code -- VERSION CHANGELOG.md AGENTS.md SKILL.md manifest.yaml site/src/data/site.ts site/src/content/docs/index.md || { echo "ERROR: version files have uncommitted changes — commit them first:"; echo "  git commit -m \"chore(release): prepare v$(VERSION)\""; exit 1; }
	@echo "── Verify local main is not behind origin/main ──"
	@git fetch -q origin main 2>/dev/null || true
	@if git rev-parse -q --verify origin/main >/dev/null 2>&1; then git merge-base --is-ancestor origin/main main || { echo "ERROR: local main is behind origin/main — pull first"; exit 1; }; fi
	@echo "── Creating annotated tag v$(VERSION) ──"
	@git tag -a "v$(VERSION)" -m "Argus v$(VERSION)"
	@echo "── Verifying tag content ──"
	@VER="$$(tr -d '\r\n ' < VERSION)"; TAGVER="$$(git show "v$$VER:VERSION" | tr -d '\r\n ')"; test "$$TAGVER" = "$$VER" || { echo "ERROR: tag v$$VER does not contain VERSION=$$VER — aborting"; git tag -d "v$$VER" >/dev/null; exit 1; }
	@echo "── Pushing main and tag ──"
	@git push origin main
	@git push origin "v$(VERSION)"
	@echo ""
	@echo "Released v$(VERSION) — GitHub Actions will create the Release page"

# ─── Skill Package ───────────────────────────────────────────────
.PHONY: package-skill
package-skill:
	@mkdir -p dist
	@rm -rf dist/_skill-staging
	@mkdir -p dist/_skill-staging
	@cp SKILL.md AGENTS.md manifest.yaml dist/_skill-staging/
	@cd dist/_skill-staging && zip -r ../argus-skill-v$(VERSION).zip .
	@rm -rf dist/_skill-staging
	@echo "Skill package: dist/argus-skill-v$(VERSION).zip"

# ─── Package ─────────────────────────────────────────────────────
.PHONY: package
package: package-skill
	@mkdir -p dist
	@tar --exclude='.git' --exclude='dist' \
	     --exclude='site/node_modules' --exclude='site/dist' --exclude='site/.astro' \
	     -czf dist/argus-v$(VERSION).tar.gz .
	@zip -q dist/argus-v$(VERSION).zip . -r \
	     -x '.git/*' -x 'dist/*' \
	     -x 'site/node_modules/*' -x 'site/dist/*' -x 'site/.astro/*'
	@echo "Packages created: dist/argus-skill-v$(VERSION).zip dist/argus-v$(VERSION).tar.gz dist/argus-v$(VERSION).zip"

# ─── SkillHub Publish Prep ───────────────────────────────────────
.PHONY: prepare-skillhub
prepare-skillhub: package-skill
	@python3 tools/publish_skillhub.py prepare dist/argus-skill-v$(VERSION).zip \
		--out dist/skillhub-argus \
		--changelog-out dist/skillhub-changelog.txt

# ─── Clean ───────────────────────────────────────────────────────
.PHONY: clean
clean:
	@rm -rf dist
	@echo "Cleaned"
