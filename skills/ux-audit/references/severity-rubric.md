# Severity Rubric

Use this to assign severity to every finding. The default severity hints in `laws-of-ux.md` and `wcag-21-AA.md` are starting points — override based on actual impact in this context.

## Levels

### P0 — Critical
Blocks task completion, causes data loss, creates legal/safety risk, or excludes a population entirely.
- Form cannot be submitted (validation broken)
- Required field invisible to screen readers (legally required form)
- Payment confirmation step missing (3.3.4 violation)
- Page unusable on mobile
- Auto-playing audio with no stop control (1.4.2)

### P1 — Major
Significantly degrades task completion, causes high friction, or affects a large portion of users.
- Primary CTA doesn't stand out (Von Restorff)
- Contrast fails on body text (1.4.3)
- Critical heading missing (2.4.6)
- Hick's Law violation on conversion page
- 5+ second delay with no loading state (Doherty)
- Inconsistent terminology between steps (3.2.4)

### P2 — Minor
Causes some friction or affects a smaller subset of users.
- Secondary CTA buried (Serial Position)
- Form label proximity issue (Law of Proximity)
- Inconsistent button styling on non-critical actions
- Missing autocomplete attributes (1.3.5)
- Subtle inconsistency in spacing/typography

### P3 — Polish
Refinement opportunity. Not affecting task completion.
- Aesthetic-Usability gap (looks dated but works)
- Minor visual hierarchy improvements
- Microcopy refinements
- Decorative inconsistencies

## Decision tree

```
Does the issue prevent task completion or cause legal/safety risk?
  YES → P0
  NO ↓
Does it significantly degrade conversion or exclude many users?
  YES → P1
  NO ↓
Does it cause some friction or affect a subset?
  YES → P2
  NO ↓
Is it a polish/refinement issue?
  YES → P3
```

## NSLS-specific calibration

For NSLS enrollment pages:
- Anything that affects FOL completion = P0 or P1 by default (this is the conversion event)
- Anything that affects credibility/prestige perception = P1 (audience-specific)
- Generic e-commerce best-practice violations may be P3 if they conflict with the Prestige-Polish Paradox (see `nsls-context.md`)
