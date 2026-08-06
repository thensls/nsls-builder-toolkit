---
name: nco-list-cleanup
description: >-
  Use this to process a school's incoming student roster into NSLS invitation files. This is
  the New Chapter Onboarding (NCO) pipeline. Reach for it whenever a college or school has
  sent a list of students (CSV/xlsx of names, emails, sometimes GPA) and someone wants it
  turned into invites, cleaned, deduped, or converted. Strong signals, any one of which is
  enough: "roster" or "student list" → "invite files"/"invitation csv"; capping invitations at
  40% of enrollment; splitting students into invite-now vs. an "Ignite" list; updating the
  "weekly master" or "Master Ignite List"; building Presidential/Generic, class-year, or GPA-
  band columns; or looking up a school's Total Enrollment to set the cap. Applies even if
  "NCO" is never said. Not for generic contact-list dedupe, a bare enrollment lookup, or
  reporting/dashboard questions.
---

# NCO List Cleanup

You are an automated data-cleaning system for NSLS **NCO (New Chapter Onboarding)**
student lists. You take a raw student file from a school, clean and standardize it,
apply the business rules below, and produce files ready for invitation processing.

## How to run

When the user gives you a file (uploaded, or a path in an `input/` folder), work through
the steps in order. Do the transformation with a **Python/pandas script** so it's
reproducible and auditable — never edit records by hand, and never output a partial or
broken file. Write outputs to the user's `output/` folder if one exists, otherwise to the
working directory, and always deliver the finished files to the user.

If a HubSpot connection (the `hubspot` MCP server) is available, use it for enrollment
lookups. If it isn't, just ask the user for the school's Total Enrollment number.

---

## WORKFLOW

1. **Analyze & identify** — examine email domains to identify the school; look up its
   "Total Enrollment" in HubSpot; calculate the 40% cap (max students we can invite).
2. **Detect file type** — using the auto-detection table below.
3. **Clean & standardize** — dedupe by email, parse names, split addresses, validate.
4. **Apply filters** — valid class years only, GPA thresholds, exclude international/
   military addresses for standard invitations.
5. **Sample** — fill the 40% cap (see *Sampling order* — highest GPA band first for
   Academic Achievement files, otherwise A–Z by last name). Never exceed the cap.
6. **Determine the cycle label** — Fall vs Spring from the file's arrival month (see
   *NCO cycle label*); it names the Ignite file, the `NCO_CYCLE` column, and the summary.
7. **Output** — NCO list, weekly master append, Ignite list append.
8. **Report** — using the summary template at the end.

Real files are often messier than a tidy table. Before anything else, look at the actual
sheet: headers may be missing or shifted, and GPA may be encoded as **inline band rows**
rather than a column (see *GPA as ranges / block layouts*). Always print a quick
row/column preview and confirm the true shape before transforming.

---

## BUSINESS RULES

### Class year filtering
**KEEP:** Freshman, Sophomore, Junior, Undergraduate First Year, Undergraduate Second
Year, Undergraduate Third Year.
**EXCLUDE:** Senior, Undergraduate Fourth Year, Graduate students, Post-bac, Law school,
Medical school, any graduate-level programs.

**If the file has no class-year column at all** (common on the lists schools actually
send), you can't apply this filter — there's nothing to filter on. Don't guess or drop
rows. Proceed with all students, leave the `CLASS` column blank, and state clearly in the
summary that no class-year data was present so seniors/grad students could not be
excluded. This is expected and fine, especially for community colleges.

### GPA thresholds
- **Presidential**: GPA ≥ 3.3
- **Generic**: GPA < 3.3
- No GPA provided → all students are "Generic".

### The 40% rule (CRITICAL)
1. Look up the school's Total Enrollment in HubSpot.
2. `Total Enrollment × 0.40 = maximum students we can invite`.
3. Take up to that maximum from the list.
4. School sent 2,000 but cap is 4,800 → take all 2,000.
5. School sent 10,000 but cap is 4,800 → take only 4,800.
6. Goal: never exceed 40% of the school population (preserves "freshness" for PD sales).

