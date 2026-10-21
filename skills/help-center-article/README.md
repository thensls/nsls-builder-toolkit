# Help Center Article (Claude Code skill)

Helps the Member Experience team write and publish member-facing articles for the
NSLS Help Center knowledge base in HubSpot (info.nsls.org/help), in the design the
Help Center has used since October 21, 2026.

Given what members are asking, it:

- searches the 90+ live articles (titles and full text) so you update an existing
  article instead of writing a second one,
- drafts an answer-first article in the Help Center design: question titles, real
  numbered lists, `<h3>` sections, the standard contact block, NSLS voice and the
  Help Center style glossary (terms, facts, canonical links),
- checks it (`scripts/check_article.py`): blocks em and en dashes, double spaces,
  non-breaking spaces, pasted styles, typed lists, loose text, missing metadata and
  a missing contact block, and fixes the purely mechanical problems itself,
- previews it inside a real Help Center page (`scripts/preview.py`),
- hands the writer click-by-click HubSpot steps to save it as a **draft**, plus a
  filled-in review message for the MEX lead (Kimberly Campbell or Kara Klimuszko),
  who publishes.

The skill never creates, edits or publishes anything in HubSpot. Scripts use the
Python standard library and read only the public Help Center.

Related: `/help-center` curates the help.nsls.org portal that these articles sync
to every Monday; `/kb-article` is for the staff-only internal knowledge base.

**To use:** say something like *"write a help center article about updating your
kit mailing address"* or *"check the help article how-can-i-track-my-order"*.

See `SKILL.md` for the full process.
