# Changelog

All notable source-quality changes to this repository are documented here.

## v0.1.4 - 2026-09-26

- Make the privacy/test workflow run explicitly for `v*` release tags so source releases validate the same percentage-only data contract as `main` pushes.
- Add repository-contract coverage for release-tag CI wiring.

## v0.1.3 - 2026-09-24

- Add release-history documentation and repository contract checks for required project files, local README links, GitHub Actions coverage, public-data privacy shape, and release-history links.

## v0.1.2 - 2026-09-24

- Fix manual-entry output so public indexed-equity JSON strips raw dollar balances from chart points.
- Add regression coverage for percentage-only public JSON publication.

## v0.1.1 - 2026-09-23

- Fix stale Schwab workflow setup guidance so credentials-missing messages point to the current developer reference.
- Add regression coverage to keep workflow documentation links accurate.

## v0.1.0 - 2026-09-23

- Redact Schwab token response values from automated update logs.
- Avoid printing rotated refresh tokens in public CI logs.
- Add regression tests for token-log redaction.
