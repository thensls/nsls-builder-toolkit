// Pure, dependency-free personality-assessment scorer.
//
// Ported faithfully from the production app (ignite-next):
//   - tally + type resolution: src/services/assessmentComputation.ts
//   - card content (what the results screen shows): src/lib/assessmentUtils.ts
//
// THE JOIN: production keys answers by `answerId` and looks weights up by
// answerId (scoringWeightsMap.get(response.answer)). We preserve that exactly.
// The prototype player stores the chosen OPTION TEXT (player.js captureCurrent),
// so resolveAnswerIds() maps text -> answerId via the track options (which carry
// both `text` and `answerId`) BEFORE scoring. Joining by text directly would be
// wrong: in the Clarity track only 50/84 option texts match a weights `optionText`,
// but 81/84 answerIds match — text-joining would silently drop a third of answers.
//
// No DOM, no fetch, no imports. DOM wiring lives in player.js / render-substep.mjs.

const ASSESSMENT_STEP_SLUG = "discover-your-personality";

// --- tally → type helpers (verbatim logic from assessmentComputation.ts) ---

function computeMBTI(s) {
  return [
    s.E > s.I ? "E" : "I",
    s.S > s.N ? "S" : "N",
    s.T > s.F ? "T" : "F",
    s.J > s.P ? "J" : "P",
  ].join("");
}

function computeEnneagram(s) {
  const entries = Object.entries(s);
  if (entries.length === 0) return "type5";
  return entries.reduce((a, b) => (a[1] > b[1] ? a : b))[0];
}

function computeHolland(s) {
  return Object.entries(s)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([k]) => k)
    .join("");
}

function computeDISC(s) {
  const entries = Object.entries(s);
  if (entries.length === 0) return "C";
  return entries.reduce((a, b) => (a[1] > b[1] ? a : b))[0];
}

function computeBig5(s) {
  const traits = [];
  if (s.openness > 0) traits.push("High Openness");
  else if (s.openness < 0) traits.push("Low Openness");
  if (s.conscientiousness > 0) traits.push("High Conscientiousness");
  else if (s.conscientiousness < 0) traits.push("Low Conscientiousness");
  if (s.extraversion > 0) traits.push("High Extraversion");
  else if (s.extraversion < 0) traits.push("Low Extraversion");
  if (s.agreeableness > 0) traits.push("High Agreeableness");
  else if (s.agreeableness < 0) traits.push("Low Agreeableness");
  if (s.neuroticism > 0) traits.push("High Neuroticism");
  else if (s.neuroticism < 0) traits.push("Low Neuroticism");
  return traits.length > 0 ? traits.join(", ") : "Balanced across all traits";
}

function emptyScores() {
  return {
    myersBriggs: { E: 0, I: 0, S: 0, N: 0, T: 0, F: 0, J: 0, P: 0 },
    enneagram: { type1: 0, type2: 0, type3: 0, type4: 0, type5: 0, type6: 0, type7: 0, type8: 0, type9: 0 },
    holland: { R: 0, I: 0, A: 0, S: 0, E: 0, C: 0 },
    disc: { D: 0, I: 0, S: 0, C: 0 },
    // NOTE: big5 has NO `introversion` key — and that is FAITHFUL to production.
    // The vendored scoring weights carry 4 `"introversion": 0.9` entries, but
    // production (assessmentComputation.ts) inits big5 with exactly these five
    // keys and tallies via `if (key in scores.big5)`, so `introversion` is a
    // dead key dropped in prod too. Don't add it here — that would make the
    // preview diverge from the app. See prototype/SYNC.md.
    big5: { openness: 0, conscientiousness: 0, extraversion: 0, agreeableness: 0, neuroticism: 0 },
  };
}

/**
 * Score a personality assessment from chosen answerIds.
 * @param {{answerIds: string[], weights: Array, types?: object}} args
 * @returns results: { myersBriggs, enneagram, hollandCode, disc, big5, detailedScores, cards }
 */
export function scoreAssessment({ answerIds = [], weights = [], types = null }) {
  const byId = new Map(weights.map((w) => [w.answerId, w]));
  const scores = emptyScores();

  for (const id of answerIds) {
    const w = byId.get(id);
    if (!w) continue; // graceful: unmatched answer contributes nothing (production warns + skips)
    addInto(scores.myersBriggs, w.myersBriggs);
    addInto(scores.enneagram, w.enneagram);
    addInto(scores.holland, w.hollandCode);
    addInto(scores.disc, w.disc);
    addInto(scores.big5, w.big5);
  }

  const results = {
    myersBriggs: computeMBTI(scores.myersBriggs),
    enneagram: computeEnneagram(scores.enneagram),
    hollandCode: computeHolland(scores.holland),
    disc: computeDISC(scores.disc),
    big5: computeBig5(scores.big5),
    detailedScores: scores,
  };
  if (types) results.cards = buildCards(results, types);
  return results;
}

