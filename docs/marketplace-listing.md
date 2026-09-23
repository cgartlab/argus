# Argus GitHub Marketplace Listing — Prep & Checklist

> Status: DRAFT — pre-submission checklist for listing **argus-flash** on the
> GitHub Marketplace. GitHub reviews listings before they go live; complete
> everything below, then submit the listing for review.

## Why Marketplace

The Marketplace gives Argus three things the standalone App cannot:

1. **Discovery** — developers browsing "code review" in the Marketplace find it.
2. **Trust** — the Marketplace badge and review process are social proof.
3. **Billing** — GitHub handles plan subscriptions (free tier required, paid plans optional); no billing infrastructure on our side.

The install flow is the same App (`github.com/apps/argus-flash`) — Marketplace adds
the listing, plans, and billing around it. The composite action
(`cgartlab/argus/.github/actions/argus-review@main`) is referenced from the
consumer repo's `review.yml` exactly as it is today.

## Pre-Flight

- [ ] `argus-flash` App is **public** and in good standing (`github.com/apps/argus-flash`)
- [ ] Marketing site (`site/`, https://argus.cgartlab.com) is live with docs + a features page
- [ ] README has accurate badges and install instructions
- [ ] `NOTICE` trademark declarations up to date
- [ ] A `review.yml` template is documented so buyers can activate within minutes
- [ ] Quality metrics story ready to publish (fixture suite + precision/recall gates — see `tools/eval_quality.py`)

## App Configuration (Settings → Developer settings → GitHub Apps → argus-flash)

### Permissions (least privilege, must match what the action does)

| Scope | Permission | Why |
|---|---|---|
| Actions | read | workflow runs |
| Checks | write | status checks from the review |
| Contents | read | read repo files for review |
| Issues | write | comment findings |
| Pull requests | write | PR comments/reviews |
| Metadata | read | repo metadata (always granted) |
| Workflows | write | optional: commit workflow updates |

- [ ] Webhooks configured for the events the review pipeline needs (e.g. pull_request)
- [ ] No unused broad scopes (least privilege is part of the review)

### Marketplace listing content (draft)

- **Name:** Argus — Frontend Design Review
- **Slug:** `argus-flash`
- **Summary (one line):** Automated frontend design code review — tokens, dark mode, a11y, copy-ready fixes.
- **Description:** Argus is a cross-platform AI coding agent specialized in frontend design code review. It catches hardcoded values, design-token violations, dark-mode breaks, and accessibility gaps, and provides copy-ready code fixes. Install it, add a minimal `review.yml`, and every PR gets a full design review driven by `AGENTS.md` + `SKILL.md` (rules updated at runtime — no version lock).
- **Category:** Code review / Developer tools
- **Logo:** 128×128 (required), on transparent background
- **Screenshots:** 5 screenshots (1280×800) — install flow, review.yml, a PR review comment, a design-token fix, the compliance report (`argus_report.py --wcag`)
- **Support URL:** https://argus.cgartlab.com
- **Pricing plan URL:** https://github.com/marketplace/argus-flash (auto)

### Pricing plans (from the commercial strategy plan, §6)

GitHub Marketplace requires a **free plan** and bills paid plans through the
Marketplace.

| Plan | Price | Includes | Notes |
|---|---|---|---|
| **Community** | Free | GitHub App review on public repos; static + free-model queue; single-repo `.argus.yml` | Always free — free-model cost structure keeps this sustainable |
| **Pro** | $20–29/seat/mo or $99/repo/mo | Private-repo scale, team multi-repo config, shareable HTML/compliance reports, model selection | Report links (`argus_report.py`) are the upgrade hook |
| **Enterprise** | Custom (≥ $1k/mo) | SSO, self-hosting (see `docs/self-hosting.md`), WCAG compliance reporting, SLA | Compliance-driven |

- [ ] Plans created in App settings (free plan first, then paid)
- [ ] "Billing" pricing tier text reviewed

## Submit for Review

1. In the App settings, open **Marketplace → Public listing** and fill every required field.
2. Mark the listing **Draft**, run the internal checklist above.
3. Submit the listing — GitHub Marketplace review typically takes days to a couple of weeks.
4. While waiting: prepare the release notes / changelog and the Pro hook (report links) so the first paid plan has its upsell ready.

## Go-Live Checklist

- [ ] Listing approved and published
- [ ] Install test on a fresh public repo (Marketplace install → review.yml → PR review)
- [ ] README + site updated with "Available on GitHub Marketplace" badge
- [ ] Announce (DevRel post / changelog entry)
- [ ] Monitor install activation (7-day first-review rate) and FP feedback for the quality loop

## References

- GitHub Marketplace docs: <https://docs.github.com/en/apps/github-marketplace>
- Pricing plans for Marketplace apps: <https://docs.github.com/en/apps/github-marketplace/selling-your-app-on-github-marketplace/pricing-plans-for-github-marketplace-apps>
- Marketplace listing review: <https://docs.github.com/en/apps/github-marketplace/using-the-github-marketplace-api-in-your-app>