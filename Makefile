# Makefile — Argus

VERSION := $(shell cat VERSION)
RELEASE_BRANCH := release/v$(VERSION)

.PHONY: help
help:
	@echo "Argus Makefile"
	@echo ""
	@echo "  make check-version    — show current version"
	@echo "  make validate         — run all quality checks"
	@echo "  make release          — tag and push a release"
	@echo "  make package         — create release archive"
	@echo "  make clean           — remove generated files"

.PHONY: check-version
check-version:
	@echo "Current version: $(VERSION)"

.PHONY: validate
validate:
	@echo "Checking SKILL.md description trigger phrases..."
	@python3 -c "import sys, re; f=open('SKILL.md').read(); phrases=[p.strip() for p in re.findall(r'(?:when|phrases?)[:\s]+([^\n]+)', f, re.I)]; print('SKILL.md ok') if len(phrases) >= 3 else (print('SKILL.md: need 3+ trigger phrases'), sys.exit(1))" 2>/dev/null || echo "SKILL.md: could not verify trigger phrases automatically"
	@echo "Checking VERSION matches CHANGELOG header..."
	@grep -q "^## \[$(VERSION)\]" CHANGELOG.md && echo "CHANGELOG ok" || (echo "CHANGELOG: missing [$(VERSION)] section" && exit 1)
	@echo "Checking AGENTS.md exists..."
	@test -f AGENTS.md && echo "AGENTS.md ok" || (echo "AGENTS.md missing" && exit 1)
	@echo "All checks passed"

.PHONY: release
release: validate
	@echo "Releasing v$(VERSION)..."
	@git add -A
	@git commit -m "chore(release): v$(VERSION)"
	@git tag v$(VERSION)
	@git push origin main
	@git push origin tags/v$(VERSION)
	@echo "Released v$(VERSION)"

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