function addInto(target, weightObj) {
  if (!weightObj) return;
  for (const [k, v] of Object.entries(weightObj)) {
    if (k in target) target[k] += v;
  }
}

// --- resolve player text answers -> answerIds via the track options ---

/**
 * Map the player's stored answers (text, keyed by substep slug) to answerIds,
 * using the assessment step's option list (each option has {text, answerId}).
 *
 * Matching is against the KNOWN option texts, never a blind delimiter split.
 * The personality substeps are SINGLE-pick (the whole stored string is one
 * option text), but the player joins true multi-selects with ", " — and option
 * texts can themselves contain ", " (e.g. "Aim for more abstract, exciting
 * possibilities"), so NO split is safe. We instead:
 *   (a) try the WHOLE stored string as one option text (fixes every single-pick
 *       comma case — the dominant case); then
 *   (b) only if that misses, recover multiple selections by greedily consuming
 *       known option texts from the string, longest-match first, tolerating the
 *       ", " join between them.
 */
export function resolveAnswerIds(track, answers = {}) {
  const step = (track?.steps || []).find((s) => s.slug === ASSESSMENT_STEP_SLUG);
  if (!step) return [];
  const subs = step.substeps || step.subSteps || [];

  // text -> answerId, scoped to this step's options
  const textToId = new Map();
  for (const sub of subs) {
    for (const o of sub.options || []) {
      if (o && typeof o === "object" && o.answerId != null && o.text != null) {
        textToId.set(o.text, o.answerId);
      }
    }
  }
  // Known option texts, longest first, so greedy matching prefers the most
  // specific text (avoids a shorter text shadowing a longer one it prefixes).
  const knownTexts = [...textToId.keys()].sort((a, b) => b.length - a.length);

  const ids = [];
  for (const sub of subs) {
    const raw = answers[sub.slug];
    if (raw == null || raw === "") continue;
    for (const id of matchOptionTexts(String(raw), textToId, knownTexts)) {
      ids.push(id);
    }
  }
  return ids;
}

/**
 * Resolve a stored answer string to one or more answerIds using only the known
 * option texts. (a) whole-string single-pick first; (b) greedy longest-match
 * recovery of a ", "-joined multi-select otherwise.
 */
function matchOptionTexts(raw, textToId, knownTexts) {
  const whole = raw.trim();
  // (a) Whole string is one known option — the single-pick case (comma-safe).
  if (textToId.has(whole)) return [textToId.get(whole)];

  // (b) Recover a multi-select: greedily consume known texts from the front,
  //     longest-match first, skipping any ", " join (and stray whitespace).
  const ids = [];
  let rest = whole;
  while (rest.length > 0) {
    const match = knownTexts.find(
      (t) => t.length > 0 && rest.slice(0, t.length) === t
    );
    if (!match) break; // unrecognized leading text — give up (graceful)
    ids.push(textToId.get(match));
    rest = rest.slice(match.length);
    // consume the join: a comma optionally followed by whitespace, or bare ws.
    rest = rest.replace(/^\s*,?\s*/, "");
  }
  return ids;
}

// --- card content for the results screen (ported from assessmentUtils.ts) ---

function getHollandCodeFormatted(hollandCode, types) {
  const primary = hollandCode.charAt(0);
  const ht = (types.hollandCode || []).find(
    (t) => t.name.charAt(0).toUpperCase() === primary.toUpperCase()
  );
  if (!ht) return { result: hollandCode, description: "" };
  const combo = ht.combinations ? ht.combinations[hollandCode] : undefined;
  const result = combo
    ? `${ht.name} (${hollandCode}) - ${combo}`
    : `${ht.name} (${hollandCode})`;
  return { result, description: ht.description || "" };
}

/**
 * Build the carousel/card list the production results screen surfaces
 * (transformUserAssessmentsToCarouselItems). Returns [{color,title,result,description}].
 */
export function buildCards(results, types) {
  const cards = [];

  if (results.myersBriggs) {
    const t = (types.myersBriggs || []).find((x) => x.id === results.myersBriggs);
    cards.push({ color: "myers-briggs", title: "Myers Briggs", result: results.myersBriggs, description: t?.description ?? "" });
  }
  if (results.enneagram) {
    const t = (types.enneagram || []).find((x) => x.id === results.enneagram);
    cards.push({ color: "enneagram", title: "Enneagram", result: t?.name ?? "", description: t?.description ?? "" });
  }
  if (results.hollandCode) {
    const { result, description } = getHollandCodeFormatted(results.hollandCode, types);
    cards.push({ color: "holland-code", title: "Holland Code", result, description });
  }
  if (results.disc) {
    const t = (types.DISC || []).find((x) => x.id === results.disc);
    cards.push({ color: "disc", title: "DISC", result: results.disc, description: t?.description ?? "" });
  }
  if (results.big5) {
    cards.push({ color: "big-five", title: "Big Five", result: results.big5, description: "Personality traits measured on five key dimensions" });
  }
  return cards;
}

export { ASSESSMENT_STEP_SLUG };
