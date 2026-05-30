# Money Flow Profile — Time-Based Lookback

**Date:** 2026-05-30
**File:** `scripts/LuxAlgo/00_money_flow_profile.pine` (Pine Script v5)

## Goal

Let the profile's lookback range be defined by a **calendar time window**
(Today / 3 Days / 1 Week / 1 Month) instead of only a fixed bar count. The
existing fixed-bar behavior stays available via a mode toggle (non-destructive).

## Decisions

| Question            | Decision                                                        |
|---------------------|-----------------------------------------------------------------|
| Mode design         | Add a `Lookback Mode` toggle: `Fixed Bars` \| `Time Period`      |
| "Today" definition  | Since the current trading **session open** (`session.isfirstbar`)|
| Bar-cap handling    | Raise `max_bars_back` 1500 → 5000, then clamp to available history |
| "1 Month" on small TF | Draw nothing when `timeframe.in_seconds() < 300` (below 5-min)  |

## New Inputs

- `Lookback Mode` — `input.string('Fixed Bars', options=['Fixed Bars','Time Period'])`
- `Time Period` — `input.string('1 Week', options=['Today','3 Days','1 Week','1 Month'])`
- Existing fixed input: relabel to `Fixed Lookback (bars)`, raise `maxval` to 5000.

Note: Pine input dropdowns are static, so "1 Month" cannot be *removed* from the
list per timeframe — instead the render is skipped (see guards).

## Computing `rpLN` (bar count) — all resolved on the last bar

**Convention:** `rpLN` is a bar **offset**, not a cardinality. It equals
`(number of bars in window) - 1`, and the script scans offsets `0..rpLN`
(i.e. `rpLN + 1` bars). All modes MUST follow this so that identical ranges
yield identical `rpLN` and therefore byte-identical output to the current
Fixed-Bars method.

- **Fixed Bars** → unchanged: `last_bar_index > rpFIX ? rpFIX - 1 : last_bar_index`.
  ("200" → `rpLN = 199` → 200 bars scanned.)
- **Today** → track session start globally:
  `var int tdStartIdx`; `if session.isfirstbar => tdStartIdx := bar_index`.
  Then `rpLN = last_bar_index - tdStartIdx`.
- **3 Days / 1 Week / 1 Month** → `target = time - N*86400000` ms
  (N = 3 / 7 / 28; month = 28 days = exactly 4 weeks). Walk back on the last bar,
  storing the **offset** of the furthest in-window bar:
  `for i = 1 to min(bar_index, 4999): if not na(time[i]) and time[i] >= target => rpLN := i, else break`.
  (`rpLN` ends as the largest offset still inside the window = bar count − 1.)
- Clamp final `rpLN` to `[1, min(last_bar_index, 4999)]`.

## Refactor (required)

The current script accumulates the profile price range `pLST`/`pHST` on **every
historical bar** using `last_bar_index - rpLN` (lines 158–168). That only works
because `rpLN` is a constant. A time window is not known until the last bar, so
this accumulation must move into the `barstate.islast` block.

1. `indicator(... max_bars_back = 5000 ...)` (was 1500).
2. Delete the global `pLST` / `pHST` / `pSTP` block (current lines 158–168).
3. Inside `barstate.islast`:
   a. compute `rpLN` per mode (above);
   b. scan the last `rpLN` bars → `pLST = min(low)`, `pHST = max(high)`;
   c. `pSTP = (pHST - pLST) / rpNR`;
   d. inner guard `if rpLN > 0 and pSTP > 0` wraps all existing rendering
      (unchanged below this point).

## Guards

- Existing seconds-timeframe skip is kept.
- New skip: `Time Period` + `1 Month` + `timeframe.in_seconds() < 300` → no render.
- `Today` on daily-or-higher charts naturally yields ~0 bars → guarded out
  (expected; "Today" is an intraday concept).

## Trade-offs

- `1 Month` at 5-min still partially truncates against the 5000-bar cap; accepted.
- On the last bar, a large window (up to ~5000 bars × up to 100 rows) is heavier
  to compute, but only on the final bar and within Pine's loop limits.

## Out of scope

- No Pine v5 → v6 migration (file stays v5).
- No change to profile rendering, sentiment, heatmap, or POC logic beyond the
  `pLST`/`pHST`/`pSTP` relocation.
