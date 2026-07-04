# Onboarding Playbook — methodology for Welcome-track (and any onboarding) work

Read this BEFORE proposing any change to the Welcome track — it is the app's
onboarding, and onboarding follows different rules than mid-journey tracks.
Compiled 2026-07-04 from (a) *Product-Led Onboarding* (Ramli John) — summary
doc linked on the Welcome track's Studio page under Context & references — and
(b) a deep-research sweep of 2023–2026 B2C onboarding evidence (23 sources,
25 claims adversarially verified 3-vote, 24 confirmed / 1 refuted). Claims
below carry their evidence grade; don't quote a "medium/blog" figure as fact.

## 1. The activation architecture: three moments, defined backward

Both the book and the Reforge activation canon (Chen/Balfour) converge on the
same skeleton — a member is not "onboarded" at any single event:

| Moment | Book's name | Welcome-track mapping | Instrument |
|---|---|---|---|
| **Setup** | Moment of Value *Perception* | Completing the wheels + needs + profile | Welcome completion (substep funnel) |
| **Aha** | Moment of Value *Realization* | The segment reveal / first personally-relevant payoff | Reveal reached + day-2 return |
| **Habit** | Moment of Value *Adoption* | Week-1 return loop, multi-track usage | Day-7 return, 4+ active days |

Work **backward from the habit moment**: decide what habitual use looks like,
find the aha that predicts it, and only then design the setup path to it.
(Reforge, secondary, 3-0 verified.)

Two strategic corollaries, both verified:
- Activation improvements lift the *early steep part* of the retention curve
  and shift whole cohorts up — activation is the highest-impact retention
  lever **only when the retention curve already flattens**. Check the
  app-wide curve before betting everything on onboarding.
- **Duolingo's caution** (first-person CPO account, verified): their DAU
  sensitivity model found retaining existing daily users (CURR) had ~5× the
  impact of any new-user metric; they got 4.5× DAU largely from habit loops
  (leaderboards: +17% learning time, 3× highly-engaged learners). Once
  Welcome is decent, the bigger lever may be week-1 loops, not more funnel
  polish. (Company-specific; a young app can see the opposite ranking.)

## 2. EUREKA mapped to NSLS machinery

The book's six-step loop is already mostly built here — use the existing
machinery, don't invent parallel process:

| EUREKA step | NSLS implementation |
|---|---|
| **E**stablish the team | Society Studio is the shared surface; owner on the Tracks row |
| **U**nderstand desired outcomes | Segments (clarity×confidence) + stated-needs data (`/audience`), JTBD per segment in `segment-lens.md` |
| **R**efine success milestones | Setup/aha/habit table above; pre-registered metrics in the `Hypotheses` table |
| **E**valuate the path | Substep funnel from `substep_save_result` (per-substep reach = quit-probability curve); Bowling-Alley the straightest path to the aha |
| **K**eep users engaged | Fogg B=MAP: prompts at the right moment, ability high (defaults, templates, empty-state guidance), motivation via progress + celebration |
| **A**pply and repeat | Small pre-registered experiments over big-bang redesigns — the Hypotheses loop IS this step |

## 3. Verified benchmarks (match the definition before comparing!)

All vendor data; populations differ — the biggest trap in this table is
comparing your number to the wrong denominator.

| Metric | Benchmark | Source/grade |
|---|---|---|
| Day-2 return (next-day) | ~5% median, ~21% = top decile (cross-industry, all new users, Amplitude 2,600+ cos) | primary PDF, high |
| Day-2 return (mobile installs) | ~16% baseline; 20% with onboarding campaigns; category medians 24–27% | Airship/eMarketer, high |
| Day-7 return | ≥7% of cohort returning on day 7 = top quartile; 69% of top day-7 performers are still top performers at 3 months | Amplitude primary, high |
| Month-1 / month-3 (monthly-cohort def.) | top decile 26% / 18.5%; median 6.5% / 3.8% (median product loses 96% by month 3) | Amplitude primary, high |

**Welcome's own baselines (2026-07-04, current era since 2026-05-19,
n=1,350 starters — point-in-time, re-pull before use):** completion 76.8%,
day-2 return 44.1%, wheel reach 84% (intro screens lose 16% pre-wheel).
Note 44.1% day-2 is far above the install benchmarks because our denominator
is *track starters inside a membership product*, not cold installs — another
reason to only compare like-for-like and to trend against ourselves.

