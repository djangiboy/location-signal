# Problem 2 — Address Translation for CSP (Point B: Partner's Decision) — v2

**Contract type:** Gate 0 thinking contract (per Wiom's Gate 0 Submission Template).
**Owner:** Maanas
**Drafted:** 2026-04-21
**Primary engine this addresses:** Wiom's Coordination engine (call-transcript ground truth).
**Secondary engines:** Allocation (notification payload) + Promise Maker (text address at flow step 8).
**Data backbone:** `master_story.md` + `master_story.csv` (shared alongside).

---

## Framing — where this problem sits

Satyam's decomposition:

> Two decision points: **Point A** where Wiom makes a promise using GPS, and **Point B** where the partner makes a decision. Three parties: Wiom, partner, customer.
>
> Two guiding questions:
> 1. What is the best way to take location from the customer? ← companion contract
> 2. **How do we ensure consistency / understanding of the location across all parties?** ← this contract

This contract is about **Point B** — the partner's decision (notification accept/decline, then on-call coordination, then physical navigation to the home) — and the **translation** of the location signal from Wiom to the partner to the customer and back.

Three parties:

| Party | What they hold at the start of Point B |
|---|---|
| **Customer** | The truth — she knows her own address |
| **Wiom** | A captured GPS (step 4) + an unstructured text address string (step 8, post-payment) |
| **Partner (CSP)** | At notification time (step 10): a map image + straight-line distance + their own install history **+ the text address as a hurriedly-typed unstructured single-string blob**. Visible, but not parseable without a voice call. At call time (step 14): the text address + voice conversation with the customer to resolve it |

The signal degrades in translation at every handoff: customer head → text field → notification map → call conversation. Each handoff is a bottleneck.

---

## SECTION A — Problem Definition

### 1. Observed / Expected / Evidence

**Observed (from Satyam):**
> CSPs frequently misinterpret user address provided by system, leading to incorrect installation decisions or delays.

**Observed (quantified, from `master_story.md` Part C; cohort: Delhi Jan-Mar 2026 non-BDO, n = 2,561 pairs / 4,930 calls):**

- **Avg calls per pair = 1.92.** If address were clear at notification, most pairs would need one call or zero.
- **70% of pairs have >1 distinct reason across calls** — a single-snapshot view misses most of the address-resolution story.
- **Transcript-level address friction = 19-20% of calls** (vs dropdown rate ~13% — dropdown under-counts real friction ~2×).
- **Gali-stuck rate at call level: 7.4%.** Pair-level mode: 9.1%. The single biggest call-level bottleneck in the canonical landmark → gali → floor chain.
- Among 927 `address_not_clear` pairs: **41% never engage the gali step** — chain broke at or before landmark.
- Of 1,023 `address_not_clear` calls: **46% one-sided** (partner confused, customer clear), 32% mutual, 20% resolved-eventually. Refutes "mutual breakdown" framing — partner-side parsing dominates.
- `partner_reached_cant_find` at site arrival: 9.8% (active-base) / 11.1% (splitter). Breakdown peaks at the moment of arrival.

**Expected (from Satyam):**
> Address provided to CSP should be clear enough for correct install decision without clarification.

**Expected — quantified:**
- Avg calls per pair: <1.3 (from 1.92)
- Gali-stuck call-level rate: <2% (from 7.4%)
- `partner_reached_cant_find`: <5% (from ~10%)
- Installed share of pairs with zero clarification calls: >70% (baseline TBD — Sprint 1 deliverable)

**Evidence (Satyam's list + where measured):**

| Satyam's evidence item | Where measured | Current state |
|---|---|---|
| % installs delayed due to address confusion | `decision_to_install_hours` sliced by primary_reason across all installed pairs | **Null finding — install time does NOT discriminate by call reason.** `address_not_clear` median = 18.8h; `partner_reached_cant_find` median = 19.1h; non-address reasons median = 21.6h. All primary_reason buckets compress into an 18.8h–25.1h range (~6h spread). Cost of address friction is paid in **conversion** (pairs that never install at all) rather than in hours-to-install (`master_story.md` Part D.B). |
| % calls made for clarification | Coordination call aggregation by pair | **1.92 avg**, p90 = 4, max = 24 |
| % failed installs due to location misunderstanding | `primary_reason = address_not_clear` × `installed = false` | 927 ANC pairs · not-installed 48.4% vs non-ANC 47.8% — ANC doesn't cause install failure in isolation but consistently lives in failing cohorts |

### 2. Cross-engine cross-check

Three independent findings converge on "the address is captured unstructured, transmitted unstructured, and forced to resolve on a voice call":

1. **Coordination call analysis:** transcript-level address friction is flat across distance and probability deciles — meaning partner-side parsing breaks regardless of geometric or ranking match quality. The fix is not ranking-the-right-partner; it's giving *whoever the partner is* a cleaner address signal.
2. **Allocation analysis:** the dropdown's 48% → 2.5% prob-decile `address_not_clear` pattern was a decline-channel artifact (polite exit on low-prob bookings), not a real per-call content signal. Allocation cannot infer address quality from existing decline reasons.
3. **Promise Maker GPS analysis:** text address capture (step 8) happens *after* booking fee is paid, as a single free-text field. No structured sub-field for landmark / gali / floor / pincode. The string is *visible downstream* but unparseable.

### 2.1 The text-visibility correction

Earlier framing of this problem held that the partner did not see the text address at notification time — only the map. **This is incorrect.** The partner sees the text address. What he doesn't see is **structure**. The text is a single-string blob hurriedly typed by the customer; the partner can read it but cannot parse it into landmark / gali / floor without a voice call. The diagnostic shift: the partner is not working without information — he is working with information he cannot use.

This correction is load-bearing for the root cause and hypothesis. It replaces the earlier "visible vs hidden" framing with "structured vs unstructured" throughout.

---

## SECTION B — Project Definition

### 2. Objective

**Objective (measurable shift):**
- Avg calls per (mobile, partner) pair: **1.92 → <1.3** (primary)
- Gali-stuck call-level rate: **7.4% → <2%** (secondary)
- `partner_reached_cant_find` site-arrival rate: **~10% → <5%** (tertiary)

These three metrics together cover the three translation failure modes: too many clarifications needed, clarifications never reach gali, clarifications reach the door but still fail.

*Framed as:* the address the partner sees should carry the same structure the customer holds in her head — landmark, gali, floor as separate confirmed fields, not a single typed blob.

### 3. Classification + Rationale

**Capability Build.**

Rationale:

- **Not Hygiene** — hygiene fixes something broken. Address capture and notification payload work as designed; the design does not include structured address or pre-click structured visibility.
- **Not Efficiency** — efficiency improves an existing mechanism. There is no "faster" version of an unstructured free-text field. We add a structured representation that does not exist today.
- **Not Outcome Shift alone** — outcome (install velocity, partner productivity) will shift, but the mechanism is a new system capability: a shared canonical address representation across Wiom, partner, customer.
- **IS Capability Build** — Wiom currently has **no structured address model**. Customer types freeform text; Wiom stores it; partner reads it; partner mentally parses it on a voice call. There is no system stock of structured address. Building one is genuinely new capability.

### 4. Root Cause

Structural, not superficial.

**Root cause.** There is **no shared canonical representation of the home's location across the three parties**, and the translation loses structure at every handoff.

Translation chain:

```
Customer (head)  →  App free-text field (step 8)  →  Wiom DB string
                                                           ↓
                                             Allocation notification (step 10)
                                                 ↓ (text visible but unparseable)
                                                Partner
                                                 ↓
                                       Voice call on locality/gali/floor (step 14)
                                                 ↓
                                              Technician
                                                 ↓
                                             Physical install
```

**Contributing mechanisms (post-analysis):**

1. **Free-text field at step 8** — no structured capture of the landmark → gali → floor chain the partner actually navigates by. Customer's mental model (which has structure) is compressed into one string on submit.
2. **Notification payload carries text address as an unstructured blob.** Partner sees it but has no way to parse it into landmark / gali / floor without a voice call. The call is not happening because the address is hidden; it is happening because an unstructured blob cannot be parsed into the chain the partner navigates by. (See A.2.1 for the text-visibility correction this replaces.)
3. **No pre-call structured transfer.** Once the partner clicks in, he sees the same free-text blob. No way to confirm landmark / gali / floor *before* calling.
4. **Voice call is the only address-resolution channel.** 46% one-sided (customer clear, partner confused) proves the customer already has the structure; we just haven't captured it.
5. **Floor detail surfaces only on the call.** Height / wiring complexity (technician prep) invisible to Allocation and partner at notification time.

### 4.1 The landmark → gali → floor chain is behaviourally established, not invented

The fix to this root cause is not a new taxonomy imposed on partners. Coordination call-transcript analysis shows this chain is the sequence partners **already use** on voice calls to resolve addresses. The behavioural sequence is: discussion on landmark → asking gali → floor number (if install is at height).

Chain-engagement has a measured protective effect: +11pp install rate inside polygon when the chain is touched on any call (`master_story.md` Part C.E). Floor-stuck pairs (partner at door) install at 73.9%. The bottleneck is *getting on the chain at all*.

Upstream capture in the same chain the partner already uses on calls **removes the call**. The structure is not new — the capture is.

### 5. Leverage Level

**LP4 — rule change + new information flow** (Meadows hierarchy).

Same level as companion contract, complementary mechanism:
- Not LP2 — tweaking notification text or adding a second free-text field doesn't change the structural representation.
- Not LP5 — Wiom's purpose stays the same.
- **IS LP4** — what information flows between the three parties changes (structured address replacing free text, confirmed landmark/gali/floor in the notification rather than a blob, floor detail pre-call rather than mid-call), and the rules of partner-customer coordination change (call becomes a confirmation step, not a discovery step).

---

## SECTION C — Measurement

### 6. Measurement Stack

| Layer | Meaning | Metric for this project |
|---|---|---|
| **L5** — final outcome | Company-level value | Install throughput per partner-week |
| **L4** — driver | System-level driver | Partner productivity (installs per unit partner time) |
| **L3** — **SIGNAL** | Fast measurable proxy | **% of (mobile, partner) pairs that install with ≤1 clarification call** |
| **L2** — execution proof | Coverage of intervention | % of bookings with structured address fully populated (all required sub-fields non-null) |
| **L1** — system correctness | Wiring works | Structured capture widget serving; notification payload carrying structured address; partner UI rendering correctly |

### 7. Tracking Table

| Metric | Baseline | Target | Frequency | Source |
|---|---:|---:|---|---|
| Avg calls per (mobile, partner) pair | **1.92** | <1.3 | Weekly | Call aggregation by pair (recomputed on post-intervention cohort) |
| Gali-stuck call-level rate | **7.4%** | <2% | Weekly | Address-chain tagger re-run |
| `partner_reached_cant_find` rate | ~10% | <5% | Weekly | same |
| One-sided confusion rate within ANC | **46%** | <25% | Weekly | Communication-failure classifier re-run |
| Structured address coverage | 0% | >90% | Daily | New event in booking event log for structured address submission |
| Pairs installing with ≤1 call | TBD (Sprint 1) | >70% | Weekly | Call aggregation by pair — add `n_calls ≤ 1 AND installed = 1` cut |

---

## SECTION D — Leading Signal (Critical)

### 8. Leading Signal

**% of (mobile, partner) pairs whose first partner-customer call either does not happen (address was clear pre-call) OR ends with the address chain fully resolved (landmark + gali + floor confirmed).**

In the existing Coordination call-analysis pipeline:
```
(no call recorded in UCCL with this partner as attributed owner)
    OR
(first call's addr_chain_stuck_at = 'none' AND primary_reason != 'address_not_clear')
```

Why this metric, not total calls per pair: total calls lags the install. First-call-resolved fires within hours of dispatch, giving fast read on whether the intervention is working.

### 9. Signal Validity

**Observability.**
*One-line proof:* UCCL + Exotel + Whisper + Haiku pipeline already built inside Coordination call-analysis; per-pair signal available within ~24 hours of first call.

No new infrastructure needed to measure. Structured-address-coverage (L2) observable in real time from booking event stream.

**Causality.**
*One-line proof:* structured address captured upstream → partner sees **structured** landmark/gali/floor in notification (displacing the unstructured blob) → partner confirms pre-call or decides without calling → fewer clarification loops → fewer gali-stuck calls.

Causal chain passes through the same bottleneck (gali resolution) that the Coordination analysis empirically identified as the biggest single call-level friction point (7.4%, `master_story.md` Part C).

**Sensitivity.**
*One-line proof:* intervention directly changes what the partner sees *before* calling; dose-response via pilot — landmark-only → landmark+gali → full landmark+gali+floor — metric should improve monotonically.

### 10. Signal Timing

- First-call-resolved rate: **~24-48h** per booking (call + transcribe + classify).
- L3 pairs-installing-with-≤1-call: **2-4 weeks** (install lookahead).
- L5 throughput: **4-8 weeks** (partner-week baselines post-intervention).

### 11. Scope Constraint

**Yes.** First-call-resolved fires within days. The pipeline processes ~4,930 calls in ~90 minutes on current config — daily-capable.

---

## SECTION E — Ownership & Mapping

### 12. Owner

**Maanas** (one person, not a team).

### 13. Driver Mapping

**Install velocity + partner productivity.**

Downstream beneficiaries:
- Allocation engine — decline decisions become content-aware (partner decides after *seeing structured address*, not using the dropdown as exit).
- Promise Maker engine — structured address collected pre-promise becomes a cross-validator for the companion contract.

*Belief-model note.* The existing allocation belief model (Belief Model 2) gets richer inputs — landmark match against partner's install history — once this capability ships. Supporting, not primary.

### 14. NUT Chain

**Structured address + landmark-framed partner notification → First-call-resolved rate → Installs per partner-week → Net installed paying customer revenue.**

Structure preserved end-to-end → partner decides on content, not blob → fewer calls per install → more installs per partner-week → partner retention rises → NUT grows.

### 15. Validation Path

**If the L3 signal moves as predicted:**

1. Structured-address coverage (L2) reaches >90%
2. First-call-resolved rate rises (leading signal)
3. Avg calls per pair drops (L3)
4. Gali-stuck and `partner_reached_cant_find` drop (tertiary metrics)
5. Install throughput rises (L4/L5)

**Disconfirmation paths:**
- L2 > 90% but leading signal doesn't move → partners ignoring the structured address (UI not surfacing it, or trust issue). Fix: UI / training, not capture.
- Leading signal moves but gali-stuck doesn't → structured capture isn't capturing *gali* specifically. Fix: taxonomy revision.
- All moves but L5 doesn't → time saved isn't converting to more installs. Partner task-routing is the next bottleneck — hand off to Partner Management.

---

## SECTION F — Execution

### 16. Time Class

**Capability Build → 2-3 sprints.**

- Sprint 1: define structured address schema (landmark / gali / floor / pincode + free-text overflow) using Coordination call-transcript taxonomy as ground truth; build customer-side capture UI.
- Sprint 2: update notification payload to carry structured address; build partner-side UI rendering structured fields with per-field confidence; instrument landmark-grounded-serviceability inference on partner install history.
- Sprint 3: roll out, monitor, iterate.

### 17. Execution Plan

| Step | Agent does | Human does |
|---|---|---|
| 1 | Pull landmark / gali / floor taxonomy from Coordination call transcripts — actual landmarks (chowk, mandir, market, metro, school), gali naming conventions, floor references (manzil, chhat, kothi, ground). Frequency table. Feeds both customer-side picker AND partner-side notification framing. | Maanas + Wiom product: decide schema (required vs optional sub-fields) |
| 2 | Draft structured capture UI copy and field definitions | Wiom product + design: partner-review UI |
| 3 | Instrument structured capture event in the booking event log (new event or extended payload) | Wiom engineering |
| 4 | Instrument notification payload to carry structured address with per-field confidence tier + map with landmark pin (not just straight-line distance) | Wiom engineering |
| 5 | Instrument landmark-grounded-serviceability inference on partner install history — which landmarks sit within each partner's actual install base | Wiom engineering |
| 6 | Build partner-side "confirm address before calling" flow with per-field confidence visible | Wiom product + partner-app engineering |
| 7 | Re-run Coordination call-analysis pipeline weekly on post-intervention cohort; emit weekly L2/L3/L4 tracking table | Maanas reviews, iterates on schema |

*(Specific anchor set, feedback-loop mechanics, external-tool choices — design choices for the system spec, not this contract.)*

### Decision point mid-build — where to capture structured address

V1 offered Option A (capture at current step 8, post-payment) vs Option B (capture between step 4 and step 6, pre-promise).

**Post-analysis the decision is made: Option B is default.** The companion contract's locked objective ("inputs verified before making a promise") requires pre-promise structured capture. The structured-address capture *is* the shared upstream element both problems rest on; post-payment capture does not serve the verification need.

Option A is a **degraded fallback only** if user-flow completion rates collapse below an acceptable threshold during Option B pilot. Not a first-choice alternative.

---

## SECTION G — Learning Logic

### 18. Hypothesis

**If we replace the free-text address field with a structured capture (landmark + gali + floor + pincode), AND propagate that structured address to the partner's notification as separate fields framed in the partner's own install history, then:**
- **avg calls per (mobile, partner) pair drops from 1.92 to <1.3**
- **gali-stuck call rate drops from 7.4% to <2%**
- **`partner_reached_cant_find` site-arrival drops from ~10% to <5%**
- **within 6 weeks of full rollout**

Mechanism: partner sees the chain he navigates by (landmark → gali → floor) rather than having to rebuild it on a voice call. Structure captured once, preserved through every handoff, rendered in the partner's own install-history context.

### 19. Risk Check

| Risk | Mitigation |
|---|---|
| Customer drop-off if structured capture flow is too long | A/B test schema variants (3-field minimal vs 5-field full); measure completion before payment step |
| Taxonomy too rigid — not every address fits landmark → gali → floor (gated societies, standalone kothis) | Free-text overflow preserved; structured fields optional but nudge-required. Transcript data shows landmark→gali→floor is dominant Delhi pattern, not exclusive. |
| Partner adoption — partners still call even with structured address, out of habit or skepticism | Sprint 3 partner training. Partner UI shows "confirmed structurally" + timestamp. **Post-install landmark validation (4 signals: transcript mining, second-call escalation, partner field GPS, time-to-door distribution) validates landmarks against actual usage — partners learn to trust structure when the stock proves itself.** |
| Address still doesn't match physical reality (wrong landmark entered) | Cross-check against map landmarks via reverse-geocode; flag mismatches pre-promise. Overlap with companion contract's verification channel — both projects share infrastructure. |
| Gali is the hard one — no canonical gali registry in Delhi | Seed with a partner-sourced registry (partners working an area suggest canonical names); post-install validation sharpens over time. |
| Companion contract solves GPS but structured address doesn't land → clean coord next to ambiguous address | Schema must include `address_confirmed_via_ssid_match` field set when install fires, closing the loop and building the neighbourhood-memory stock |
| L3 moves but L5 (throughput) does not | Bottleneck shifted further downstream — partner task-routing or technician scheduling. Hand off to Partner Management. |

### 20. Learning Path

| Outcome | Decision |
|---|---|
| L2 coverage >90% + L3 rises + L5 throughput rises | **Scale** — roll out to all cities |
| L2 coverage >90% + L3 rises + L5 flat | **Partial win** — coordination friction down; install throughput bottleneck further downstream. Investigate partner task-routing / technician scheduling |
| L2 coverage >90% + L3 flat | **Partners aren't using the structured address.** Investigate partner UI, partner trust, schema quality. Remedy: show partner *why* the address is confirmed (pincode verified, landmark confirmed by customer twice) |
| L2 coverage <90% | **Customer-side capture failing.** Simplify schema, reduce required fields, re-test |
| L3 moves but gali-stuck doesn't | **Taxonomy wrong at gali level.** Re-pull transcript taxonomy; partner-sourced canonical registry |

---

## FINAL RULE (per template)

- ✅ Clear problem: 1.92 calls per pair, 7.4% gali-stuck, 46% one-sided confusion — all from transcript ground truth, not dropdown proxies.
- ✅ Measurable signal: first-call-resolved rate (real-time), avg calls per pair (weekly).
- ✅ Testable hypothesis: structured address + landmark-framed notification → call volume and gali-stuck drop in 6 weeks.

**This is a project.**

---

## Open pre-requisites before build starts

| Pre-requisite | Sits in | Blocks |
|---|---|---|
| Landmark / gali / floor taxonomy frequency table from Coordination call transcripts | Address-chain tagger already tags; needs aggregation by value | Structured capture schema design |
| Partner-side UI research — do partners want structured address, or prefer free-text + voice call? | Wiom product research | Partner-side UI design (Sprint 2) |
| Re-compute install-rate by n_calls bucket | Call aggregation by pair | L3 baseline for "pairs installing with ≤1 call" |
| Post-install landmark validation stack (D8 in companion frame) — wiring | New — Sprint 3 | Partner-adoption risk mitigation |

---

## Cross-link: relation to companion contract

This contract solves **signal consistency across parties between Point A and Point B**. The companion contract (`problem_1_location_estimation_v2.md`) solves **input verification at Point A**.

The two problems are **parallel workstreams** resting on a **shared upstream element** — structured landmark / gali / floor capture at flow steps 4-6. Captured once, consumed by both:
- Companion contract uses the ≥2 landmark confirmations as the independent second channel that verifies home-presence.
- This contract uses the same confirmed landmark / gali / floor as the structured fields in the partner's notification.

Solving only this contract: cleaner address, but GPS still drifts — partner arrives at the wrong block despite perfect address.
Solving both: the three parties hold the same location model at the same quality at every handoff.
