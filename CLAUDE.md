# TSLA Group — Claude Working Rules

## Standing Rules (never forget these)

### Git / PR workflow
- Branch: `claude/pdf-autofill-theme-fix-vo2b4p`
- Repo: `njmii/tsla-group`
- Use **GitHub MCP tools** (`mcp__github__*`) — the `gh` CLI is not available
- **Always create a PR and squash-merge it immediately** after pushing — do not wait for user confirmation
- If the branch PR is already merged, reset the branch from main and push fresh work there

### Code safety
- **NEVER change the PR13 or CE formula** — they are verified against FWD portal figures
- `scripts/test_pr13.py` must pass all 10 tests after any change to `agent-report.html`
- Do not break local-mode users in `budget-tracker.html` — the key `tsla_budget2_local` (SK) must still work

---

## PR13 Formula (`agent-report.html`)

**Cohort window** (rolling, relative to projection month):
- Issued 13–24 months before end of projection month
- `wsKey = PROJ_YEAR*12 + PROJ_MONTH - 24`
- `weKey = PROJ_YEAR*12 + PROJ_MONTH - 12`

**ACE calculation — `getACE(c)`**:
```js
// ×13 multiplier for qualifying FWD plans
X13_PLANS  = ['FWD Life First', 'FWD Protect First', 'FWD Income First']
FORCE_X12  = ['AN443318', 'AN457372']   // override: FWD portal confirms ×12

if (!FORCE_X12.has(certNo) && X13_PLANS.has(plan)
    && issueDate >= '2024-07-01' && issueDate <= '2024-11-30'
    && contribution >= 200)
  return round(contribution * 13, 2dp)

return c.ace || round(contribution * 12, 2dp)
```

**Classification — `classifyPR13(c)`**:
1. Outside window → `na`
2. Freelook Cancellation → `excl`
3. `pointInTimeStatus(c)`:
   - Contract Surrendered + statusUpdatedDate > projLast → treat as In Force
   - Lapsed + statusUpdatedDate > projLast + months(issueDate→dueDate) ≥ 13 → treat as In Force
4. In Force → `100%`
5. Contract Surrendered: months(issueDate→statusUpdatedDate) ≥ 13 → `100%`, else `0%`
6. Lapsed → `0%`

**Rate**: `round(collACE / eligACE * 10000) / 100` → 2dp

**Verified expected values** (A11668, from FWD portal):
| Month | PR13% |
|-------|-------|
| June 2026 | 93.43% |
| May 2026 | 95.74% |
| April 2026 | 95.33% |
| March 2026 | 95.68% |

---

## CE Formula (`agent-report.html`)

**Cohort window**: issued within the last 12 months (complement of PR13)
- `ceM = PROJ_YEAR*12 + PROJ_MONTH - 12`
- Eligible: `issuedKey >= ceM && issuedKey < PROJ_YEAR*12 + PROJ_MONTH`

**Classification — `classifyCE(c)`**:
1. Outside CE window → `na`
2. Freelook Cancellation → `excl`
3. dueDate in current month → `100%` ⚠️ WATCH
4. dueDate before current month → `0%`
5. Contract Surrendered → `0%`
6. Biro Angkasa → `100%`
7. In Force → `100%`, else `0%`

**Rate**: same formula as PR13 — `round(collACE / eligACE * 10000) / 100`

---

## Agent Data (`data/pr-data.json`)

**Leader**: A11668 — Najmi Fikri bin Azini

**DOWNLINES** (hardcoded in `agent-report.html` line ~1517):
```js
const DOWNLINES_CFG = { 'A11668': ['A13290', 'A14252', 'A12322'] }
```

**Agent short names**:
| Code | Name |
|------|------|
| A11668 | Najmi |
| A13290 | Naqi |
| A14252 | Roza |
| A15475 | Muaz |
| A15756 | Fadhlan |
| A15781 | Fauzan |
| A16553 | Adam |

**Monthly update**: run `python3 scripts/convert.py` on new FWD Excel → updates `data/pr-data.json`

---

## Firebase (`budget-tracker.html`)

Same project as `activity-tracker.html` — **tsla-group**.

```js
firebase.initializeApp({
  apiKey:      'AIzaSyAyLIIH1zmeoBqH1DuT3wbSxmQlRcDJ_P4',
  authDomain:  'tsla-group.firebaseapp.com',
  databaseURL: 'https://tsla-group-default-rtdb.asia-southeast1.firebasedatabase.app',
  projectId:   'tsla-group',
})
```

**Data paths**:
- `budget/accounts/{username}` → `{ pin, created }`
- `budget/data/{username}` → `{ json: JSON.stringify(data) }` (stored as string to avoid array→object conversion)

**Sync strategy**:
- On login: pull from Firebase, merge into localStorage
- On save: write localStorage (instant) + Firebase (background, fire-and-forget)
- On page reload (already logged in): load localStorage immediately, background-sync Firebase after 800ms
- Offline: fall back to localStorage throughout

**Storage keys**:
- `tsla_budget2_local` (SK) — legacy local mode, must never break
- `tsla_bdata_{username}` — per-account local cache
- `tsla_cur_user` — persists logged-in username across sessions
- `tsla_accts` — local account registry for offline fallback

---

## Budget Tracker — Salary Privacy

Salary input is masked by default. Two-step reveal:
- Show: tap the `••••••` masked row → input appears
- Hide: click "Hide" link or close the setup panel
- The setup panel collapse (`toggleSetup`) also calls `hideSalary()`

---

## Key Files

| File | Purpose |
|------|---------|
| `agent-report.html` | PR13 + CE + leaderboard dashboard |
| `budget-tracker.html` | Budget tracker with Firebase sync |
| `data/pr-data.json` | Agent + client data (updated monthly) |
| `scripts/convert.py` | Excel → JSON converter |
| `scripts/test_pr13.py` | PR13 regression tests (10 cases, must all pass) |
| `index.html` | Homepage with accordion nav |
| `client-profile.html` | Client profile + Ankasa Servicing (PIN: 1111) |
| `dame-strategy.html` | DAME strategy tool with myPusaka step |
