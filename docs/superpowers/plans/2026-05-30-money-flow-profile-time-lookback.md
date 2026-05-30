# Money Flow Profile — Time-Based Lookback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `Lookback Mode` toggle to the Money Flow Profile indicator so the profile range can be defined by a calendar window (Today / 3 Days / 1 Week / 1 Month) in addition to the existing fixed bar count.

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

### Task 2: Replace the fixed-lookback input with mode + period + fixed inputs

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
rpMODE   = input.string('Fixed Bars', '  Lookback Mode', options = ['Fixed Bars', 'Time Period'], group = rpGR, display = disp)
rpPERIOD = input.string('1 Week', '  Time Period', options = ['Today', '3 Days', '1 Week', '1 Month'], group = rpGR, tooltip = 'Used when Lookback Mode = Time Period.\n - Today = bars since the current session opened\n - 1 Month = 28 days (4 weeks); not drawn below the 5-minute timeframe', display = disp)
rpFIX    = input.int(200, '  Fixed Lookback (bars)', minval = 10, maxval = 5000, step = 10, group = rpGR, tooltip = 'Used when Lookback Mode = Fixed Bars.', display = disp)
```

Note: this removes the global `rpLN` symbol. `rpLN` becomes a `var` computed in Task 4; nothing between here and Task 4 references it (all other uses are inside the `barstate.islast` block). The script will NOT compile cleanly until Task 4 is done — that is expected; Tasks 2–4 are one logical change. Commit at Step 3 anyway to keep diffs small ONLY if you are using a branch; otherwise proceed straight to Task 3 without the on-chart check.

- [ ] **Step 2: Verify (static)**

Confirm by reading the file that the three new inputs sit in the `rpGR` group and the old `rpLN` input lines are gone. Do not expect a clean TradingView compile yet (deferred to Task 4).

- [ ] **Step 3: Commit**

```bash
git add scripts/LuxAlgo/00_money_flow_profile.pine
git commit -m "Add Lookback Mode / Time Period inputs to Money Flow Profile"
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
    if rpMODE == 'Time Period'
        if rpPERIOD == 'Today'
            rpLN := last_bar_index - tdStartIdx
        else
            int periodMs = switch rpPERIOD
                '3 Days'  => 3  * 86400000
                '1 Week'  => 7  * 86400000
                '1 Month' => 28 * 86400000
                => 0
            int target  = time - periodMs
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

// hide "1 Month" on sub-5-minute timeframes (28 days cannot fit there)
bool hide1M = rpMODE == 'Time Period' and rpPERIOD == '1 Month' and timeframe.in_seconds() < 300
```

- [ ] **Step 3: Update the render guard (was line 170)**

Change:

```pine
if barstate.islast and not na(nzV) and not timeframe.isseconds and rpLN > 0 and pSTP > 0 and nzV > 0
```

to:

```pine
if barstate.islast and not na(nzV) and not timeframe.isseconds and not hide1M and rpLN > 0 and pSTP > 0 and nzV > 0
```

Everything inside this `if` (down to end of file) stays exactly as-is.

- [ ] **Step 4: Verify (TradingView) — default behaves like before**

Paste full file → Add to chart on a liquid symbol (e.g. NASDAQ:AAPL, 1h). Defaults are `Fixed Bars` / 200. Expected: compiles with no errors; profile looks identical to the original script's Fixed 200 output.

- [ ] **Step 5: Commit**

```bash
git add scripts/LuxAlgo/00_money_flow_profile.pine
git commit -m "Resolve lookback range dynamically per mode on the last bar"
```

---

### Task 5: Verify behavior — parity + each period + guards

**Files:** none (manual verification on TradingView).

- [ ] **Step 1: Parity check (the key correctness test)**

On NASDAQ:AAPL, 1h:
1. Mode = `Fixed Bars`, Fixed Lookback = `200`. Note the profile (POC line level, profile high/low — enable "Profile Price Levels" to read exact values).
2. Switch Mode = `Time Period`, Period = whichever window currently spans 200 bars. To force an exact match instead of guessing: temporarily set Fixed Lookback so its bar count equals a Time window you can reproduce, OR compare by reading the "Number of bars" tooltip on the profile high/low label in each mode.

Expected: when the **Number of bars** tooltip matches between the two modes, the profile high, profile low, and POC are identical.

- [ ] **Step 2: Each time window renders**

Mode = `Time Period`. On a 1h chart cycle Period through `Today`, `3 Days`, `1 Week`, `1 Month`. Expected: each redraws with a progressively wider price range and larger bar count (check the profile-high tooltip "Number of bars"). `Today` should cover only the current session's bars.

- [ ] **Step 3: "Today" on a daily chart draws nothing**

Switch the chart to `1D`, Mode = `Time Period`, Period = `Today`. Expected: no profile drawn (session-open == last bar ⇒ `rpLN` 0 ⇒ guarded out). This is intended.

- [ ] **Step 4: "1 Month" hidden below 5-minute**

Mode = `Time Period`, Period = `1 Month`. Set chart to `1m` then `3m`: expected no profile. Set chart to `5m` then `15m`: expected profile draws. Confirms `hide1M` (`timeframe.in_seconds() < 300`).

- [ ] **Step 5: Fixed mode unchanged**

Mode = `Fixed Bars`, sweep Fixed Lookback across 50 / 200 / 1500 / 5000. Expected: behaves like the original (5000 only fully realized when that much history is loaded; otherwise clamps to available bars without error).

- [ ] **Step 6: Record the verification outcome**

If all pass, note it in the final summary to the user. If any fail, STOP and debug (superpowers:systematic-debugging) before claiming completion.

---

## Self-Review

- **Spec coverage:** mode toggle (Task 2) ✓; Today = session open (Tasks 3, 4 Step 2) ✓; 3D/1W/1M counting with 28-day month (Task 4 Step 2) ✓; offset-parity convention (Task 4 Step 2 comment + Task 5 Step 1) ✓; max_bars_back→5000 (Task 1) ✓; clamp to available history (Task 4 Step 2 clamp) ✓; hide 1M below 5-min (Task 4 Steps 2–3, Task 5 Step 4) ✓; seconds-timeframe skip preserved (guard kept in Task 4 Step 3) ✓.
- **Placeholder scan:** none — all code shown in full.
- **Type/name consistency:** `rpMODE`, `rpPERIOD`, `rpFIX`, `rpLN`, `pLST`, `pHST`, `pSTP`, `tdStartIdx`, `hide1M` used identically across tasks. `rpLN`/`pLST`/`pHST`/`pSTP` declared `var` once (Task 4) and read in the existing render block. Old `rpLN` input symbol fully removed (Task 2).
- **Note vs spec:** spec said clamp `[1, …]`; plan clamps lower bound to `0` so that `Today`-on-daily and too-short windows fall through the existing `rpLN > 0` guard (no degenerate 2-bar profile). This is the correct realization of the spec's "guarded out" intent.
