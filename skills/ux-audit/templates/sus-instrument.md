# Deployable SUS Instrument Template

Use when the user wants to run a real SUS survey (not a heuristic estimate). Outputs an intercept-ready protocol.

## Sample size guidance

| Goal | Recommended n |
|---|---|
| Directional read on one design | 8–10 |
| Reliable single-design estimate | 12–14 |
| Compare two designs (A/B) | 25+ per variant |
| High-precision benchmark | 30+ |

(Source: Sauro & Lewis, *Quantifying the User Experience*)

## Instrument copy

```
We're improving [product/page]. Please complete the task you came here for, then take 1 minute to share your experience.

For each statement, choose the response that best matches your experience just now:
1 = Strongly disagree, 2 = Disagree, 3 = Neutral, 4 = Agree, 5 = Strongly agree

1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very quickly.
8. I found the system very cumbersome to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this system.
```

## Deployment notes

- **Timing:** Show after task attempt, before any other survey or debrief.
- **Required:** All 10 items. Force completion (mark midpoint if unsure, but require an answer).
- **Don't add items.** Adding items breaks comparability with the validated norm.
- **Optional add-on:** A single open-text "What was the hardest part?" question after item 10 captures qualitative signal without contaminating the SUS score.

## Response schema (Hex/Snowflake-friendly)

```sql
CREATE TABLE sus_responses (
  response_id        VARCHAR PRIMARY KEY,
  user_id            VARCHAR,
  variant            VARCHAR,        -- e.g., 'control', 'test_1'
  page_audited       VARCHAR,        -- e.g., 'fol_payment_page'
  task_attempted     VARCHAR,        -- e.g., 'complete_fol_enrollment'
  task_completed     BOOLEAN,
  submitted_at       TIMESTAMP,
  q1_frequent_use    INT,            -- 1-5
  q2_complex         INT,
  q3_easy            INT,
  q4_need_support    INT,
  q5_integrated      INT,
  q6_inconsistent    INT,
  q7_learn_quickly   INT,
  q8_cumbersome      INT,
  q9_confident       INT,
  q10_learn_a_lot    INT,
  open_text_hardest  VARCHAR
);
```

## Scoring SQL

```sql
WITH scored AS (
  SELECT
    response_id,
    variant,
    -- Positive items: score - 1
    (q1_frequent_use - 1) +
    (q3_easy - 1) +
    (q5_integrated - 1) +
    (q7_learn_quickly - 1) +
    (q9_confident - 1) +
    -- Negative items: 5 - score
    (5 - q2_complex) +
    (5 - q4_need_support) +
    (5 - q6_inconsistent) +
    (5 - q8_cumbersome) +
    (5 - q10_learn_a_lot) AS raw_total
  FROM sus_responses
)
SELECT
  variant,
  COUNT(*) AS n,
  ROUND(AVG(raw_total) * 2.5, 1) AS sus_score,
  ROUND(STDDEV(raw_total) * 2.5, 1) AS sus_stddev,
  -- 95% CI half-width
  ROUND(1.96 * (STDDEV(raw_total) * 2.5) / SQRT(COUNT(*)), 1) AS ci_95_halfwidth
FROM scored
GROUP BY variant
ORDER BY sus_score DESC;
```

## Reporting back

| Variant | n | SUS | 95% CI | Grade |
|---|---|---|---|---|
| Control | 14 | 68.4 | ±3.2 | C |
| Test_1 | 13 | 76.2 | ±2.9 | B |

**Interpretation:** Test_1 likely above industry average; CIs do not overlap, suggests real effect. Recommend ship pending other guardrails.