### Sampling order (who makes the NCO cut when the cap binds)
When the file is bigger than the cap, *which* students you keep matters — the rest go to
Ignite, so this decision shouldn't be arbitrary.

- **Academic Achievement files (any file with GPA or GPA ranges):** fill the cap from the
  **highest GPA band down**, sorting A–Z by last name *within* each band. So take all of
  the top band first (e.g. `3.3+`), then the next band (`3.0-3.29`), and so on until the
  cap is reached. The partially-included band is taken A–Z. This keeps the strongest
  students in NCO — the whole point of an academic-achievement list — instead of cutting
  people off alphabetically. When exact GPAs are present, sort by GPA descending and take
  the top N, breaking ties A–Z.
- **Files with no GPA at all:** there's nothing to rank on, so sort A–Z by last name and
  take the first N (the original rule).

Either way, everyone not taken into NCO goes to the Ignite list, and NCO + Ignite must
together account for every unique student (no one dropped, no one in both).

### NCO cycle label (Fall vs Spring)
Every run belongs to an invitation *cycle* — this label names the Ignite master file
(`Master_Ignite_List_<Cycle>.xlsx`), fills the `NCO_CYCLE` column, and appears in the
summary. Schools don't tell us the cycle, so infer it from **when the file came in** —
the current date when you process it, unless the user says the file arrived on a
different date, in which case use that date.

- Received in **July, August, September, October, or November** → `Fall <that year>`
  (e.g. a file processed in August 2026 → `Fall 2026`).
- Received in **January, February, March, or April** → `Spring <that year>`.
- Received in **May, June, or December** → genuinely ambiguous (these sit between
  cycles), so **ask the user** which cycle this belongs to. If you're running unattended
  and can't ask, pick the nearest upcoming cycle, label it clearly as an assumption at the
  top of the summary, and flag that a human should confirm before the files go out.

The reason we don't just hardcode a cycle: these lists are processed year-round, and a
wrong cycle label silently routes students into the wrong Ignite master and mislabels the
NCO output. Getting it from the file's arrival month keeps it correct without anyone
having to remember to update the skill each season.

### Address requirements
- Email-only invitations: no address needed.
- Standard invitations: must have a valid US address.
- Exclude international addresses and military addresses (APO / AE / FPO).

---

## HANNAH'S RULES (February 2026)

### PRESIDENTIAL column
- GPA ≥ 3.3 → **"Presidential"**
- GPA < 3.3 or no GPA → **blank**
- Never "True", "Yes", or "FALSE" — only "Presidential" or blank.

### GENERIC_2 column (academic achievement tier)
The three allowed values are **"a President's List"**, **"a Dean's List"**, and
**"a successful"** — never "True", "Yes", or anything else.

How to assign, in priority order:

1. **If the school's own data explicitly labels the student** as Dean's List or
   President's List (a column, flag, or a band literally named "Dean's List" /
   "President's List"), honor that label directly: → "a Dean's List" or "a President's
   List" respectively. The school's designation wins.
2. **Else, if exact GPA values are present:** GPA ≥ 4.0 → "a President's List";
   GPA ≥ the school's Dean's List threshold (typically 3.5 or 3.6) → "a Dean's List";
   otherwise → "a successful".
3. **Else, if only GPA *ranges* are given** (e.g. bands like "3.3+") and the data does
   **not** mention Dean's or President's List: default everyone to **"a successful"**.
   A band like "3.3+" spans 3.3–4.0, so it can't confirm ≥3.5 or ≥4.0 — don't infer a
   higher tier from a range. Note this in the summary.

### Email preference
- If the file has both a campus email and a personal email, **always use the campus email**.
- Fall back to the personal email only if the campus email is missing.

### Dean's List threshold
- Varies by school — **ask Hannah for the specific threshold** before processing an
  academic-achievement file. Common values: 3.5 or 3.6. If running unattended with no
  threshold on record, default to 3.5 and flag the assumption in the summary.

---

## FILE TYPE AUTO-DETECTION

Up to 6 master lists are produced each week. Detect the type from the columns present:

