# Geoff + Donna critiques — full transcripts + synthesis

**Date:** 2026-04-20
**Parent:** `partner_customer_calls/` (Jan-Mar 2026 Delhi non-BDO call-transcript analysis).
**Context sent to agents:** full funnel numbers (6,951 master → 2,561 pair-level), reason distribution, comm_quality drill-down, decision→install gap, splitter vs active_base signal, the proposed "pre-dispatch address-capture" landing.

---

## What is "46/32/22"?

Shorthand for the `address_not_clear` drill-down using comm_quality tagging on the 1,023 unique calls primarily classified as address_not_clear:

| comm_quality tag | n | % | install rate |
|---|---:|---:|---:|
| **one_sided_confusion** — partner confused, customer clear | **471** | **46.0%** | 54.6% |
| **mutual_failure** — both parties struggle | **322** | **31.5%** | 48.4% |
| **clear** — partner resolved it within the call | **209** | **20.4%** | 62.2% |
| not_applicable | 21 | 2.1% | — |

I rounded 20.4% + 2.1% to "22" when saying 46/32/22. Precise: 46 / 32 / 20 / 2.

This is the key finding my analysis landed on: the dominant address-friction pattern (46%) is **partner-side parsing difficulty on addresses that customers gave clearly**, not mutual communication breakdown (32%).

Both agents challenge the magnitudes (not the direction) — see their critiques below.

---

## Are they saying pin-drop is not convincing?

**Yes, both agents push back on pin-drop as THE lever, for different reasons:**

### Geoff's push-back on pin-drop

- Pin-drop + Places autocomplete solves the 46% one-sided parsing subset — partner can parse once a coordinate is provided.
- **It does nothing for the 41% on-site mutual-failure cohort** (within `partner_reached_cant_find`). Those calls already have coordinates — partner is physically there, standing at the pin, and STILL can't meet the customer. Address doesn't resolve to a findable location even with ground truth.
- Also doesn't help customers whose physical premises lack signage / numbering / landmarks.
- His deeper point: the real upstream lever may be **Promise Maker — who gets promised service in what territory**. Splitter +4pp friction is structural, not an address-capture problem.

### Donna's push-back on pin-drop

- Hard gate on pin-drop creates a **gaming feedback loop**:
  - Gate booking on pin → customers drop ANY pin to pass → partner arrives wrong location → partner distrusts pins → reverts to voice-parsing → WORSE than baseline because partner stopped pre-calling.
- Recommends **soft nudge with reverse-geocode sanity check against pincode** instead of hard gate.
- Pin-drop helps arrival (reduces the first leg of a journey) but doesn't solve the **last-100-meters problem** — which is where mutual failure actually peaks (41% on-site vs 32% pre-dispatch).

**Bottom line:** pin-drop addresses ~46% of the address_not_clear cohort (the one-sided partner parsing slice) at best, and creates gaming risks if implemented as a hard gate. It's one useful lever, not the full answer.

---

## Are they saying partner may not remember the area if a lead comes from it again?

**Yes — this is Donna's sharpest point.**

Her framing (systems lens):

> "The real stock is neighborhood-level parsing knowledge — held partially in partners' heads, partially in the customer's ability to self-describe, **zero in the system itself**."

Specifically:
- A partner who burned 21h solving "Gali No. 4, near mandir" gets NO artifact from the system.
- Next booking on the same gali → same confusion, from scratch.
- The partner IS the stock. The stock evaporates on shift-end — or when the booking goes to a different partner who has never been there.
- A partner's personal memory degrades; someone else's is zero.

So yes — **system has no memory of resolved address quirks**. That's the stock-with-no-inflow problem. Every address-friction event is solved from scratch and the solution is thrown away.

Donna's recommended intervention explicitly addresses this:
> "Neighborhood-level address artifact — first partner to resolve a cluster's quirks writes a 2-line note ('gate is behind the mandir, not front'), surfaced to next partner assigned there. **Converts partner-memory into system-stock**."

Risk she flags: stale-note decay. Notes age; the mandir gets repainted. Track note-age vs install-rate, expire aggressively.

---

## What are they asking to do now?

Both agents give concrete follow-up tests. Two are label-validation checks; two are hypothesis-sharpening analyses.

### Geoff's asks

**G1. Dual-blind re-label 200 `address_not_clear` transcripts** for inter-rater reliability on the one_sided-vs-mutual distinction.
- 100 by a second Haiku run with a different prompt framing (check intra-model stability)
- 100 by a human local to Delhi (check model vs ground truth)
- **Pass/fail criterion:** Human agreement on "partner is the confused party" ≥ 70% → bank the 46% headline. < 70% → kill it.

**G2. Separate splitter-area effect from partner-familiarity effect.**
- Among splitter-area calls, does install rate vary by the partner's *tenure in that specific splitter area*?
- If tenured splitter partners still fail at ~same rate → territorial-encoding problem (fix = address infrastructure upstream, Promise Maker gating).
- If tenured partners succeed → partner-familiarity problem (fix = training / matching).

### Donna's asks

