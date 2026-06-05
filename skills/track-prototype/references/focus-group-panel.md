# Focus-Group Panel & Anti-Groupthink Protocol

How the Phase-2 panel evaluates a rendered track. The **staged flow is load-bearing** — it exists to fight the documented failure modes of synthetic panels (sycophancy, groupthink, and a systematic *over*-statement of adoption). Do not collapse the stages for speed.

Input: the screenshot gallery + `report.json` from `walk-gallery.mjs` (the panel judges the **rendered run-through**, including live `generate`/`chat` output — not `track.json`).

## The panel

**Member personas** — reuse `references/member-personas.md` (5 registers + 2 edge personas: anxious first-gen student, skeptical returning member). Give the edge personas explicit weight.

**Four experts** (synthesis + scoring):
- **UX Designer** — cognitive load, pacing, interaction clarity, peak-end.
- **Educational Designer** — does the learning land; scaffolding; is the deliverable real.
- **Copywriter** — voice, tone, Society brand fit, resonance.
- **Product/Engagement Strategist** — adoption/retention mechanics, value-promise strength, predicted drop-off.

**Adversarial skeptic** — one designated voice whose only job is to argue the track will *fail*.

## The staged flow

1. **Stage 1 — Personas react INDEPENDENTLY.** Each persona, in its **own isolated context** (not a shared thread, never seeing another persona), walks the screenshots and emits structured reactions (`schemas/persona-reaction.json`). **Warm temperature (~0.7–1.0)** to preserve diversity. Edge personas get explicit weight. Personas must speak with authentic skepticism/friction — do NOT sanitize.

2. **Stage 2 — Experts score BLIND.** Each of the 4 experts **independently** scores all 16 sub-checks from the run-through, **3 samples each at low temp (~0.1)**, **justification-before-verdict**, **citing the specific screen** as evidence (`schemas/expert-verdict.json`). They do NOT see the personas or each other. Instruct them to **ignore verbosity/length** (longer copy ≠ better).

3. **Stage 3 — Experts revise INFORMED.** Experts now see the **aggregated, anonymized** persona reactions (a distribution, not "Sofia said X") and may revise, stating what changed and why.

4. **Stage 4 — Adversarial pass.** The skeptic argues each dimension is over-scored and surfaces the abandonment / negative-lived-experience case the others omit. Experts respond. This counteracts the upward adoption bias of synthetic personas.

5. **Stage 5 — Aggregate** (code: `scorecard.mjs`). Per sub-check, take the median across all expert samples → MET/UNMET/CONTESTED → dimension rollup → checks-met total → ship-bar.

## Anti-groupthink rules (encode these)

- **Independent commitment before any shared visibility** (Stages 1 and 2 are blind).
- **Only aggregated/anonymized cross-agent visibility** (Stage 3) — never feed one agent another's verbatim output.
- **Mandatory contrarian** (Stage 4) — no convergence until the skeptic's objections are registered.
- **Randomize** the order sub-checks/personas are presented (position bias).
- **Use a different model family for the judges than for any generated track copy** (self-preference bias) where feasible.
- **Report the spread, not just the median** — a CONTESTED / high-dispersion sub-check is a low-confidence signal routed to human review, regardless of the median.

## Orchestration note

Run personas as parallel sub-agents in isolated contexts (warm temp); run each expert's 3 samples at low temp. The structured outputs (below) feed `scorecard.mjs` directly. Keep it staged — the value is in the independence, not the conversation.
