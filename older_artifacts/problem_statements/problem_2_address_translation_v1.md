# Problem 2 — Address Translation for CSP (Point B: Partner's Decision)

**Contract type:** Gate 0 thinking contract (per `../Gate 0 Submission Template (explained).docx`)
**Owner:** Maanas
**Narrator:** `story_teller_part1`
**Drafted:** 2026-04-20
**Parent synthesis:** `../README.md` (cross-engine flow + three-engine findings)
**Primary engine this addresses:** `../coordination/` (transcript-level ground truth)
**Secondary engines:** `../allocation_signal/` (partner notification payload) and `../promise_maker_gps/` (text address captured at flow step 8)

---

## Framing — where this problem sits

Satyam's decomposition:

> There are two decision points: **Point A** where Wiom makes a promise using GPS location, and **Point B** where the partner makes a decision. Three parties are involved: Wiom, partner, customer.
>
> Two guiding questions:
> 1. What is the best way to take location from the customer? ← Problem 1
> 2. **How do we ensure consistency / understanding of the location across all parties?** ← this contract (Problem 2)

**This contract is about Point B** — the partner's decision (notification accept/decline, then on-call coordination, then physical navigation to the home) — and the **translation** of the location signal from Wiom to the partner to the customer and back. The three parties are:

| Party | What they hold at the start of Point B |
|---|---|
| **Customer** | The truth — they know their own address |
| **Wiom** | A captured GPS (step 4) + an unstructured text address string (step 8, post-payment) |
| **Partner (CSP)** | At notification time (step 10): a map image + straight-line distance + their own install history. **The text address is not shown until they click through.** At call time (step 14): the text address + voice conversation with the customer to resolve it |

The signal degrades in translation at every handoff: customer head → text field → notification map → call conversation. Each handoff is a bottleneck.

---

## SECTION A — Problem Definition

### 1. Observed / Expected / Evidence

**Observed** (from Satyam):
> CSPs frequently misinterpret user address provided by system, leading to incorrect installation decisions or delays.

**Observed** (quantified from `../coordination/`, Delhi Jan-Mar 2026 non-BDO, n = 2,561 pairs / 4,930 calls):
- **Avg calls per (mobile, partner) pair = 1.92** (4,930 calls / 2,561 pairs). If the address were clear at notification, most pairs would need one or zero calls, not two.
- **70% of pairs have >1 distinct reason across calls** — a single snapshot misses most of the address-resolution story.
- **Transcript-level address friction = 19-20% of calls** (vs dropdown rate of ~13%) — dropdown *under-counts* real address friction by roughly 2×.
- **Gali-stuck rate at call level: 7.4%** (364 / 4,930). At pair-level mode: 9.1% (232 / 2,561). Gali is the **single biggest call-level bottleneck** in the canonical landmark → gali → floor chain.
- Among 927 `address_not_clear` pairs: **41% never engage the gali step at all** — chain broke at or before landmark.
- Of 1,023 `address_not_clear` calls: **46% are one-sided** (partner confused, customer clear), 32% mutual, 20% resolved-eventually. Refutes "mutual breakdown" framing — partner-side parsing is dominant.
- `partner_reached_cant_find` at site arrival: 9.8% (active_base) / 11.1% (splitter). Breakdown peaks at the moment of arrival, not only pre-dispatch.

**Expected** (from Satyam):
> Address provided to CSP should be clear enough for correct install decision without clarification.

**Expected — quantified:**
- Avg calls per (mobile, partner) pair: <1.3 (from current 1.92)
- Gali-stuck call-level rate: <2% (from 7.4%)
- `partner_reached_cant_find` rate: <5% (from ~10%)
- Installed share of pairs with zero clarification calls: >70% (baseline TBD — needs one-call-zero-call install-rate re-slice)