**D1. Re-run comm_quality install rates CONDITIONAL on call number** (call 1 vs call 2 vs call 3+).
- Tests saturation bias: multi-call pairs may be a distressed sub-population.
- Prediction: mutual_failure install rate drops from ~48% → ~35% for pairs with 3+ calls.
- If true, mutual_failure is a SYMPTOM stock (late-pair distress) not a root cause.

**D2. Check partner-persistence / fatigue hypothesis.**
- Does install rate within `address_not_clear` correlate with the partner's *n-th task of the day*?
- If yes → the drain is task-fatigue, not address-complexity.
- This reframes the 59% install rate — it's not "address_not_clear is surmountable," it's "partner persistence is the scarce resource."

### Systemic intervention proposals (vs current "pin-drop" framing)

| Source | Intervention | Addresses |
|---|---|---|
| Geoff | Promise Maker territorial gating — don't promise service in under-encoded areas without caveats | Splitter +4pp structural friction |
| Geoff | Build in reverse-geocode sanity check (pincode match) rather than hard pin-drop gate | Closes the gaming loop Donna flagged |
| Donna | Neighborhood-level address artifact store — partner writes resolved notes; next partner to that cluster sees them | Converts partner-memory (leaky stock) to system-memory (durable stock) |
| Donna | Track note-age vs install-rate to detect stale notes; auto-expire | Prevents stale-note decay |

---

## Full critiques (verbatim)

### Geoff

> # Pain Point (restated)
>
> You're claiming: *"Address_not_clear is dominantly a partner-side parsing failure (46%), not a customer-side articulation failure, and the lever is pre-dispatch address capture."*
>
> I'll critique this before decomposing further, because the critique changes what the pain point even is.
>
> ---
>
> ## 1. Is the 46/32/22 decomposition sound?
>
> **Partially. The labels are doing more work than they can bear.**
>
> "one_sided_confusion: customer clear, partner can't parse" — Haiku is inferring intent from a transcript. But consider the failure modes:
>
> - **Observer-effect bias.** A customer who *sounds* clear on a recorded call may have given a *locally* correct address ("behind Sharma dairy, second gali") that is unparseable *without territorial priors*. That's not the partner being bad at parsing — that's the address itself being illegible to a non-local. The label blames the partner; the reality is the address schema.
> - **Asymmetric verbosity.** One-sided labels likely over-fire when the customer talks more. Partners often go silent when lost. Silence reads as "confused" to an LLM; fluency reads as "clear." You may be measuring *who talked*, not *who understood*.
> - **46% vs 32% is not a large gap given Haiku's label noise.** Without an inter-rater reliability check (Haiku vs Haiku on the same transcript, or Haiku vs human on ~100), you don't know if the 14pp gap survives ±10pp label noise.
>
> **I'd trust the direction, not the magnitude.** Partner-side difficulty is real. Whether it's 46% or 35% or 55% is unresolved.
>
> ## 2. Splitter +4pp + one-sided dominance = partner territorial unfamiliarity?
>
> **Competing explanation you haven't ruled out: splitter areas have worse address infrastructure, not worse partner familiarity.**
>
> Splitter areas are, by definition, newer expansion zones. They likely have: fewer Google-mapped landmarks, more informal naming, more under-construction plots, less settled gali numbering. A *local* partner in a splitter area would still struggle because the *territory itself* is under-encoded, not because the partner is unfamiliar with it.
>
> Test to separate these: among splitter-area calls, does install rate vary by *partner tenure in that splitter*? If tenured splitter partners still fail at the splitter rate, it's territorial encoding, not familiarity. If they succeed, it's familiarity.
>
> The on-ground contrast is the sharper signal: **mutual_failure 41% on-site vs 32% pre-dispatch**. That says the address problem gets *worse* when the partner is physically there. That's not a parsing problem — that's a *reality* problem. The address genuinely doesn't resolve to a findable location even with ground truth. This weakens the "partner can't parse" story considerably.
>
> ## 3. Is pre-dispatch address capture the right lever?
>
> **It's *a* lever. I don't think it's *the* lever.**
>
> Pin-drop + Places autocomplete solves the *partner-parsing* slice (maybe 46%, maybe less). It does nothing for:
> - The 41% on-site mutual-failure cohort — they have coordinates and still can't meet.
> - Customers whose *physical premises* lack signage, numbering, or landmarks.
> - Splitter areas where the pin-drop lands on an unmapped road.
>
> The deeper upstream lever you may be missing: **who is being promised service in what territory**. If splitters carry +4pp friction *structurally*, that's a promise-maker input, not an address-capture input. Pre-dispatch capture is downstream of the decision to say yes.
>
> ## 4. Edges where the conclusion breaks
>
> - Haiku labels correlate with install outcome (clear=62%, one-sided=55%, mutual=48%) — suspiciously monotonic. Either the labels are valid, *or* Haiku is peeking at call-length/tone proxies that also predict install. Check: does label predict install *after* controlling for call duration and word count?
> - "CONNECTED ≡ recording" — good. But the 27% install rate on UCCL-row-no-recording cohort is suspicious. Are these systematically different customers, or a recording-infrastructure artifact?
> - Jan/Feb ingestion gaps mean your 2,561 pairs skew March-heavy. March conclusions may not generalize.
>
> ## 5. The one experiment
>
> **Dual-blind re-label 200 address_not_clear transcripts: 100 by a second Haiku run with a different prompt framing, 100 by a human local to Delhi.** Measure:
> - Haiku-vs-Haiku agreement (label stability)
> - Haiku-vs-human agreement on one_sided_confusion specifically
> - Among human-confirmed one_sided, is the "confused party" actually the partner? (Your headline claim.)
>
> If human agreement on "partner is the confused one" is below 70%, the 46% headline dies. If above 85%, you can bank it.
>
> ---
>
> **Bottom line:** Your direction is defensible. Your magnitudes are fragile. Your intervention is too narrow. Don't commit to "pre-dispatch capture" as THE lever until you've separated *address schema quality* from *partner parsing ability* — they look identical in transcripts but have completely different fixes.