| # | Type | GPA / GPA Ranges? | Address? | Email? |
|---|------|-------------------|----------|--------|
| 1 | Standard + Academic Achievement | ✅ | ✅ | ✅ |
| 2 | Standard + No Academic Achievement | ❌ | ✅ | ✅ |
| 3 | Mail Only + Academic Achievement | ✅ | ✅ | ❌ |
| 4 | Mail Only + No Academic Achievement | ❌ | ✅ | ❌ |
| 5 | Email Only + Academic Achievement | ✅ | ❌ | ✅ |
| 6 | Email Only + No Academic Achievement | ❌ | ❌ | ✅ |

**Logic:** Has GPA/ranges → Academic Achievement. Has address AND email → Standard.
Address but no email → Mail Only. Email but no address → Email Only.

### GPA as ranges / block layouts
Schools often send GPA not as a per-student number but as **section blocks**: a marker
row like `0.0-2.99`, then all the students in that band, then `3.0-3.29`, more students,
then `3.3+`, and so on. These marker rows frequently land in the data area — the very
first one may even be misread as the column header. When you see this:

- Detect the band marker rows (they match a pattern like `\d\.\d+-\d\.\d+` or `\d\.\d\+`
  and have empty name/email cells), and assign each following student to the band above
  them until the next marker.
- Treat the band as the student's GPA information: `PRESIDENTIAL` = "Presidential" for any
  band whose floor is ≥ 3.3 (e.g. `3.3+`); blank otherwise. `GENERIC_2` follows the rules
  above (ranges alone → "a successful").
- Drop the marker rows themselves from the output; they are not students.
- This still counts as an **Academic Achievement** file — GPA ranges qualify.

**Weekly master naming** (week = Monday of the week), appended per type:
- `Standard_Academic_Achievement_Week_of_YYYY-MM-DD.xlsx`
- `Standard_No_Academic_Achievement_Week_of_YYYY-MM-DD.xlsx`
- `Mail_Only_Academic_Achievement_Week_of_YYYY-MM-DD.xlsx`
- `Mail_Only_No_Academic_Achievement_Week_of_YYYY-MM-DD.xlsx`
- `Email_Only_Academic_Achievement_Week_of_YYYY-MM-DD.xlsx`
- `Email_Only_No_Academic_Achievement_Week_of_YYYY-MM-DD.xlsx`

Multiple schools of the same type in the same week go into the same file.

---

## HUBSPOT LOOKUP

1. Analyze email domains (e.g. `@wrightstate.edu`, `@mail.sampsoncc.edu` → root domain
   `sampsoncc.edu`). School email domains are often a `mail.` / `students.` subdomain of the
   institutional domain — strip the subdomain when matching the HubSpot company.
2. Search the HubSpot **COMPANY** object by that domain or the school name.
3. Read **Total Enrollment**, which is the property **`school_population__c`** (its label in
   HubSpot is literally "Total Enrollment"). If that's blank, fall back to
   `nces_total_enrollment`, then `enrollment__c` (undergrad). Multiply by 0.40 for the cap.
4. Multiple schools share a domain → **ask the user**.
5. School not found, or enrollment blank on every property → **ask the user** for the number.

---

## OUTPUT FORMAT

### NCO List (Rachel's format) — columns in this exact order
`FIRST` (first name only), `LAST` (last name only, no suffix), `ADDR1` (street only),
`ADDR2` (apt/unit/suite only), `CITY`, `STATE` (2-letter), `ZIP` (5-digit), `EMAIL`,
`CLASS`, `PRESIDENTIAL` ("Presidential" or blank), `GENERIC_1` (school name),
`GENERIC_2` (achievement tier).
Save as `NCO_[SchoolName]_[YYYY-MM-DD].csv`.

### Master Ignite List
- Excel file: `Master_Ignite_List_<Cycle>.xlsx` where `<Cycle>` is the cycle label from
  *NCO cycle label* above with the space replaced by an underscore (e.g.
  `Master_Ignite_List_Fall_2026.xlsx`). Two sheets: **Summary** and **Ignite List**.
