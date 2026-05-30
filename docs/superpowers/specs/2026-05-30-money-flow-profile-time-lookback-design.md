# Money Flow Profile — Time-Based Lookback

**Date:** 2026-05-30
**File:** `scripts/LuxAlgo/00_money_flow_profile.pine` (Pine Script v5)

## Goal

Let the profile's lookback range be defined by a **calendar window** — the
current session ("Today") or a rolling number of **days** — instead of only a
fixed bar count. The existing fixed-bar behavior stays available via a mode
selector.

## Decisions

| Question              | Decision                                                          |
|-----------------------|-------------------------------------------------------------------|
| Input shape           | `Lookback Mode` = `Fixed Bars` \| `Today` \| `Days`, **default `Today`** |
| Days input            | Integer `Lookback Days`, `minval = 1`, `maxval = 28`              |
| "Today" definition    | Bars since the current trading **session open** (`session.isfirstbar`) |
| Bar-cap handling      | Raise `max_bars_back` 1500 → 5000, then clamp to available history |
| Small-timeframe rule  | None — always render; clamp silently to whatever history fits     |

## New Inputs

- `Lookback Mode` — `input.string('Today', options=['Fixed Bars','Today','Days'])`
- `Lookback Days` — `input.int(7, minval=1, maxval=28)` (used when mode = `Days`)
- `Fixed Lookback (bars)` — the existing fixed input, relabeled, `maxval` raised
  to 5000 (used when mode = `Fixed Bars`).

## Computing `rpLN` (bar count) — all resolved on the last bar

**Convention:** `rpLN` is a bar **offset**, not a cardinality. It equals
`(number of bars in window) - 1`, and the script scans offsets `0..rpLN`
(i.e. `rpLN + 1` bars). All modes follow this so that identical ranges yield
identical `rpLN` and therefore byte-identical output to the current Fixed-Bars
method.

- **Fixed Bars** → unchanged: `last_bar_index > rpFIX ? rpFIX - 1 : last_bar_index`.
  ("200" → `rpLN = 199` → 200 bars scanned.)
- **Today** → track session start globally:
  `var int tdStartIdx`; `if session.isfirstbar => tdStartIdx := bar_index`.
  Then `rpLN = last_bar_index - tdStartIdx`.
- **Days** → `target = time - rpDAYS * 86400000` ms. Walk back on the last bar,
  storing the **offset** of the furthest in-window bar:
  `for i = 1 to min(bar_index, 4999): if not na(time[i]) and time[i] >= target => rpLN := i, else break`.
  (`rpLN` ends as the largest offset still inside the window = bar count − 1.)
- Clamp final `rpLN` to `[0, min(last_bar_index, 4999)]`. A value of `0` falls
  through the existing `rpLN > 0` render guard (no profile drawn).

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
   d. existing render guard keeps `rpLN > 0 and pSTP > 0` so degenerate windows
      draw nothing. Everything below the guard is unchanged.

## Guards

- Existing seconds-timeframe skip is kept.
- `Today` on daily-or-higher charts naturally yields ~0 bars → guarded out
  (expected; "Today" is an intraday concept).
- Large `Lookback Days` on small timeframes is **not** blocked; it clamps to the
  5000-bar cap / available history. The profile-high label's "Number of bars"
  tooltip reports the actual bars used, so truncation is visible.

## Trade-offs

- A clamped Days window (e.g. 28 days on 1-min) silently shows a partial window;
  accepted, surfaced via the existing bar-count tooltip.
- On the last bar, a large window (up to ~5000 bars × up to 100 rows) is heavier
  to compute, but only on the final bar and within Pine's loop limits.

## Out of scope

- No Pine v5 → v6 migration (file stays v5).
- No change to profile rendering, sentiment, heatmap, or POC logic beyond the
  `pLST`/`pHST`/`pSTP` relocation.