**Evidence** (Satyam's list + where we measure it):

| Satyam's evidence item | Where we measure it | Current state |
|---|---|---|
| % installs delayed due to address confusion | `decision_to_install_hours` by primary_reason (`../coordination/` § 7) | Median by reason: `address_not_clear` = 21.4 h vs `partner_reached_cant_find` = 8.0 h. Ambiguous-address pairs take ~2.7× longer from decision to install. |
| % calls made for clarification | Calls per pair in `../coordination/pair_aggregated.csv` | **1.92 avg**, p90 = 4 calls, max = 24 calls |
| % failed installs due to location misunderstanding | Cross of `primary_reason = address_not_clear` × `installed = false` | 927 ANC pairs · not-installed share = 48.4%. Versus non-ANC pair not-installed share = 47.8%. So ANC doesn't *cause* the install failure in isolation, but it consistently lives in failing cohorts — more detail in the chain-engaged-vs-not cross-cut below. |

**Extra evidence from `../coordination/` worth front-loading:**

- **Chain engagement is protective (+10pp install)**: pairs that engage the landmark-gali-floor chain at any point install at 57.7% vs 47.8% for never-engaged (n=1,627). Floor-stuck pairs install at **73.9%** (partner at the door). The bottleneck is *getting on the chain at all*.
- **Crossed with polygon-side** (from `coordination/polygon_analysis/`): chain-engagement's protective effect is almost entirely inside-polygon (+11.2pp). The most dangerous cell anywhere in the coordination analysis: **gali-stuck × outside-polygon = 25.4% install** (+37pp below inside-polygon).

### The evidence cross-checks itself across engines

1. **`coordination/`:** transcript-level address friction is flat across distance/prob deciles — meaning partner-side parsing breaks regardless of geometric match quality. The fix is not ranking-the-right-partner (that's Allocation's job). The fix is giving *whoever the partner is* a cleaner address signal.
2. **`allocation_signal/`:** dropdown's 48%→2.5% prob-decile `address_not_clear` pattern was a decline-channel artifact, *not* a real per-call address-friction gradient. Partners facing the same underlying address friction click "address not clear" as a polite exit when they don't want the booking — the click is a disposal channel, not a content signal. So the Allocation engine cannot cleanly infer address quality from existing decline reasons.
3. **`promise_maker_gps/`:** the text address capture (step 8) happens *after* the booking fee is paid and is a *single free-text field*. There is no structured sub-field for landmark / gali / floor / pincode.

Three engines, one signal: the address is **captured unstructured, shown to the partner late, and forced to resolve on a voice call**.

---

## SECTION B — Project Definition

### 2. Objective

**Reduce address-driven coordination load, measured two ways:**
- **Primary:** Avg calls per (mobile, partner) pair: **1.92 → <1.3**
- **Secondary:** Gali-stuck call-level rate: **7.4% → <2%**
- **Tertiary:** `partner_reached_cant_find` site-arrival rate: **~10% → <5%**

These three metrics together cover the three translation failure modes: too many clarifications needed (primary), clarifications never reach the gali step (secondary), clarifications reach the door but still fail (tertiary).

### 3. Classification + Rationale

**Capability Build.**

Rationale (confirmed with Satyam):

- **Not Hygiene** — hygiene fixes something broken. The address capture and the notification payload are working as designed; the design does not include structured address or pre-click address visibility.
- **Not Efficiency** — efficiency improves an existing mechanism. We are adding a structured representation that does not exist today. There is no "faster" version of an unstructured free-text field.
- **Not Outcome Shift alone** — the outcome (install velocity, partner productivity) will shift, but the mechanism is a new system capability: a shared canonical address representation across Wiom, partner, customer.
- **IS Capability Build** — Wiom currently has **no structured address model**. Customer types freeform text; Wiom stores it; partner reads it; partner calls customer; partner mentally parses the spoken address into an internal landmark→gali→floor mental model. There is no system stock of structured address. Building one is genuinely new capability.

### 4. Root Cause

Structural, not superficial:

**Root cause:** **There is no shared canonical representation of the home's location across the three parties**, and the translation loses structure at every handoff.

The translation chain (from `../README.md` flow):

```
Customer (head)  →  App free-text field (step 8)  →  Wiom DB string
                                                           ↓
                                             Allocation notification (step 10)
                                                 ↓ (text hidden until click-through)
                                                Partner
                                                 ↓
                                       Voice call on locality/gali/floor (step 14)
                                                 ↓
                                              Technician
                                                 ↓
                                             Physical install
```

Contributing factors:
1. **Free-text field at step 8** — no structured capture of the canonical Delhi hierarchy (landmark → gali → floor). Customer's mental address model is compressed into a single string.
2. **Notification payload hides text address** — partner sees map + distance only until click-through (step 10). The accept/decline decision is made on geometry, not content. This is why `address_not_clear` reads as a decline-channel artifact in `../allocation_signal/` — partner hasn't seen the address when they decline.
3. **No pre-call structured transfer** — once the partner clicks in, they see the same free-text blob. They have no way to confirm the landmark/gali/floor *before* calling.
4. **Voice call is the only address-resolution channel** — 46% of ANC calls are one-sided (partner confused, customer clear). Customer already has the structure; we just haven't captured it.
5. **Floor detail surfaces only on the call** — height/wiring complexity (relevant for technician prep) is invisible to Allocation and to the partner at notification time.

### 5. Leverage Level

**LP4 — rule change + new information flow** (Meadows hierarchy).

Same level as Problem 1, complementary mechanism:
- Not LP2 (parameter change): tweaking notification text or adding a second free-text field doesn't change the structural representation.
- Not LP5 (system purpose change): Wiom's purpose stays the same.
- IS LP4 because we are changing **what information flows between the three parties** (structured address replacing free text, address visible at notification rather than at click-through, floor/landmark confirmed pre-call), and the **rules of partner-customer coordination** (call becomes a confirmation step, not a discovery step).

---

## SECTION C — Measurement

### 6. Measurement Stack

| Layer | Meaning | Metric for this project |
|---|---|---|
| **L5** — final outcome | Company-level value | Install throughput per partner-week (installs / partner-active-day) |
| **L4** — driver | System-level driver | Partner productivity (installs per unit partner time) |
| **L3** — **SIGNAL** | Fast measurable proxy | **% of (mobile, partner) pairs that install with ≤1 clarification call** (captures "address was clear enough without a back-and-forth") |
| **L2** — execution proof | Coverage of intervention | % of bookings with structured address fully populated (all required sub-fields non-null) |
| **L1** — system correctness | Wiring works | Structured capture widget serving; notification payload including structured address; partner UI rendering correctly |

### 7. Tracking Table

| Metric | Baseline | Target | Frequency | Source |
|---|---:|---:|---|---|
| Avg calls per (mobile, partner) pair | **1.92** | <1.3 | Weekly | `../coordination/pair_aggregated.csv` re-computed on post-intervention cohort |
| Gali-stuck call-level rate | **7.4%** | <2% | Weekly | `../coordination/flag_address_chain.py` re-run |
| `partner_reached_cant_find` rate | ~10% | <5% | Weekly | same |
| One-sided confusion rate within ANC | **46%** | <25% | Weekly | `../coordination/flag_comm_failure.py` re-run |
| Structured address coverage | 0% | >90% | Daily | New event in `booking_logs` for structured address submission |
| Pairs installing with ≤1 call | TBD (to baseline) | >70% | Weekly | `../coordination/pair_aggregated.csv` — add `n_calls ≤ 1 AND installed = 1` cut |

---

## SECTION D — Leading Signal (Critical)

### 8. Leading Signal

**% of (mobile, partner) pairs whose first partner-customer call either does not happen (address was clear) OR ends with the address chain fully resolved (landmark + gali + floor confirmed).**

In the existing `../coordination/` pipeline this maps to:
```
(no call recorded in UCCL with this partner as attributed owner)
    OR
(first call's addr_chain_stuck_at = 'none' AND primary_reason != 'address_not_clear')
```

Why *this* metric, not total calls per pair: total calls lags the install. The first-call-resolved signal fires right after the first call (within hours of dispatch), giving us fast read on whether the intervention is working.

### 9. Signal Validity

**Observability:**
- UCCL + Exotel + Whisper + Haiku pipeline is already built in `../coordination/`. No new infrastructure needed to measure.
- Per-pair signal available within ~24 hours of the first call (transcription lag).
- Parallel: structured-address-coverage (L2) observable in real time from the booking event stream.

**Causality:**
- Structured address captured upstream → partner sees landmark/gali/floor in notification → partner confirms address pre-call (possibly no call needed) → fewer clarification loops → fewer gali-stuck calls → shorter decision-to-install time
- Causal chain passes through the same bottleneck (gali resolution) that `../coordination/` empirically identified as the biggest single call-level friction point (7.4%).

**Sensitivity:**
- Intervention directly changes what the partner sees *before* calling. Any sensitivity of the first-call-resolved rate to address clarity should be visible.
- Dose-response: pilot with landmark-only → pilot with landmark+gali → full landmark+gali+floor. Metric should improve monotonically.

### 10. Signal Timing

**First-call-resolved rate:** observable within **~24-48 hours** per booking (call + transcribe + classify).
**L3 (pairs installing with ≤1 call):** observable within **2-4 weeks** (install lookahead).
**L5 (install throughput):** observable within **4-8 weeks** (requires partner-week baselines post-intervention).

### 11. Scope Constraint

**Yes.** First-call-resolved fires within days of any booking. The coordination pipeline processes ~4,930 calls in ~90 minutes on the current config — rerun cadence is daily-capable.

---

## SECTION E — Ownership & Mapping

### 12. Owner

**Maanas** (one person, not a team).

### 13. Driver Mapping

**Install velocity + partner productivity.**

Downstream beneficiaries:
- Allocation (`../allocation_signal/`) — decline decisions become more content-aware (partner declines because they *saw* the address and decided not to take it, not because they used the dropdown as an exit)
- Promise Maker (`../promise_maker_gps/`) — if structured address is collected *pre-promise* (a sub-option of this project, see risk section), it becomes a cross-validator for Problem 1

### 14. NUT Chain

```
Structured address + partner-visible pre-click
    ↓
First-call-resolved rate rises (L3 signal)
    ↓
Clarification calls per install drop (L4 driver)
    ↓
Partner time per install drops; more installs per partner-week
    ↓
Install throughput rises; partner active-base grows (retention)
    ↓
Net installed paying customers (company value)
```

*(NUT = Net installed paying customer revenue. Same placeholder as Problem 1 — override with Wiom's canonical NUT if different.)*

### 15. Validation Path

**If L3 signal moves as predicted:**

1. Structured address capture coverage (L2) reaches >90%
2. First-call-resolved rate rises (leading signal)
3. Avg calls per pair drops (L3)
4. Gali-stuck and `partner_reached_cant_find` drop (tertiary metrics) — these are the ground-truth ratchets from `../coordination/`
5. Install throughput rises (L4/L5)

**Disconfirmation paths:**
- If L2 hits >90% but the leading signal doesn't move → partners are ignoring the structured address (not trusting it, or the notification UI is not surfacing it well). Fix is UI/partner training, not capture.
- If the leading signal moves but gali-stuck doesn't → the structured capture isn't capturing *gali* specifically (landmark and floor improve, gali doesn't). Need taxonomy revision.
- If everything moves but L5 doesn't → the time saved is not being converted to more installs. Partner task-routing is the next bottleneck — hand off to a future engine (Partner Management).

---

## SECTION F — Execution

### 16. Time Class

**Capability Build → 2-3 sprints.**
- Sprint 1: define structured address schema (landmark / gali / floor / pincode + free-text overflow) using `../coordination/` transcript taxonomy as ground truth; build customer-side capture UI
- Sprint 2: update notification payload to include structured address pre-click; build partner-side UI for pre-call confirmation
- Sprint 3: roll out, monitor, iterate

### 17. Execution Plan

| Step | Agent does | Human does |
|---|---|---|
| 1 | Pull landmark / gali / floor taxonomy from `../coordination/` transcripts — which actual landmarks (chowk, mandir, market, metro, school), gali naming conventions, floor references (manzil, chhat, kothi, ground) show up most frequently. Emit a frequency table. | Maanas + Wiom product: decide schema (required vs optional sub-fields) |
| 2 | Draft structured capture UI copy and field definitions | Wiom product + design: partner-review UI |
| 3 | Instrument structured capture event in `booking_logs` (new event or extended payload) | Wiom engineering |
| 4 | Instrument notification payload to include structured address + small map with landmark pin (not just straight-line distance) | Wiom engineering |
| 5 | Build partner-side "confirm address before calling" flow | Wiom product + partner-app engineering |
| 6 | Re-run `../coordination/` pipeline weekly on post-intervention cohort; emit weekly L2/L3/L4 tracking table | Maanas reviews, iterates on schema |

*(Specific anchor set, feedback-loop mechanics, and external-tool choices — design choices explored in the sibling solution synthesis, not in this contract.)*

### Decision point mid-build — where to capture structured address

**Option A (conservative):** Capture structured address at current step 8 (post-payment, current timing). Low risk; does not change the promise-making gate. Limits Problem 1 complementarity.

**Option B (bold):** Capture structured address **between step 4 (home GPS) and step 6 (booking fee)**. Allows cross-validation of GPS against address pre-promise — directly complements Problem 1's pre-promise validator. Higher design risk: longer flow to commitment, potential drop-off.

**Recommendation (to be confirmed with Satyam + Wiom product):** pilot Option B in one city after Sprint 1 evidence suggests the schema is workable. Fall back to Option A if drop-off is material.

---

## SECTION G — Learning Logic

### 18. Hypothesis

**If we replace the free-text address field with a structured capture (landmark + gali + floor + pincode), AND propagate that structured address into the partner's notification payload so it's visible pre-click, then:**
- **avg calls per (mobile, partner) pair will drop from 1.92 to <1.3**
- **gali-stuck call rate will drop from 7.4% to <2%**
- **`partner_reached_cant_find` site-arrival rate will drop from ~10% to <5%**
- **within 6 weeks of full rollout**

Mechanism: the three-party translation loses structure at every handoff today. Structuring upstream and making it visible downstream preserves structure across the chain. Specific schema, anchor set, and feedback-loop design are design choices explored separately (see sibling solution synthesis, not this contract).

### 19. Risk Check

| Risk | Mitigation |
|---|---|
| Customer drop-off if structured capture flow is too long | A/B test schema variants (3-field minimal vs 5-field full); measure completion rate before payment step |
| Taxonomy too rigid — not every address fits landmark→gali→floor (e.g., gated societies, standalone kothis) | Free-text overflow field preserved; structured fields optional but nudge-required. `../coordination/` transcript data shows this is the dominant Delhi pattern but not exclusive. |
| Partner adoption — partners may still call even with structured address, out of habit or skepticism | Sprint 3 partner training. Partner-side UI shows "this address has been confirmed structurally" with timestamp. |
| Address still doesn't match physical reality (customer enters wrong landmark) | Cross-check against map landmarks via reverse-geocode; flag mismatches pre-promise. This overlaps with Problem 1's validator — the two projects share infrastructure. |
| Gali is the hard one — no canonical gali registry exists in Delhi | Seed with a partner-sourced registry (partners who've worked an area can suggest canonical names). Donna's neighborhood-memory artifact concept from `../coordination/` recommendations is the systems-level fix. |
| Problem 1 solves the GPS but Problem 2's structured address doesn't land — we end up with a clean coord next to an ambiguous address | Schema design must include `address_confirmed_via_ssid_match` field that gets set when install fires, closing the loop over time and creating the neighborhood-memory stock |
| L3 moves but L5 (throughput) does not | The bottleneck has shifted further downstream — partner task-routing, or technician scheduling. Hand off to a future engine. |

### 20. Learning Path

| Outcome | Decision |
|---|---|
| L2 coverage >90% + L3 signal rises + L5 throughput rises | **Scale** — roll out to all cities. Consider Option B (pre-promise capture) next. |
| L2 coverage >90% + L3 signal rises + L5 flat | **Partial win** — coordination friction reduced; install throughput bottleneck is further downstream. Investigate partner task-routing / technician scheduling. |
| L2 coverage >90% + L3 signal flat | **Partners aren't using the structured address.** Investigate partner UI, partner trust, or schema quality. Possible remedy: show partner *why* the address is confirmed (e.g., "pincode verified against reverse-geocode"). |
| L2 coverage <90% | **Customer-side capture is failing.** Simplify schema, reduce required fields, re-test. |
| L3 moves but gali-stuck doesn't | **Taxonomy is wrong at the gali level.** Re-pull `../coordination/` transcript taxonomy with focus on gali-naming patterns; partner-sourced canonical registry. |

---

## FINAL RULE (per template)

- ✅ Clear problem: 1.92 calls per pair, 7.4% gali-stuck, 46% one-sided confusion — all from transcript ground truth, not dropdown proxies
- ✅ Measurable signal: first-call-resolved rate (real-time), avg calls per pair (weekly)
- ✅ Testable hypothesis: structured address + pre-click visibility → call volume and gali-stuck drop in 6 weeks

**This is a project.**

---

## Open pre-requisites before build starts

| Pre-requisite | Sits in | Blocks |
|---|---|---|
| Landmark / gali / floor taxonomy frequency table from `../coordination/` transcripts | `../coordination/` (partial — `flag_address_chain.py` already tags; needs an aggregation by value) | Structured capture schema design |
| Partner-side UI research — do partners *want* structured address, or will they prefer free-text-plus-voice-call? | Wiom product research | Partner-side UI design (Sprint 2) |
| Decide Option A vs Option B (capture timing — post-payment vs pre-promise) | Satyam + Wiom product | Sprint 1 schema scope |
| Re-compute install-rate by n_calls bucket in `../coordination/pair_aggregated.csv` | `../coordination/` | L3 baseline for "pairs installing with ≤1 call" |

---

## Cross-link: relation to Problem 1

Problem 1 solves the **input quality at Point A** (GPS capture before promise).
Problem 2 solves the **signal consistency across parties between Point A and Point B** (structured address, visible at notification time).

The two problems share infrastructure:
- A **pincode / reverse-geocode validator** serves both (Problem 1 uses it for GPS cross-check; Problem 2 uses it for landmark confirmation)
- A **shared canonical address representation** is built once (Problem 2) and consumed by both promise-making (Problem 1 extension) and allocation/coordination (this contract)

Solving only Problem 1 → cleaner GPS but still ambiguous text address; partner still calls to resolve gali and floor.
Solving only Problem 2 → cleaner address but GPS still drifts; partner arrives at the wrong block despite perfect address.
Solving both → the three parties hold the *same* location model, at the *same* quality, at every handoff.

Joint storyline in `../README.md` once both contracts ship.