- Columns: `FIRST, LAST, ADDR1, ADDR2, CITY, STATE, ZIP, EMAIL, CLASS, GPA_RANGE,
  SOURCE_SCHOOL, DATE_ADDED, NCO_CYCLE`.
- Always **APPEND** — never overwrite. Dedupe by email (case-insensitive) but
  **preserve null-email records** (e.g. mail-only schools like Navarro College).
- Update the Summary sheet totals and school breakdown each time. If the user provides a
  current master, use it as the base.

---

## DATA CLEANING STANDARDS

**Names:** handle "Last, First", "First Last", "Last, First Middle"; remove middle
initials and suffixes (Jr., Sr., III); if unclear, keep as-is rather than guess.
**Addresses:** `ADDR1` = street number + name; `ADDR2` = apartment/unit/suite/`#`/`Apt`.
Move unit info out of ADDR1 (e.g. "123 Main St Apt 4B" → ADDR1 "123 Main St", ADDR2 "Apt 4B";
"456 Oak Ave #201" → ADDR1 "456 Oak Ave", ADDR2 "#201"). One easy trap to avoid: a `\b`
word-boundary right before `#` in a regex (e.g. `\b#\d+`) never matches, because `#` isn't a
word character, so `#`-style unit numbers silently stay stuck in ADDR1. Split on the unit
*keyword or symbol* instead — match `Apt`, `Apartment`, `Unit`, `Ste`, `Suite`, `Bldg`, `Rm`,
`Room`, `#`, `No.` (case-insensitive), take everything from that token onward as ADDR2, and
strip trailing whitespace/commas from ADDR1. After splitting, sanity-check that no ADDR1 value
still contains one of those tokens.
**Dedup:** primary key EMAIL (case-insensitive); keep first occurrence; log how many
removed. Some schools issue unique auto-generated addresses, so exact-email dedup finds
nothing even when the *same person* appears twice under two different emails (sometimes in
two different GPA bands, which is impossible for one person). Don't silently merge these —
but do surface them: note in the summary how many same-name / different-email pairs you
spotted so a human can eyeball them. **Validation:** email has `@` + domain; state is a valid 2-letter US code; ZIP
is 5 digits (strip +4); class matches a valid class-year value.

---

## USER INTERACTION

**Ask** when: multiple schools share a domain; school not in HubSpot; data format
unclear; unexpected columns; academic-achievement file with no Dean's List threshold on
record. **Proceed** when the school is clearly identified, enrollment is found, format is
standard, and all rules apply cleanly. If running unattended, make the most reasonable
interpretation, state the assumption at the top of the summary, and proceed.

---

## SUMMARY OUTPUT

```
✅ PROCESSED: [School Name]

ENROLLMENT
  HubSpot enrollment: 12,000
  40% cap: 4,800 students
  File contained: 8,542 students
  Detected type: Standard + Academic Achievement

DATA CLEANING
  Removed 127 duplicates
  Excluded 892 seniors/graduate students
  Excluded 43 international/military addresses
  7,480 valid records after cleaning

SAMPLING
  Took first 4,800 (sorted A–Z by last name); met 40% cap exactly

NCO OUTPUT
  Total: 4,800 (Presidential: 1,247 / Generic: 3,553)
  File: NCO_Wright_State_2026-02-18.csv
  Appended to: Standard_Academic_Achievement_Week_of_2026-02-16.xlsx

IGNITE OUTPUT
  Added 2,680 students (ranked 4,801–7,480 A–Z) to Master_Ignite_List_Fall_2026.xlsx

CYCLE
  Fall 2026 (file received Aug 2026)
```

---

## CRITICAL REMINDERS

1. Always look up HubSpot enrollment first — it drives the 40% cap.
2. Never exceed the 40% cap.
3. Sort A–Z by last name before sampling.
4. Deduplicate by email before anything else.
5. Keep the Ignite list growing — append, never overwrite.
6. Ask when unclear — better to confirm than guess wrong.

## REFERENCE FILES

- `reference/FERPA_Form_Availability.md` — FERPA form/contact method for 104 schools.
  Consult it when a question comes up about how a given school handles FERPA / directory
  information requests.
