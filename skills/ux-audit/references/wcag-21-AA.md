# WCAG 2.1 A + AA Reference

50 success criteria — 30 at Level A, 20 at Level AA. Skip AAA by default.

**Auditable** column shorthand:
- **U** = URL/HTML (programmatic + visual)
- **F** = Figma frame (visual + design tokens)
- **S** = Screenshot (visual only)
- **N** = Not auditable from any static input — flag for prototype/live testing

## High-yield criteria (audit these first on every page)

These are violated most often on enrollment/marketing pages and have the highest user impact.

### 1.1.1 Non-text Content (A) — U,F,S
Every image, icon, and non-text element has a text alternative serving equivalent purpose. Decorative images marked `alt=""` or `aria-hidden="true"`.
- **Check:** Look for `<img>` without `alt`, decorative images with descriptive alt, icon buttons without `aria-label`.

### 1.4.3 Contrast (Minimum) (AA) — U,F,S
Text contrast ≥4.5:1 normal, ≥3:1 for large text (≥18pt or ≥14pt bold).
- **Check:** Use design token values; verify against background. Pay attention to placeholder text, secondary text, links over images, button text.

### 1.4.11 Non-text Contrast (AA) — U,F,S
UI component boundaries and graphical objects ≥3:1 against adjacent colors.
- **Check:** Form field borders, focus indicators, icon graphics, chart elements.

### 2.4.7 Focus Visible (AA) — N (must test live)
Keyboard focus indicator visible.
- **Check:** Tab through the page. Look for `outline: none` without replacement.
- **Mark "not auditable from this input" for static reviews.**

### 2.4.6 Headings and Labels (AA) — U,F,S
Headings and labels describe topic or purpose.
- **Check:** Generic labels ("Click here", "Submit"), missing heading hierarchy, headings used for styling.

### 3.3.2 Labels or Instructions (A) — U,F,S
Form inputs have labels or instructions.
- **Check:** Inputs relying on placeholder-only labels, ambiguous fields, missing format hints (e.g., date format).

### 4.1.2 Name, Role, Value (A) — U
Custom controls expose name, role, value programmatically.
- **Check:** `<div onclick>` masquerading as buttons, custom dropdowns without ARIA, toggles without state.

## Full A + AA criteria

### Perceivable

| Criterion | Level | Audit | Auditable | Quick check |
|---|---|---|---|---|
| 1.1.1 Non-text Content | A | All non-text has text alt | U,F,S | See above |
| 1.2.1 Audio/Video-only (Pre) | A | Transcript or audio track | U | Look for transcript link near media |
| 1.2.2 Captions (Pre) | A | Captions for prerecorded audio | U | Inspect video for `<track>` |
| 1.2.3 Audio Description (Pre) | A | Audio description or alt | U | Check video metadata |
| 1.2.4 Captions (Live) | AA | Captions for live audio | U | Live streams only |
| 1.2.5 Audio Description (Pre) | AA | Audio description for video | U | Check video metadata |
| 1.3.1 Info and Relationships | A | Structure programmatic | U | Headings nest correctly, lists use `<ul>/<ol>`, tables have `<th>` |
| 1.3.2 Meaningful Sequence | A | Reading order preserves meaning | U,F | DOM order matches visual order |
| 1.3.3 Sensory Characteristics | A | Don't rely on shape/color/sound alone | U,F,S | "Click the green button" + label |
| 1.3.4 Orientation | AA | Works portrait + landscape | U,F | No `orientation: portrait` lock |
| 1.3.5 Identify Input Purpose | AA | Inputs use autocomplete tokens | U | `<input autocomplete="email">` etc. |
| 1.4.1 Use of Color | A | Color not sole conveyor | U,F,S | Required fields marked with text + color |
| 1.4.2 Audio Control | A | Auto audio >3s has stop control | U | Auto-playing media has controls |
| 1.4.3 Contrast (Min) | AA | 4.5:1 normal, 3:1 large | U,F,S | See above |
| 1.4.4 Resize Text | AA | 200% zoom no loss | U | Test zoom |
| 1.4.5 Images of Text | AA | Use real text, not images of text | U,F,S | Marketing banners often violate |
| 1.4.10 Reflow | AA | 320px width no horizontal scroll | U,F | Mobile reflow test |
| 1.4.11 Non-text Contrast | AA | UI components 3:1 | U,F,S | See above |
| 1.4.12 Text Spacing | AA | Survives spacing overrides | U | Test with bookmarklet |
| 1.4.13 Content on Hover/Focus | AA | Tooltips dismissible/hoverable/persistent | N (mostly) | Static review limited |

