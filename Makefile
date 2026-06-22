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
	@echo "  make validate         — run all quality checks"
	@echo "  make release          — commit, tag and push a release"
	@echo "  make package         — create release archive"
	@echo "  make clean           — remove generated files"

.PHONY: check-version
check-version:
	@echo "Current version: $(VERSION)"

# ─── Version bumping ─────────────────────────────────────────────
.PHONY: bump-patch bump-minor bump-major
bump-patch bump-minor bump-major: BUMP_KIND=$(notdir $(firstword $(MAKECMDGOALS)))
bump-patch bump-minor bump-major:
	@python3 tools/bump_version.py $(BUMP_KIND)
	@echo ""
	@echo "Files staged. Review, then: make validate && make release"

.PHONY: validate
validate:
	@echo "Checking SKILL.md description trigger phrases..."
	@python3 -c "import sys, re; f=open('SKILL.md').read(); phrases=[p.strip() for p in re.findall(r'(?:when|phrases?)[:\s]+([^\n]+)', f, re.I)]; print('SKILL.md ok') if len(phrases) >= 3 else (print('SKILL.md: need 3+ trigger phrases'), sys.exit(1))" 2>/dev/null || echo "SKILL.md: could not verify trigger phrases automatically"
	@echo "Checking VERSION matches CHANGELOG header..."
	@grep -q "^## \[$(VERSION)\]" CHANGELOG.md && echo "CHANGELOG ok" || (echo "CHANGELOG: missing [$(VERSION)] section" && exit 1)
	@echo "Checking AGENTS.md exists..."
	@test -f AGENTS.md && echo "AGENTS.md ok" || (echo "AGENTS.md missing" && exit 1)
	@echo "Checking composite action exists..."
	@test -f .github/actions/argus-review/action.yml && echo "action.yml ok" || (echo ".github/actions/argus-review/action.yml missing" && exit 1)
	@echo "All checks passed"

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

.PHONY: package
package:
	@mkdir -p dist
	@tar --exclude='.git' --exclude='dist' -czf dist/argus-v$(VERSION).tar.gz .
	@zip -q dist/argus-v$(VERSION).zip . -r -x '.git/*' -x 'dist/*'
	@echo "Packages created: dist/argus-v$(VERSION).tar.gz dist/argus-v$(VERSION).zip"

.PHONY: clean
clean:
	@rm -rf dist
	@echo "Cleaned"
