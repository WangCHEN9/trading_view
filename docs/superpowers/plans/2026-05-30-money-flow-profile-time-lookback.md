# Money Flow Profile — Time-Based Lookback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `Lookback Mode` selector to the Money Flow Profile indicator so the profile range can be defined by the current session ("Today") or a rolling number of days (1–28), in addition to the existing fixed bar count. Default mode is "Today".

**Architecture:** The script's entire downstream logic depends on a single integer bar-offset `rpLN`. We compute `rpLN` per mode on the last bar only, then move the profile's price-range scan (`pLST`/`pHST`/`pSTP`) into that same last-bar block (it previously relied on `rpLN` being a compile-time constant). All rendering below stays untouched, so identical ranges reproduce the current output byte-for-byte.

**Tech Stack:** Pine Script v5 (TradingView). No local test runner — verification is "compiles in TradingView" + on-chart visual/parity checks.

**Spec:** `docs/superpowers/specs/2026-05-30-money-flow-profile-time-lookback-design.md`

**File touched (single):** `scripts/LuxAlgo/00_money_flow_profile.pine`

---

## Testing reality (read first)

Pine Script runs only on TradingView; there is no CLI compiler or unit framework in this repo. Each task's verification is therefore manual:

1. Open <https://www.tradingview.com>, Pine Editor → paste the full file → **Add to chart**.
2. "PASS" = no red compiler errors AND the described on-chart behavior holds.
3. The decisive correctness test is **parity** (Task 5): Fixed `N` and a Time window covering the same `N` bars must render an identical profile.

Do each task's edit, then run the verification before committing. Commit only on PASS.

---

## Current code anchors (verify before editing — line numbers may drift)

- `indicator(...)` declaration: line 6, contains `max_bars_back = 1500`.
- Fixed lookback input + reassignment: lines 15–16.
- `bar b = bar.new()`: line 105.
- Global `pLST`/`pHST` accumulation + `pSTP`: lines 158–168.
- Main render guard `if barstate.islast and ...`: line 170.

---

### Task 1: Raise the history cap

**Files:**
- Modify: `scripts/LuxAlgo/00_money_flow_profile.pine:6`

- [ ] **Step 1: Edit the indicator declaration**

Change `max_bars_back = 1500` to `max_bars_back = 5000`. The full line becomes:

```pine
indicator("Money Flow Profile [LuxAlgo]", "LuxAlgo - Money Flow Profile", true, max_bars_back = 5000, max_boxes_count = 500, max_lines_count = 500)
```

- [ ] **Step 2: Verify (TradingView)**

Paste full file → Add to chart. Expected: compiles, profile still draws exactly as before (no behavior change yet).

- [ ] **Step 3: Commit**

```bash
git add scripts/LuxAlgo/00_money_flow_profile.pine
git commit -m "Raise Money Flow Profile history cap to 5000 bars"
```

---

### Task 2: Replace the fixed-lookback input with mode + days + fixed inputs

**Files:**
- Modify: `scripts/LuxAlgo/00_money_flow_profile.pine:15-16`

- [ ] **Step 1: Replace lines 15–16**

Delete these two lines:

```pine
rpLN   = input.int(200, '  Lookback Length / Fixed Range', minval = 10, maxval = 1500, step = 10 , group = rpGR, display = disp)
rpLN  := last_bar_index > rpLN ? rpLN - 1 : last_bar_index
```

Replace with:

```pine
rpMODE = input.string('Today', '  Lookback Mode', options = ['Fixed Bars', 'Today', 'Days'], group = rpGR, tooltip = 'Today = bars since the current session opened. Days = a rolling N-day window. Fixed Bars = a fixed bar count.', display = disp)
rpDAYS = input.int(7, '  Lookback Days', minval = 1, maxval = 28, group = rpGR, tooltip = 'Used when Lookback Mode = Days. Rolling window of N calendar days (max 28). On small timeframes the window clamps to available history.', display = disp)
rpFIX  = input.int(200, '  Fixed Lookback (bars)', minval = 10, maxval = 5000, step = 10, group = rpGR, tooltip = 'Used when Lookback Mode = Fixed Bars.', display = disp)
```

