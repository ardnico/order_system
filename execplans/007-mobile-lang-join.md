# Mobile nav, Japanese default language, and join code reliability

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintain the plan in accordance with .agent/PLANS.md.

## Purpose / Big Picture

Users reported three gaps: on phones the top navigation consumes too much vertical space, the app still defaults to English instead of Japanese, and joining a household sometimes rejects a correct join code. The goal is to make the mobile navigation compact with an explicit toggle, switch the default language to Japanese for new and anonymous sessions, and make join code validation robust so valid codes work reliably.

## Progress

- [x] (2025-02-06 00:25Z) Drafted ExecPlan describing goals, scope, and steps.
- [x] (2025-02-06 00:45Z) Implemented mobile navigation toggle and compact styling for small screens.
- [x] (2025-02-06 00:46Z) Switched default language to Japanese for new sessions and households.
- [x] (2025-02-06 00:47Z) Hardened join code comparison to accept correct codes consistently.
- [x] (2025-02-06 00:56Z) Ran tests and updated plan notes.

## Surprises & Discoveries

- None encountered; changes behaved as expected.

## Decision Log

- Decision: Use a collapsible nav controlled by a button on narrow screens instead of always stacking links to reduce header height.
  Rationale: Keeps all links reachable while minimizing space on phones.
  Date/Author: 2025-02-06 / assistant

## Outcomes & Retrospective

Navigation now collapses cleanly on mobile, reducing header height while keeping links accessible. Japanese is the default langu
age for new households and sessions without existing preferences. Join code comparison now trims and lowercases input to avoid 
false negatives. All tests pass, and no regressions were observed.

## Context and Orientation

The FastAPI app lives in `app/main.py` with request handlers, language selection helpers, and household registration. UI templates are under `app/templates/` with `base.html` defining the shared header and navigation. Styles are in `app/static/style.css`. The `Household` model in `app/models.py` defines defaults including language. Registration and join validation are handled in `/register` handlers in `app/main.py`.

## Plan of Work

Edit `app/templates/base.html` to wrap the nav in a container with a toggle button that collapses links on small screens while keeping desktop layout unchanged. Update `app/static/style.css` with responsive styles that hide the nav links by default on small viewports, show a menu toggle, reduce padding, and allow horizontal scrolling if needed. Switch default language handling by changing the fallback in `get_language` and the `Household.language` default in `app/models.py` to Japanese. Make join code validation more forgiving by normalizing whitespace and case before comparison when joining existing households in `app/main.py`.

## Concrete Steps

Working directory: repository root.

1. Update `app/templates/base.html` to introduce a nav wrapper and toggle button for mobile. Add minimal JavaScript to toggle a CSS class on the nav.
2. Adjust `app/static/style.css` with responsive rules: show the toggle only on small screens, keep nav hidden until toggled, reduce padding/font size for nav links on mobile, and ensure overflow handling so the header stays compact.
3. Set the language default to Japanese by updating `Household.language` default in `app/models.py` and the fallback in `get_language` within `app/main.py`.
4. Normalize join code input by trimming and lowercasing user input (and stored codes for comparison) in the `/register` POST handler when joining existing households.
5. Run `pytest` to confirm no regressions.
6. Update this plan’s Progress, Surprises, Decision Log (if needed), and Outcomes sections to reflect completed work and observations.

## Validation and Acceptance

- On a small viewport, the header should show a compact brand with a menu toggle; tapping the toggle reveals nav links without occupying the full viewport. On desktop, nav remains always visible with unchanged layout.
- Fresh sessions without a stored language should load Japanese strings by default; new households should store Japanese as their default language.
- Joining an existing household with the correct join code (ignoring case and stray spaces) succeeds; incorrect codes still reject.
- `pytest` passes.

## Idempotence and Recovery

CSS and template changes are additive and safe to reapply. Language defaults are applied when values are missing; existing households with a set language remain unchanged. Join code normalization only affects comparison; data is not mutated. If issues arise, revert the modified files via version control.

## Artifacts and Notes

None yet.

## Interfaces and Dependencies

No new external dependencies. Changes rely on existing FastAPI routes, Jinja templates, and CSS. The join code comparison will use standard Python string methods.
