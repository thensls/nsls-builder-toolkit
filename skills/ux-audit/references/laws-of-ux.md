# Laws of UX Reference

21 laws across heuristics, Gestalt principles, cognitive bias, and additional principles. Use these as audit lenses — each law gives you 1–3 questions to ask of the artifact.

**Severity hints** are defaults; override based on actual impact. See `severity-rubric.md`.

## Heuristics

### 1. Aesthetic-Usability Effect
*Polished designs feel more usable, even when they aren't.*
- Does the design appear polished and intentional?
- **Watch for:** polish masking real issues. Audit usability *as if* the polish weren't there.
- Default severity: P3 (when polish is the only positive)

### 2. Fitts's Law
*Targets that are larger and closer are faster to hit.*
- Are primary CTAs ≥44×44 px (touch) or ≥24×24 (WCAG 2.2 minimum)?
- Are critical targets in easy-reach zones (mobile: bottom; desktop: F-pattern)?
- Are tiny click targets near each other (mis-click risk)?
- Default severity: P1 if primary CTA fails; P2 otherwise

### 3. Goal-Gradient Effect
*Motivation increases as users approach completion.*
- Is progress visible (steps, progress bar, "X of Y")?
- Does the user know how close they are to done?
- Default severity: P2 in multi-step flows

### 4. Hick's Law
*More options = slower decision.*
- How many primary actions are competing for attention?
- Are options grouped, prioritized, or progressively disclosed?
- Default severity: P1 on conversion-critical pages

### 5. Jakob's Law
*Users expect your site to work like other sites they know.*
- Do conventions match the category (logo top-left → home, etc.)?
- Are familiar patterns implemented as expected?
- Are you reinventing for novelty's sake?
- Default severity: P1 when violation breaks task completion

### 6. Miller's Law
*Working memory holds ~7±2 items.*
- Are info chunks ≤5–9 items per group?
- Is content broken into digestible sections?
- Default severity: P2

### 7. Parkinson's Law
*Tasks expand to fill the time given.*
- Are tasks expedited (autofill, smart defaults, minimal fields)?
- Does the design make tasks feel faster than expected?
- Default severity: P2

## Gestalt Principles

### 8. Law of Common Region
*Elements in a shared visible region are seen as grouped.*
- Are related elements grouped by cards, sections, or backgrounds?
- Does grouping match actual semantic relationships?
- Default severity: P2

### 9. Law of Proximity
*Closer elements are seen as related.*
- Are labels close to their inputs?
- Are related actions close, unrelated actions separated?
- Is whitespace separating distinct groups?
- Default severity: P2 (P1 if proximity misleads in a form)

### 10. Law of Prägnanz
*The brain interprets ambiguous shapes as the simplest possible form.*
- Are CTA shapes simple and unambiguous?
- Is iconography clear without labels?
- Default severity: P3

### 11. Law of Similarity
*Things that look similar are seen as related.*
- Do similar functions look similar (all links styled alike)?
- Are visual differences meaningful (not arbitrary)?
- Default severity: P2

### 12. Law of Uniform Connectedness
*Visually connected elements are seen as a group.*
- Are connected elements unified (lines, frames, shared backgrounds)?
- Default severity: P3

## Cognitive Bias

### 13. Peak-End Rule
*Experiences are remembered by their peak and their end.*
- What is the most memorable moment in this flow?
- How does the experience end? Is the ending memorable in a good way?
- Default severity: P1 (high leverage — small fixes, big perceived improvement)

### 14. Serial Position Effect
*First and last items are remembered most.*
- Are the most important elements first or last in sequence?
- Are critical items hidden in the middle of a list?
- Default severity: P2

### 15. Von Restorff Effect
*The thing that stands out is remembered.*
- Does the primary CTA stand out?
- Are non-essential elements competing for attention?
- Default severity: P1 if primary CTA doesn't stand out

### 16. Zeigarnik Effect
*Incomplete tasks linger in memory.*
- Are incomplete tasks made visible (saved progress, draft indicators)?
- Default severity: P2

## Additional Principles

### 17. Doherty Threshold
*Users expect responses within 400ms.*
- Is feedback to actions <400ms (or has loading state)?
- Are loading states acknowledged immediately?
- Default severity: P1

### 18. Occam's Razor
*The simplest solution is best.*
- Does every element earn its place?
- What could be removed without losing function?
- Default severity: P2

### 19. Pareto Principle
*80% of effects come from 20% of causes.*
- What 20% of issues will fix 80% of pain?
- This is a meta-principle for prioritizing the report itself.

### 20. Postel's Law
*Be liberal in what you accept, strict in what you require.*
- Does the form accept varied input formats (UK / United Kingdom; 555-1234 / 5551234)?
- Is validation lenient where appropriate?
- Default severity: P1 in forms

### 21. Tesler's Law
*Every system has a minimum complexity that can't be designed away.*
- Where is intrinsic complexity unavoidable?
- Has the design over-simplified to the point of breaking function?
- Default severity: P2 if over-simplification causes friction