Note: this removes the global `rpLN` symbol. `rpLN` becomes a `var` computed in Task 4; nothing between here and Task 4 references it (all other uses are inside the `barstate.islast` block). The script will NOT compile cleanly until Task 4 is done — that is expected; Tasks 2–4 are one logical change. Commit at Step 3 anyway to keep diffs small ONLY if you are using a branch; otherwise proceed straight to Task 3 without the on-chart check.

- [ ] **Step 2: Verify (static)**

Confirm by reading the file that the three new inputs sit in the `rpGR` group and the old `rpLN` input lines are gone. Do not expect a clean TradingView compile yet (deferred to Task 4).

- [ ] **Step 3: Commit**

```bash
git add scripts/LuxAlgo/00_money_flow_profile.pine
git commit -m "Add Lookback Mode / Days inputs to Money Flow Profile"
```

---

### Task 3: Add global session-start tracker for the "Today" window

**Files:**
- Modify: `scripts/LuxAlgo/00_money_flow_profile.pine` (immediately after `bar b = bar.new()`, currently line 105)

- [ ] **Step 1: Insert the tracker**

Directly below `bar b = bar.new()` add a blank line then:

```pine
// index of the first bar of the current session — drives the "Today" window
var int tdStartIdx = 0
if session.isfirstbar
    tdStartIdx := bar_index
```

