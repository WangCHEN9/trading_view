# Thesis-Trade Playbook (Domain-Edge Trading)

For trading tech/auto where **your edge is sector knowledge**, not a price indicator. The thesis is the edge; the toolkit is execution + risk + verification. This is the legitimate version of "use the tools" — your analysis decides *what* and *why*, the machine decides *how much* and enforces *when to quit*.

---

## The non-negotiable guardrails

1. **Public information + your analysis only. Never MNPI.** Trading on material non-public information from your job is insider trading — illegal. If you have private info on a name, or you're in a blackout window, **do not trade that name.** Your edge is *better analysis of public data*, not secret data.
2. **"Is it already priced in?"** Your knowledge is edge only where your view *differs from consensus and you're right*. Before every trade, state what consensus expects and why you disagree. If you can't articulate the disagreement, there's no edge — skip it.
3. **Sector concentration = correlated risk.** Your whole book is tech/auto. A sector selloff hits every position at once. Cap total sector exposure (see risk rules). Don't confuse 6 positions for diversification when they're all the same bet.

---

## The thesis-trade workflow

Every trade fills out this card *before* entry. If you can't complete it, don't trade.

### 1. Thesis (your edge — be specific & falsifiable)
- **Name + direction:** e.g. "Long XYZ"
- **The view:** one sentence on what you believe and why your sector knowledge gives you an edge. e.g. *"XYZ's next-gen product ramps faster than the Street models because [public supply-chain / demand signal you understand better than analysts]."*
- **Catalyst + timeframe:** what makes the market re-price, and by when (earnings, product launch, guidance, industry data print). No catalyst → it can stay mispriced indefinitely.

### 2. Consensus & disconfirmation (the honesty check)
- **What does consensus expect?** (analyst estimates, the prevailing narrative)
- **Why are you right and they're wrong?** (your specific informational/analytical edge)
- **What would prove you wrong?** (a falsifiable condition — forces intellectual honesty)

### 3. Execution (the toolkit — time the entry, don't chase)
- Use the structure / VWAP / value tools (`mtf_structure_value`, Order Flow VWAP σ-bands, SMC structure) to enter on a **pullback to value or a structure confirmation** in the thesis direction — not by chasing a green candle.
- Wait for price to come to you. A good thesis with a bad entry is a mediocre trade.

### 4. Risk (the math — non-negotiable, machine-enforced)
- **Technical stop ≠ thesis invalidation.** Separate them: the *stop* is where the chart says the timing is wrong; the *thesis* is invalidated by a fundamental disconfirmation. Place the hard stop at a structural level; if the thesis breaks fundamentally, exit regardless of price.
- **Position size:** `shares = (account × 1–2% risk) / (entry − stop)`. Use the strategy scripts' sizing math.
- **Reward:risk ≥ 2:1** vs your thesis price target.
- **Sector cap:** total tech/auto exposure ≤ ~50% of capital; max ~6 positions; size down when positions are highly correlated (e.g. two semis on the same demand thesis = really one bet).

### 5. Review (verify the edge is real)
After the trade closes, log: was the **thesis** right? was the **timing** right? They're independent — you can be right on the company and wrong on the entry, or vice versa. Tag each trade:
- Thesis ✓/✗ · Timing ✓/✗ · R-multiple result

---

## Measuring whether your edge is real

After ~30–50 thesis trades, split the journal:

| | Thesis ✓ | Thesis ✗ |
|---|---|---|
| **Timing ✓** | the goal — both right | study: good entry, wrong view |
| **Timing ✗** | study: right view, fix entries | both wrong — skip these setups |

- If your **thesis hit-rate** is meaningfully > 50% with positive avg R → **your domain edge is real.** Scale slowly.
- If thesis ✓ but timing ✗ dominates → the edge is real but you're entering badly → lean harder on the execution tools.
- If thesis hit-rate ≈ 50% → your "edge" is priced in / illusory → back to indexing for the core. No shame; most insiders are here.

**This split is the whole point.** It separates "do I know the sector" (probably yes) from "can I make money on it" (unproven until measured). A poker player knows the difference between a good read and a winning session — same discipline here.

---

## What the toolkit does in this workflow

| Tool | Role in a thesis trade |
|---|---|
| Your sector knowledge | **The edge** — what & why |
| `screener_*` | Surface names in your sectors at actionable technical setups |
| `mtf_structure_value`, Order Flow VWAP | Time the entry to value/structure (step 3) |
| Strategy sizing math | Compute exact share count from your stop (step 4) |
| Backtest harness | NOT for the thesis (can't backtest your analysis) — only sanity-checks the *technical* entry timing |
| The journal split above | Verify the edge is real (step 5) |

The mechanical strategies we built and their backtests are now **demoted to execution helpers** — they don't generate the edge, they help you enter and size cleanly once your thesis says go.

---

## Honest expectation

Industry knowledge genuinely *can* produce edge — but most insiders don't beat the market, usually because their knowledge is priced in or they over-concentrate emotionally. The thesis/timing journal is the referee. Trade small until the split table proves your thesis hit-rate is real. If it is, tech/auto is your soft table and this is how you press it.