### Operable

| Criterion | Level | Audit | Auditable | Quick check |
|---|---|---|---|---|
| 2.1.1 Keyboard | A | All function via keyboard | N | Live test required |
| 2.1.2 No Keyboard Trap | A | Focus can leave any component | N | Live test required |
| 2.1.4 Char Key Shortcuts | A | Single-char shortcuts have escape | U | Code review |
| 2.2.1 Timing Adjustable | A | Time limits adjustable | U | Sessions, idle timeouts |
| 2.2.2 Pause, Stop, Hide | A | Auto-moving content controllable | U | Carousels, auto-rotators |
| 2.3.1 Three Flashes | A | No flashing >3/sec | U,F | Animation review |
| 2.4.1 Bypass Blocks | A | Skip nav available | U | Look for skip link |
| 2.4.2 Page Titled | A | `<title>` describes purpose | U | Check `<title>` |
| 2.4.3 Focus Order | A | Sequential focus preserves meaning | N | Live test required |
| 2.4.4 Link Purpose (Context) | A | Link purpose clear from text + context | U,F,S | "Click here", "Read more" |
| 2.4.5 Multiple Ways | AA | Multiple navigation methods | U | Search, sitemap, nav |
| 2.4.6 Headings and Labels | AA | Descriptive | U,F,S | See above |
| 2.4.7 Focus Visible | AA | Visible focus indicator | N | Live test |
| 2.5.1 Pointer Gestures | A | Multipoint gestures have alt | U,F | Maps, swipe-only carousels |
| 2.5.2 Pointer Cancellation | A | Down-event not the trigger | U | Code review |
| 2.5.3 Label in Name | A | Visible label = accessible name | U,F | Visible "Send" but `aria-label="Submit form"` is a violation |
| 2.5.4 Motion Actuation | A | Motion-triggered also has UI | U | Shake-to-undo etc. |

### Understandable

| Criterion | Level | Audit | Auditable | Quick check |
|---|---|---|---|---|
| 3.1.1 Language of Page | A | `lang` attr set | U | Check `<html lang>` |
| 3.1.2 Language of Parts | AA | Inline language changes marked | U | Foreign words wrapped with `lang` |
| 3.2.1 On Focus | A | Focus doesn't change context | N | Live test |
| 3.2.2 On Input | A | Selection doesn't auto-submit | N | Live test |
| 3.2.3 Consistent Navigation | AA | Nav same across pages | U,F | Site-level review |
| 3.2.4 Consistent Identification | AA | Same components labeled same | U,F | "Buy" vs "Purchase" inconsistency |
| 3.3.1 Error Identification | A | Errors identified in text | U,F | See errors in design? |
| 3.3.2 Labels or Instructions | A | Inputs have labels | U,F,S | See above |
| 3.3.3 Error Suggestion | AA | Suggestions provided when known | U,F | "Email must contain @" |
| 3.3.4 Error Prevention | AA | Reversible/checked/confirmed for legal/financial | U,F | Payment confirmation step |

### Robust

| Criterion | Level | Audit | Auditable | Quick check |
|---|---|---|---|---|
| 4.1.1 Parsing | A | Valid HTML | U | Note: largely satisfied automatically by modern browsers |
| 4.1.2 Name, Role, Value | A | UI components expose semantics | U | See above |
| 4.1.3 Status Messages | AA | Status announced without focus | U | Toast notifications, live regions |

## Output format

Group findings under the four POUR principles. For each finding, cite the criterion number and level. Mark each as auditable or not auditable from this input.