**Definitional discipline (Mixpanel docs, verified):** every day-N number
must state (a) the birth event (track start vs completion), (b) the return
event, (c) the criterion — "On" (exactly day N) vs "On or After" (day N or
later; Mixpanel's default, always reads higher). State all three on every
hypothesis and benchmark comparison. Recent cohorts are right-censored for
multi-day metrics — day-2 reads fast, 4+/7+ day metrics need the window to
mature before judging.

## 4. Psychology toolbox — what's actually verified

Ranked by evidence strength; the moderators are the design guidance.

1. **Endowed progress** (peer-reviewed, field-experimental, high). Artificial
   head-start progress raises completion likelihood AND speed — 10-stamp card
   with 2 pre-stamped beat an identical 8-stamp card, 34% vs 19% redemption
   (~+79% relative). **Moderator: the effect disappears without a stated
   reason for the head start.** Application: Welcome's progress bar should
   count signup/account creation as steps already done, with a framing line
   ("you earned this by joining").
2. **IKEA effect with a hard completion boundary** (peer-reviewed, high).
   Effort raises valuation (~63% higher bids for self-assembled boxes) — but
   ONLY if the labor completes: builders stopped short of finishing bid ~60%
   LESS than finishers. Application: the wheels/checklists are effort
   investments that pay off only if every member reaches the finished payoff
   (reveal + plan). An abandoned flow converts invested effort into negative
   value — completion-rate engineering on the payoff path is not optional,
   and the payoff must never sit behind a failure-prone step.
3. **Reciprocity / question placement** (blog-grade, 2-1 vote — directional
   only). Unframed asks (permissions, demographics) before any value delivery
   degrade the experience; quiz-heavy funnels work when questions are framed
   as personalization the user benefits from ("so we can build YOUR plan").
   Application: personalization-framed questions may lead; hard asks
   (notifications, demographics) come after the reveal or made skippable.
   The specific quiz-first completion/retention numbers circulating for
   Duolingo/Noom-style funnels did NOT survive verification — don't cite them.
4. **Labeling effect — CONTESTED, do not assume** (peer-reviewed nulls,
   high confidence in the *caution*). Large pre-registered replications found
   no effect of identity-labeling wording ("be a voter" vs "vote"); the
   literature is an unresolved replication fight. Application: build the
   segment reveal as **tangible value delivery** — a personalized diagnosis
   plus next steps that visibly use the member's own answers — not as
   identity priming. Measure the reveal with a holdout; never assume lift
   from the label itself. (Reinforces the standing rule: stage, not identity;
   internal segment names never member-facing.)

## 5. Welcome-specific rules of thumb

- **Day-One win**: the first session must end with the member having
  *received* something (the reveal, a real grounded stat, a plan) — not
  merely having given data.
- **Bowling Alley**: one straightest path to the aha; defer everything else
  (tours, secondary features, optional profile fields) to later cycles.
- **Survivorship guardrail** (from `segment-lens.md`, still binding): Welcome
  per-segment metrics are tautological — the wheels assign segments. Measure
  Welcome on all-starter numbers.
- **Satisfaction without the survivor trap**: hazard curves from
  `substep_save_result`, sampled pulses, rating deltas — never end-of-track
  ratings alone.
- **Every change ships as a pre-registered hypothesis** (Hypotheses table:
  baseline with n, prediction from X to Y by when, exact measure_query,
  window_end). Small frequent experiments beat redesigns — and a refuted
  prediction is a finding.

## 6. Anti-patterns

- Feature tours as onboarding (touring ≠ succeeding; show *their* progress,
  not your features).
- Collecting data the first session never uses (violates the
  reciprocity/IKEA logic above — every answer should visibly shape the payoff).
- Comparing day-N numbers across different denominators, birth events, or
  On/On-or-After criteria.
- Judging a fresh cohort's 4+/7+ day metrics before the window matures
  (right-censoring reads as decline).
- Quoting the refuted loose "7% rule" ("7% day-7 = demonstrated value") —
  only the top-quartile framing (§3) is supported.
- Assuming the segment label itself moves behavior (§4.4) — the payoff does
  the work, the label is packaging.

## 7. Known gaps (tested in-house or not at all)

The sweep found NO surviving external evidence on: question-count tolerance
and per-question skip rates; survey placement before vs after value
explanation (A/B-grade); optimal onboarding length; progressive profiling;
streak/notification ethics and effectiveness for our category. These are
exactly what our own pre-registered experiments must answer — the
wheel-up-front hypothesis (logged 2026-07-04, day-2 return 44.1% → ≥48%) is
the first; a reveal-vs-no-label holdout is the highest-value second.

## Sources (verified set)

Amplitude Product Benchmark Report 2025 (primary PDF) · Mixpanel retention
docs (primary) · Nunes & Drèze 2006 JCR (endowed progress, primary) · Norton,
Mochon & Ariely 2012 JCP (IKEA effect, primary) · Gerber, Huber & Fang 2018
Political Psychology (labeling null, primary) · Mazal, "How Duolingo reignited
user growth" (Lenny's, first-person primary) · Reforge activation guides
(secondary) · Airship via eMarketer (secondary) · growth.design Headspace
teardown (blog, 2-1) · *Product-Led Onboarding*, Ramli John (book summary doc
on the Welcome track's Studio page).