Rationale (gotcha #4): `session.isfirstbar` is a built-in series variable read at global scope every bar, so its history is not corrupted. Do NOT move this read inside the `barstate.islast` block.

- [ ] **Step 2: Verify (static)**

Confirm the four lines are at global scope (column 0 for `var`/`if`), not nested in any other block.

- [ ] **Step 3: Commit**

```bash
git add scripts/LuxAlgo/00_money_flow_profile.pine
git commit -m "Track session start index for Today lookback window"
```

---

### Task 4: Resolve rpLN + profile range on the last bar; wire the guards

**Files:**
- Modify: `scripts/LuxAlgo/00_money_flow_profile.pine:158-170`

This is the core change. It (a) deletes the old constant-`rpLN` range accumulation, (b) computes `rpLN`, `pLST`, `pHST`, `pSTP` on the last bar per mode, and (c) updates the render guard. The large render block below line 170 is NOT touched or re-indented.

- [ ] **Step 1: Delete the old global range block (lines 158–168)**

Delete exactly:

```pine
var float pLST = na
var float pHST = na

if b.i == last_bar_index - rpLN
    pLST := b.l 
    pHST := b.h
else if b.i > last_bar_index - rpLN
    pLST := math.min(b.l, pLST)
    pHST := math.max(b.h, pHST)

pSTP = (pHST - pLST) / rpNR
```

- [ ] **Step 2: Insert the dynamic-lookback block in its place**

Insert (same location the deleted block occupied — between the `bull`/`nzV`/`rpS`/`vpS` lines and the main render guard):

```pine
// Dynamic lookback — rpLN is a bar OFFSET (= bar count - 1), resolved on the last bar.
// Scanning offsets 0..rpLN reproduces the Fixed-Bars range exactly when counts match.
var int   rpLN = na
var float pLST = na
var float pHST = na
var float pSTP = na

if barstate.islast
    // 1) resolve the bar offset for the active mode
    if rpMODE == 'Today'
        rpLN := last_bar_index - tdStartIdx
    else if rpMODE == 'Days'
        int target  = time - rpDAYS * 86400000
        int maxScan = math.min(bar_index, 4999)
        rpLN := 0
        for i = 1 to maxScan
            if na(time[i]) or time[i] < target
                break
            rpLN := i
    else
        rpLN := last_bar_index > rpFIX ? rpFIX - 1 : last_bar_index

    // clamp to a valid offset; 0 falls through the rpLN > 0 guard below (no profile)
    rpLN := math.min(math.max(rpLN, 0), math.min(last_bar_index, 4999))

    // 2) profile price range over offsets 0..rpLN
    pLST := low
    pHST := high
    for i = 0 to rpLN
        pLST := math.min(low[i], pLST)
        pHST := math.max(high[i], pHST)

    // 3) row height
    pSTP := (pHST - pLST) / rpNR
```

Note: `rpDAYS * 86400000` — `rpDAYS` ≤ 28, so the product ≤ 2,419,200,000, which fits Pine's 64-bit `int`. No overflow concern.

- [ ] **Step 3: Confirm the render guard (was line 170) is unchanged**

The existing guard already does what we need — no edit required:

```pine
if barstate.islast and not na(nzV) and not timeframe.isseconds and rpLN > 0 and pSTP > 0 and nzV > 0
```

`rpLN > 0` skips degenerate windows (e.g. Today on a daily chart). Everything inside this `if` (down to end of file) stays exactly as-is.

- [ ] **Step 4: Verify (TradingView) — compiles and Fixed-Bars matches original**

Paste full file → Add to chart on a liquid symbol (e.g. NASDAQ:AAPL, 1h). The default mode is now `Today`, so first confirm a session profile draws. Then set Mode = `Fixed Bars`, Fixed Lookback = `200` and confirm the profile is identical to the original script's Fixed 200 output (the original is the prior git revision of this file).

- [ ] **Step 5: Commit**

```bash
git add scripts/LuxAlgo/00_money_flow_profile.pine
git commit -m "Resolve lookback range dynamically per mode on the last bar"
```

---

### Task 5: Verify behavior — parity + Today + Days + guards

**Files:** none (manual verification on TradingView).

- [ ] **Step 1: Parity check (the key correctness test)**

On NASDAQ:AAPL, 1h, enable "Profile Price Levels" so the profile high/low labels show exact values + a "Number of bars" tooltip:
1. Mode = `Fixed Bars`, Fixed Lookback = `200`. Read profile high, profile low, POC level, and the tooltip's "Number of bars".
2. Mode = `Days`, adjust `Lookback Days` until the "Number of bars" tooltip matches the Fixed run's bar count.

Expected: when the **Number of bars** matches between the two modes, profile high, profile low, and POC are identical. (Confirms the offset-parity convention.)

- [ ] **Step 2: Today renders the current session**

Mode = `Today` on a 5m or 15m intraday chart. Expected: profile covers only bars since the current session opened; the "Number of bars" tooltip ≈ bars elapsed in today's session.

- [ ] **Step 3: Days window scales and clamps**

Mode = `Days`. On a 1h chart sweep `Lookback Days` = 1 / 3 / 7 / 28. Expected: each redraws with a wider range / larger bar count. Then switch to 1m and set Days = 28: expected it still draws (no error), with "Number of bars" capped near 5000 — confirming silent clamp, not a hide.

- [ ] **Step 4: "Today" on a daily chart draws nothing**

Switch the chart to `1D`, Mode = `Today`. Expected: no profile drawn (session-open == last bar ⇒ `rpLN` 0 ⇒ guarded out). This is intended.

- [ ] **Step 5: Fixed mode unchanged**

Mode = `Fixed Bars`, sweep Fixed Lookback across 50 / 200 / 1500 / 5000. Expected: behaves like the original (5000 only fully realized when that much history is loaded; otherwise clamps to available bars without error).

- [ ] **Step 6: Record the verification outcome**

If all pass, note it in the final summary to the user. If any fail, STOP and debug (superpowers:systematic-debugging) before claiming completion.

---

## Self-Review

- **Spec coverage:** mode selector `Fixed Bars`/`Today`/`Days` default `Today` (Task 2) ✓; Today = session open (Tasks 3, 4 Step 2) ✓; Days counting, 1–28 (Task 2 input + Task 4 Step 2) ✓; offset-parity convention (Task 4 Step 2 comment + Task 5 Step 1) ✓; max_bars_back→5000 (Task 1) ✓; clamp to available history, no hide rule (Task 4 Step 2 clamp + Task 5 Step 3) ✓; seconds-timeframe skip preserved (guard kept in Task 4 Step 3) ✓.
- **Placeholder scan:** none — all code shown in full.
- **Type/name consistency:** `rpMODE`, `rpDAYS`, `rpFIX`, `rpLN`, `pLST`, `pHST`, `pSTP`, `tdStartIdx` used identically across tasks. No `rpPERIOD`/`hide1M` remain. `rpLN`/`pLST`/`pHST`/`pSTP` declared `var` once (Task 4) and read in the existing render block. Old `rpLN` input symbol fully removed (Task 2).
- **Clamp vs spec:** both spec and plan clamp the lower bound to `0` so `Today`-on-daily and too-short windows fall through the existing `rpLN > 0` guard (no degenerate profile).
