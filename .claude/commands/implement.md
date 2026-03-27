# Implement — Feature Implementation Workflow

Step-by-step workflow for implementing a feature from the task backlog.

## Instructions

### Step 1: Select Feature

- If the user specifies a feature, use that.
- If not, read `CLAUDE.md` task backlog and pick the next Pending feature.
- Confirm the selection with the user before proceeding.

### Step 2: Read the FSD

Read `docs/FSD/{feature}.md` completely before writing any code.
If the FSD file doesn't exist, STOP and tell the user to create it first (use `/planner`).

### Step 3: Plan Implementation

Before coding, briefly outline:
1. Files to create or modify
2. Key functions/components to implement
3. Dependencies needed (if any)
4. Order of implementation

Present this plan to the user. Wait for approval.

### Step 4: Implement

- Implement one logical unit at a time.
- Follow the project's coding conventions (see CLAUDE.md).
- Write code that matches the FSD spec exactly.
- If you need to deviate from the FSD, note the deviation immediately.

### Step 5: Self-Check

Before invoking review:
- Does the code compile/run without errors?
- Are there any obvious bugs?
- Does it match the FSD user stories?

### Step 6: Review & Test

Invoke both in parallel:
1. `/reviewer` — Code review for bugs, security, spec compliance
2. `/tester` — Test coverage and execution

### Step 7: Product Verification (Playwright MCP)

After unit/integration tests pass, verify the feature in a real browser:
1. Ensure the app is running locally (dev server).
2. Use Playwright MCP to open the app and walk through the FSD user flows.
3. Verify: UI renders correctly, interactions work, error states display properly.
4. If issues are found, fix and re-run from Step 6.

### Step 8: Handle Results

**If all checks PASS (review + test + Playwright verification):**
1. Record any spec deviations in `docs/CHANGELOG.md`
2. Commit with: `feat: {feature description}`
3. Push to main
4. Update CLAUDE.md task backlog status to "Done"

**If any FAIL:**
1. Fix the BLOCKER items
2. Re-run the failing check (Step 6 or 7)
3. Repeat until PASS

### Step 9: Sync Time (if deviations exist)

If any spec deviations were recorded:
- Run `/sync-time` to update SDD/FSD docs

## Rules
- One feature at a time — no parallel feature work.
- Always read the FSD before coding.
- Always get review/test pass before committing.
- Record ALL spec deviations in CHANGELOG.md.
- Don't skip steps — the workflow exists for a reason.
