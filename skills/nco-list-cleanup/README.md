# NCO List Cleanup (Claude Code skill)

Automates cleaning of NSLS NCO (New Chapter Onboarding) student lists sent by schools.

Given a raw school roster, it:

- identifies the school from email domains and looks up Total Enrollment in HubSpot,
- enforces the **40% cap** (never invites more than 40% of a school's population),
- detects the file type (Standard / Mail Only / Email Only × Academic Achievement or not),
- cleans and standardizes names, addresses (splitting unit/apt info into ADDR2), emails,
  and validates the data,
- filters out seniors/graduate students and international/military addresses,
- when the cap binds, keeps the strongest students first — **highest GPA band down** for
  academic-achievement files (A–Z within each band), or A–Z by last name when there's no
  GPA — and sends the rest to Ignite,
- labels the invitation **cycle** (Fall vs Spring) from the file's arrival month, so the
  Ignite master and `NCO_CYCLE` column are correct year-round,
- outputs the NCO list (Rachel's format), the correct weekly master sheet, and appends
  the remainder to the Master Ignite List.

Includes Hannah's February 2026 rules (Presidential column, GENERIC_2 achievement tiers,
campus-email preference, per-school Dean's List threshold), handles GPA supplied as inline
band rows and lists with no class-year column, and ships a FERPA form-availability
reference for 104 schools under `reference/`.

**To use:** run `claude` in this repo and say something like *"process this NCO list"*
with the school file attached or its path. The skill loads automatically.

See `SKILL.md` for the full rule set.