### Donna

> # Donna's Critique: The Address-Friction Story
>
> Maanas, I've read your numbers three times. The story is *almost* right, but it's papering over structural questions. Let me map it.
>
> ## 1. Stocks and flows: where does address-difficulty accumulate?
>
> The framing treats address-friction as a call-level event. Wrong level. The real **stock is neighborhood-level parsing knowledge** — held partially in partners' heads, partially in the customer's ability to self-describe, zero in the system itself.
>
> **Inflows:** new bookings in unfamiliar geographies, splitter partners entering new territory (+4pp confirms this).
> **Outflows:** partner repeat-visits to same cluster (learning), customer learning to send pin.
> **Critical leak:** the system has **no memory**. A partner who burned 21h solving "Gali No. 4, near mandir" gets no artifact. Next booking on same gali, same confusion. That's not a bug in a call — that's a missing stock.
>
> **Disagreement with your landing:** calling it "46% partner-side parsing" understates this. It's not that partners are bad parsers; it's that **the system discards parsing work after each call**. The partner is the stock, and the stock evaporates on shift-end.
>
> ## 2. Pre-dispatch pin-drop as the lever — partially agree
>
> Agree it addresses the 46% one-sided subset (install 55%). Disagree it's the highest-leverage move.
>
> **Feedback loops activated:**
> - *Reinforcing (good):* better pins → faster arrivals → partner trust in pins → partner relies on pins → demands them more.
> - *Reinforcing (bad, your gaming concern is real):* gating booking on pin → customers drop any pin to pass → partner arrives wrong location → partner distrusts pins → back to voice-parsing → worse than baseline because partner stopped pre-calling.
>
> The 8h decision-to-install for `partner_reached_cant_find` tells me **on-site recovery is already fast**. The expensive stock is the 21h on `address_not_clear` — pre-dispatch. So yes, intervene pre-dispatch, but **not with a hard gate**. Soft nudge with verification (reverse-geocode sanity check against pincode).
>
> ## 3. The 40% mutual-failure rate — you're hiding selection bias
>
> Pairs with multiple calls are **not** the same population as single-call pairs. A pair that called 4 times is conditionally a pair where something already went wrong. Pair-level primary_first collapses this.
>
> **Specific challenge:** what fraction of the 2,561 pairs are multi-call? If call-count correlates with mutual_failure, you're measuring **pair distress**, not communication quality. Re-run comm_quality install rates *conditional on call number* (call 1, call 2, call 3+). I'd bet the 47% install on mutual collapses to ~35% for pairs with 3+ calls — meaning mutual_failure is a **symptom stock**, not a cause.
>
> ## 4. Surmountable vs terminal — the missing variable is partner persistence
>
> 59% install on `address_not_clear` is impressive *only if* you control for partner. My hypothesis: the 59% who resolve share a small set of high-persistence partners. The 41% drop is where partner-persistence stock is depleted — late in shift, high task-load, splitter on unfamiliar ground.
>
> **Ask the data:** does install-rate-within-`address_not_clear` correlate with partner's *nth task of the day*? If yes, the drain is task-fatigue, not address-complexity.
>
> ## 5. `partner_reached_cant_find` > `address_not_clear` in mutual failure (41% vs 32%)
>
> This is your most interesting finding and you underplayed it. Pre-dispatch, the customer has time and is motivated — mutuality is achievable. **On-site**, partner is rushed, customer is confused about what landmark partner sees, and the conversation collapses faster.
>
> **Implication:** the breakdown lives **on-site, under time pressure**, not in the pre-dispatch call. Which weakens the pin-drop-at-booking thesis slightly — pins help arrival, but the last-100-meters problem is different.
>
> ## Recommendation
>
> **Intervention:** neighborhood-level address artifact — first partner to resolve a cluster's quirks writes a 2-line note ("gate is behind the mandir, not front"), surfaced to next partner assigned there. Converts partner-memory into system-stock.
>
> **Risk to measure:** stale-note decay. Notes written 6 months ago mislead when the mandir is repainted. Track note-age vs install-rate; expire aggressively.
