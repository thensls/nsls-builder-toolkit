---
name: macroscope
description: >
  Use when the Macroscope review bot (macroscopeapp[bot], the "Macroscope - Correctness"
  check) has posted review comments on a pull request, when a new push triggered a fresh
  batch of correctness findings, or when a merge is blocked by unresolved Macroscope
  comments. Trigger phrases: macroscope, macro scope, macroscope comments, correctness
  check, review bot flagged, merge blocked by comments, new comments after push.
---

# Responding to a Macroscope review

Macroscope re-reviews the newest commit on every push and posts inline review comments,
a review verdict, and an auto-summary block in the PR description. It shows you **one
instance** of a problem; the same class of problem often lives in many other places. If
you fix the literal comments one at a time, the next push surfaces the siblings as "new
comments" — an endless drip. This skill exists to end that in a single round by fixing
**classes at the root**, not comments one by one.

## The one rule

**Fix the class, not the comment.** Every finding is treated as an example of a pattern.
You find every instance of that pattern in the codebase and fix the root cause, so the
whole class is gone in one pass.

## The promise

You **cannot** promise "Macroscope won't comment again" — it re-runs on every push and can
always find something new. What you **can**
promise, and must deliver: *this round fixes the entire class of each finding, so it will
not come back for the same reason.*

## The workflow, start to finish

### 1. Pull every finding at its source — never from scroll-back or a stale summary
Read the live PR, not memory and not an earlier plan. Auto-detect the repo and PR:

    REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
    PR=$(gh pr view --json number -q .number)

Get the current inline findings and the review verdict:

    gh api "repos/$REPO/pulls/$PR/comments" --paginate \
      -q '.[] | select(.user.login=="macroscopeapp[bot]") | "\(.path):\(.line // .original_line)  ::  \(.body | split("\n")[0])"'
    gh api "repos/$REPO/pulls/$PR/reviews" --paginate \
      -q '.[] | select(.user.login=="macroscopeapp[bot]") | "[\(.state)] commit=\(.commit_id[0:7]) \(.submitted_at)"'

Get the **still-unresolved** threads (these are what block merge). Resolution status only
comes from GraphQL:

    gh api graphql --paginate -f query='
    query($owner:String!,$repo:String!,$pr:Int!,$endCursor:String){
      repository(owner:$owner,name:$repo){
        pullRequest(number:$pr){
          reviewThreads(first:100, after:$endCursor){
            pageInfo{ hasNextPage endCursor }
            nodes{ isResolved isOutdated
              comments(first:1){ nodes{ author{login} path line body } } } } } } }' \
      -F owner="${REPO%/*}" -F repo="${REPO#*/}" -F pr="$PR"

Filter to `isResolved == false` and author `macroscopeapp[bot]`. Confirm which commit the
review is on — findings on an old commit may already be fixed. Count them yourself from the
API; do not trust a prior count in a plan or summary.

### 2. Verdict first — does each finding actually need fixing?
For every finding, give a plain-English verdict before proposing any code change:
**real bug, theoretical nit, future bug, macroscope just wrong?** Quantify the blast radius with real data where the finding
implies user impact (e.g. query the read-only production replica when relevant). A finding that cannot ever bite anyone in
practice, or that would have net negative impact, is not a comment to recommend action on.

### 3. Group findings into classes, not a flat list
Collapse the findings into the underlying patterns. Two comments in different files are often
the same class (e.g. "flush call inside a try block that a catch can overwrite," "success
event fired after a caught failure," "callback reads render-closure values instead of the
mutation's variables"). Name each class.

### 4. Sweep the whole codebase for every sibling of each class
For each class, search the entire codebase for other instances — dispatch an explorer per
class if useful. This is the step that ends the drip: you find the siblings *now*, before a
future push turns them into "new comments." Report how many instances each class has and
where.

### 5. One consolidated plan covering ALL of it — before touching code
Present a single plan that addresses every class and every instance, with the root fix for
each. Not comment-by-comment. Get approval before editing. Do not start fixing until the
whole plan is agreed.

### 6. Fix at the root; stay surgical
Prefer the fix that neutralizes the class at its source (e.g. make the shared helper
non-throwing so every call site is safe at once) over N local patches. Make only the changes
the plan calls for — no structural or opportunistic changes. **Never clobber Macroscope's
auto-summary block in the PR description** (it lives between hidden markers); when editing the
body, preserve that block byte-for-byte.

### 7. Never defer real work into a ticket to make the review pass
If a finding needs fixing, fix it in this round. Do not file a new issue as an escape hatch to
get the check green — that is whack-a-mole wearing a disguise. Filing a ticket is only
legitimate for work that is genuinely out of this PR's scope, and only when that is stated
plainly and agreed — never as a way to make a comment go away.

### 8. Verify, then checkpoint, then commit
Run the project's full checks (and the app itself for anything user-visible) and report what
you actually saw. Bring a consolidated review-and-commit checkpoint — every changed line, the
class each change closes, how you verified it, and the commit message — and commit only after
approval.

### 9. Push, re-review, and confirm the class is gone
Push so Macroscope re-reviews the new commit. Poll for the review on the **new** commit SHA
and report the result as the evidence that the class is closed:

    gh api "repos/$REPO/pulls/$PR/reviews" --paginate \
      -q '[.[] | select(.user.login=="macroscopeapp[bot]") | select(.commit_id|startswith("<NEW_SHA>"))] | length'
    gh pr checks "$PR" | grep -i "Macroscope"

Resolving the review threads and merging the PR belong to the PR owner. Surface exactly which
comments remain to be resolved; do not merge on their behalf.

## Anti-patterns (all of these have caused the drip before)
- Fixing the literal comments one at a time.
- Trusting a stale plan/summary for the finding count instead of reading the live comments.
- Promising "this is the last round" — the bot re-runs on every push; that promise is not
  yours to make.
- Filing a ticket to defer a real fix so the check goes green.
- Overwriting Macroscope's auto-summary block in the PR description.
- Making structural changes when only a surgical fix was needed.
