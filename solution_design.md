# Solution Design — Location Signal Audit

**Author:** `story_teller_part1`
**Drafted:** 2026-04-20 · **Status:** living document · agent validation pending (Geoff + Donna running)
**Companion docs:**
- `README.md` (parent synthesis — customer flow + three-engine findings + contract index)
- `problem_statements/problem_1_location_estimation.md`, `problem_statements/problem_2_address_translation.md` (Gate 0 thinking contracts — pure thinking, no solution)
- `solution_synthesis.md` (my critique + innovation layer + Promise Maker substrate review — strategic)
- `possible_solutioning_approaches/` (Maanas's own notes + full Gate 0 HTML pitch)

**This document is the build spec.** It's kept separate from the Gate 0 contracts because Satyam's template is about *thinking*, not *designing*.

---

## 1. Framing — the reset

Maanas's directive: *"Reset and evaluate basis the features I currently have, and the way I am thinking of collecting signals, and more novel approaches. I may not implement the full Promise Maker Belief Model (PMBM) in one go."*

This is right. The full Promise Maker architecture (see `solution_synthesis.md` §1) is sophisticated — six stocks, cause-coded self-learning, Bayesian shrinkage, B_operational fusion. It's the right long-term destination. But if the location problems wait for PMBM to land fully, they don't ship.

### The reframe from Geoff (first-principles RCA)

Before diving into design, hold this: **the pain is not bad GPS**. Stage A proved the GPS apparatus is fine (p50 = 7.7m, p75 = 20m). The pain is that **Genie makes a promise — collects Rs. 100 — on an input it has never interrogated**.

Deeper still, per Geoff's validation: *the promise is structurally premature*. Wiom commits (fee + allocation) before it has evidence it can keep the commitment. **This violates one of Genie's own founding principles: "promise-making and promise-fulfillment are structurally separated."** Today they aren't, in spirit — the promise is being made on pre-evidence.

Symmetric reframe for Problem 2: there's a **structural asymmetry** — the customer has gali knowledge Wiom's app never captured. Every downstream intervention (landmark prompts, photo, video, packet, voice calls) is compensating for the fact that the original capture form asked for "free text address" post-payment with no validation. The 41% of pairs that never engage the gali step at all is partners *giving up* on structured resolution.

These reframes shift the design target. The observed metrics (25.7% structural drift, 1.92 calls, 7.4% gali-stuck) are *proxies* for the real pain. The real objective is upstream:

- **P1 true objective:** make the promise only when Wiom has interrogated the evidence it's committing on.
- **P2 true objective:** capture (and surface) the address structure the customer already holds, so the partner never has to rebuild it by call.

Design principle: **every phase must deliver standalone value and simultaneously seed the next phase's infrastructure.** No throwaway scaffolding.

The design below:
1. **Starts with what's already in the codebase today** — `partner_cluster_boundaries.h5`, `data_lib/geometry/hex.py`, `data_lib/external/enrich_wards.py`, install history in Snowflake, haversine. No new ML, no new training pipelines.
2. **Ships signal in sprint 1** without requiring PMBM to be live.
3. **Progressively adds capability** — novel signal collection lands in later sprints without breaking V0.
4. **Keeps the long-term PMBM destination open** — every V0-V2 artifact is compatible with eventual PMBM integration. Nothing blocks; nothing preempts.

---

## 2. The day-in-the-life story (Priya, adapted from HTML Gate 0 report)

Best practice from the HTML: ground the design in one concrete human narrative. Same narrative repeats across thousands of leads; fix it once, fix it many times.

**9:12 AM** — Priya opens the Wiom app on her ₹6,000 Android. Submits home GPS. Her building is tall, she's indoors, GPS returns a fix **540m east, on top of a petrol pump**. She doesn't notice. The 25m gate checks infrastructure near the petrol pump — happens to find a splitter 22m away (serving a different block). Gate passes. She pays Rs. 100. Promise made.

**9:13 AM** — Wiom types the promise to Snowflake. Booking lat/lng: petrol pump coords. Lead scoring reads the coord, looks up hex features for the petrol-pump hex (not Priya's building's hex). Score is based on a place Priya doesn't live in.

**9:15 AM** — Priya types her address: "Flat 3B, Green Apts, near SBI, Lajpat Nagar-III". Free-text. No structure.

**2:30 PM** — Ramesh (CSP partner) opens his app. Sees the task. Sees a map with a straight-line distance (from his historical install base to the petrol-pump coord). No text address shown. Accepts.

**2:35 PM** — Ramesh clicks through. Sees the text address. Delhi has three SBI branches in Lajpat Nagar. Two buildings are named "Green Apartments." Ramesh calls Priya.

**3:10 PM** — After 20 minutes of discussion — landmark confusion ("which SBI?"), gali identification, floor clarification — Ramesh drives to his best guess.

**4:45 PM** — Wrong SBI, wrong Green Apts. Ramesh is 600m from Priya. Late for the next install. Reschedules Priya for tomorrow.

**What broke and where:**

| Time | Break | Which engine owns the fix |
|---|---|---|
| 9:12 | Bad GPS — no validation, no re-capture | Promise Maker (Problem 1) |
| 9:13 | Scoring on wrong hex | Promise Maker (Problem 1) downstream |
| 9:15 | Unstructured address — no landmark parse, no sub-fields | Problem 2 |
| 2:30 | Notification hides the address from Ramesh — decision on geometry alone | Allocation + Problem 2 |
| 2:35-3:10 | Address resolution happens on a phone call, not in a structured transfer | Coordination + Problem 2 |
| 4:45 | Wrong place, real cost | Everyone downstream |

Every break above corresponds to a design decision currently in place. Each is addressable.

---

## 3. Current feature inventory — what we actually have

This is the reset. Everything below is live in the Wiom stack or the `genie_stocks` repo today. No promises, no roadmap items.

### 3.1 Features available at Point A (Wiom's promise decision)

| Feature | Source | How fresh | Reliability |
|---|---|---|---|
| Booking lat/lng | Wiom app — one-shot GPS at step 4 of flow (`lead_state_changed` · `lead_state='serviceable'`) | At capture time | **25.7% structurally wrong** (Stage B) |
| `booking_accuracy` | Device self-report at capture time | At capture time | Unknown calibration (open Stage B slice) |
| Customer-stated pincode | Typed by customer | At capture time | 30-40% wrong nationally per HTML evidence |
| `time_bucket` | IST hour of `fee_captured_at` | Derived | Deterministic |
| Ilaaka GPS | Wiom app — step 2 of flow (city filter) | Pre-home-GPS | Not currently surfaced downstream — latent asset |
| `partner_cluster_boundaries.h5` | From install history — `B/compute/compute.py` | Daily refresh | 47 partners × 219 clusters (sample) |
| Install history (per pincode) | Snowflake — all past `wifi_connected_location_captured` events | Real-time | Ground-truth addresses for completed installs |
| Ward polygons | `data_lib/external/enrich_wards.py` — spatial join infrastructure | Already running | Delhi coverage good, Noida partial |
| Pincode centroid table | Reverse-geocode asset | Quarterly refresh | Good except near re-drawn boundaries |
| Haversine distance | `data_lib/geometry/distance.py` | — | Trivial |

### 3.2 Features available at Point B (partner notification)

| Feature | Source | Shown to partner when? |
|---|---|---|
| Booking lat/lng | As above | Pre-click (on the map) |
| Partner's historical install points | Snowflake | Pre-click (on the map) |
| Straight-line distance to partner's base | Computed | Pre-click (displayed) |
| Text address (free-form) | Customer typed post-payment | **POST-click only** |
| GNN `probability` score | Allocation model | Internal — not rendered to partner |
| Partner's own service polygon (if rendered) | `partner_cluster_boundaries.h5` | Partner-app dependent |

### 3.3 Features available downstream (after acceptance)

| Feature | Source | Used by |
|---|---|---|
| Call transcripts | UCCL + Exotel recordings | `../coordination/` pipeline |
| Address-chain tags (landmark / gali / floor) | Haiku-4.5 classifier output | Coordination analysis |
| Decision event | Partner action (INTERESTED / DECLINED) | Allocation + learning loop |
| Decline dropdown | Partner click | Allocation (diluted signal per `../coordination/`) |
| `wifi_connected_location_captured` | Post-install event | Ground-truth for drift + jitter baseline |

### 3.4 Signals currently collected — one-line summary

- **Point A:** 1 GPS fix + 1 self-reported accuracy + 1 free-text address (captured in that order, with payment in between GPS and text).
- **Point B:** Partner sees geometry-only at notification; address only post-click.
- **Post-install:** Ground truth install GPS, partner call transcripts (optional mine).

That is the full substrate. Everything else must be *added*.

---

## 4. Novel signals we can start collecting

These are additive. None require PMBM. Most require a UX change, not a model.

### 4.1 Novel signals at Point A

| Signal | How | Cost |
|---|---|---|
| **Continuous GPS stream during capture** (5-10 seconds) | Wiom app — stream fixes, compute stability + confidence envelope | App-side change, small |
| **Repeat pings from same mobile over time** | Already emitted on reinstall — mineable as per-mobile jitter profile | Zero — data already exists |
| **Explicit "I am at my home" affirmation** | Simple Y/N button after GPS capture | App-side, trivial |
| **Reverse-geocoded pincode** | Pincode centroid lookup on captured lat/lng | Existing infra |
| **Text address BEFORE payment (not after)** | Flow re-order — capture structured address between GPS and fee | App + backend, UX sensitive |
| **Structured address sub-fields** (landmark / gali / floor) | Customer enters as 3 fields instead of one blob | App + schema change |
| **Photo of building entrance / street / landmark** | Customer uploads; stored as blob | App + S3, small |
| **Short reel-style video from nearest landmark to home** | Customer records 15-30 sec video; stored | App + S3, medium |

### 4.2 Novel signals at Point B

| Signal | How | Cost |
|---|---|---|
| **Structured address packet in notification** | D&A OS `genie_context_manager` enriches dispatch | Backend + partner-app rendering |
| **Past-install anchor** ("same building as install I8831213, 18m NE") | KNN over install history per pincode | Existing infra |
| **what3words code** | API call at capture or notification build | API cost (~$0.0003/lookup) |
| **Temporal navigation anchor** ("partner Ram went to 'SBI near water tank' last Tuesday") | Mine recent transcripts + install outcomes | `../coordination/` pipeline extension |
| **Partner-visible decline consequence** (hex-reddening with decay) | Partner-app map rendering change | Partner-app + mapping |

### 4.3 Novel signals from the learning loop

| Signal | How | Cost |
|---|---|---|
| **Explicit cause codes** (GPS_TRUST_FAILURE, ADDRESS_RESOLUTION_FAILURE) | Cause-coding extension in ALLOC_CONTEXT processing | H-table schema + version |
| **Per-mobile jitter profile** | Aggregate from repeat `wifi_connected_location_captured` events | Batch job |
| **Gaming-detection flag** | Features from repeat captures, accuracy plausibility, IP consistency | New classifier + features |

---

## 5. Design principles (bright lines)

These hold across all phases. Compromising them compromises the architecture.

1. **Scoring artifacts stay internal to Genie** (SAT-01 ratification). Trust scores, gaming flags, and classifier outputs do NOT ride in Promise Packet. They are consumed internally by B/R/E/S and by `genie_context_manager` for D&A OS enrichment.
2. **The capture layer must receive feedback.** Every phase includes some path for Genie → customer app signal. Without this, Layer 4 (learning) is missing.
3. **Every partner-visible signal with a feedback gradient decays with time and evidence.** Hex-reddening from a 6-month-old single decline is worth less than five declines this week. No permanent markers.
4. **Customer re-capture is structurally different from initial capture** — not a "confirm your inputs" form, but a live re-acquisition with environmental checks. Avoid adversarial doubling-down.
5. **Cause-code fidelity is non-negotiable.** Every new failure mode a phase introduces gets a new cause code in H. Otherwise B learns nothing from the new signal.
6. **Shiprocket NER is the canonical structured-address parser.** Apache 2.0, 11 entity types, free, runs on CPU in <200ms. Do not build a bespoke parser; do not buy a commercial alternative.
7. **what3words is an addition, not a replacement.** Raw text stays. NER parses stay. w3w is one more anchor, not a substitute.
8. **Nothing in V0-V2 blocks the eventual PMBM integration.** Every cause code, feature flag, and signal is named so it can feed B later.

---

## 6. V0 — MVP shipping this sprint (pure current features)

**Goal:** Ship signal. No customer-app changes. No new ML models. Zero PMBM dependency. One sprint.

### 6.1 Problem 1 V0 — Rules-based trust bands

**What:** Tag every booking with a `location_trust_band ∈ {HIGH, MED, LOW}` at capture time, using only features that already exist in Snowflake.

**Rules:**
```
Check A — partner cluster containment:
  For each partner in the booking's allocation pool:
    point-in-polygon(booking_lat_lng, partner_cluster_boundaries[partner])
  a_score = fraction of partners for which the point is inside their cluster

Check B — pincode reverse-geocode match:
  geo_pincode = reverse_geocode(booking_lat_lng)   # pincode centroid table
  b_score = 1 if geo_pincode == stated_pincode else 0

Check C — nearest past install in stated pincode:
  d = haversine(booking_lat_lng, nearest_past_install(pincode=stated_pincode))
  c_score = 1 if d <= 500m else max(0, 1 - (d - 500) / 2000)

trust_score = 0.4·a_score + 0.3·b_score + 0.3·c_score

location_trust_band = HIGH if trust_score > 0.75 else
                      MED  if trust_score > 0.40 else
                      LOW
```

**What it does with the band:**

| Band | V0 action |
|---|---|
| HIGH | Nothing — proceed as today. |
| MED | Log the flag. Add a feature column for downstream learning. No routing change in V0. |
| LOW | Log the flag + add an asynchronous CRE callback queue (not blocking promise). |

**Where the code lands:** new file `B/compute/trust_gateway_v0.py`. Called inline with the 25m gate. Writes `location_trust_band` into `booking_logs`.

**Thresholds (0.75 / 0.40):** calibrated in Sprint 0 using the already-pulled Stage B cohort (`promise_maker_gps/booking_install_distance/investigations/install_drift_raw.csv`). Target: 80% of installs with drift < p95 Stage A should be HIGH; 70% of installs with drift > Stage A p95 should be MED or LOW. Tune weights (0.4/0.3/0.3) to hit both.

**What V0 does NOT do:** change the 25m gate, block promises, or notify the customer. Pure measurement + tagging. Classifier (in later phase) will replace the hand-weighted rule.

**Why this is the right V0:** we already showed in the synthesis that the biggest structural leverage is the pre-commit re-capture loop (Innovation 1). But that requires a customer-app change. V0 ships *the measurement* that proves the problem, in a form the customer-app team can consume when they get to the UX change. Don't wait for the app team — tag, measure, publish.

### 6.2 Problem 2 V0 — NER-augmented notification payload

**What:** Partners see a structured parse of the existing free-text address at notification time (pre-click), plus a nearest-past-install anchor when available.

**Rules:**
```
At allocation time, for each booking, build address_packet_v0:
  ner = Shiprocket.parse(text_address)
  past_install = nearest_install(booking_lat_lng, pincode=stated_pincode, within=200m)

  packet = {
    "components": {unit, building, landmark, locality, pincode},
    "past_install_anchor": {install_id, distance_m, bearing, snippet} or null,
    "ward": enrich_wards(booking_lat_lng),
    "raw_text": text_address,
  }

  D&A OS notification consumes packet; partner app renders:
    - past_install_anchor (★ "STRONGEST CLUE") if present
    - components (fielded, not paragraph)
    - ward name (disambiguates duplicated localities)
    - raw_text (bottom, for voice-calling reference)
```

**What V0 does NOT do:** capture any new customer-side signal, introduce w3w, or add photos. Uses only text already captured.

**What ships in 1 sprint:** Shiprocket model downloaded (Apache 2.0, free), `genie_context_manager` packet builder, partner-app rendering change.

**Partner UI (sketch from HTML):** "★ Same building as install I8831213 — Green Apts, 2F, 18m NE" rendered as the strongest clue. Rest below.

**What V0 does NOT do:** structure the customer-side capture, change payment ordering, add photos or video. Those land in V2.

### 6.3 V0 cross-cutting: new cause codes

Add two cause codes to H from day 1, even if V0 doesn't yet drive them widely:

- `GPS_TRUST_FAILURE` — later triggered when trust layer blocks/retries (V1+)
- `ADDRESS_RESOLUTION_FAILURE` — triggered when partner reports unresolvable gali/floor

Schema-version H to support new columns. Retro-backfill existing records as `UNKNOWN_CAUSE` or `LEGACY`. This is the investment that makes V1+ possible.

### 6.4 V0 measurement plan

| Metric | Baseline | V0 target (1 sprint after ship) |
|---|---|---|
| `location_trust_band` distribution | — | Publish. Expect ~60-75% HIGH, ~15-25% MED, ~10-15% LOW on current-flow cohort. |
| Install rate by trust band | — | HIGH > MED > LOW, gap ≥ 10pp between HIGH and LOW |
| Calls per pair on packet cohort vs raw cohort (50/50 A/B) | 1.92 | <1.7 directionally |
| Gali-stuck rate on packet cohort | 7.4% | <5% directionally |

V0 is a measurement shipment, not an outcome shipment. The outcomes come in V1+.

---

## 7. V1 — Wiom-specific leverage (2-3 weeks post-V0)

**Goal:** Add novel signals Wiom uniquely has access to. Ship the single highest-leverage intervention.

### 7.1 Per-mobile jitter profile (novel)

From `gps_jitter/investigations/jitter_mobile_v4.csv` we already have 8,317 mobiles with measured jitter distributions. Productionize this:

- Batch job aggregates `wifi_connected_location_captured` events per mobile
- Emits `mobile_jitter_p50`, `mobile_jitter_p75`, `mobile_jitter_p95`, `n_pings`
- Trust layer consumes: replaces the global Stage A p95 floor (154.8m) with per-mobile p95 when n_pings ≥ 3
- Falls back to global p95 when mobile has no profile (cold start)

**Effect:** A known-clean mobile with p95 = 25m gets a tighter drift tolerance. A known-noisy mobile with p95 = 400m is held to a looser threshold (fewer false LOWs). Device class is now implicitly modeled.

### 7.2 Pre-commit re-capture loop (the signature intervention, novel)

This is Innovation 1 from my synthesis. The single highest-leverage move.

**Mechanism:**
```
Customer submits home GPS (flow step 4)
    ↓
Trust layer evaluates (V0 rules, V1 with per-mobile profile)
    ↓
If trust_band == LOW:
    → Wiom app receives Genie signal: RE_CAPTURE_REQUESTED
    → App UX: "Let's try that again. Please make sure you're at your home. Hold still for 10 seconds."
    → Force live re-acquisition with:
      - Minimum 10 seconds of stationary GPS stream
      - Minimum accuracy threshold (self-report < 30m)
      - Plausibility check: new fix within 500m of first fix (gaming detection)
    → Re-evaluate trust
    → After N=3 retries still LOW: escalate to structured-address capture BEFORE fee capture
If trust_band == MED:
    → Soft nudge: "We're fairly confident of your location. Want to tap your exact home on a map?"
    → Optional, not blocking
If trust_band == HIGH:
    → Proceed as today (25m gate, fee capture, promise)
```

**Why this is the signature move:**

- It closes Layer 4 (learning loop) of the 4-layer architecture
- It intercepts bad captures before any downstream heroics are needed
- Every subsequent intervention (packet, hex-reddening, PMBM) operates on a higher-quality input
- It shifts cost from the field (wasted CSP trips) to the app (10 seconds of waiting) — enormous unit economics shift

**Architectural addition:** a new outbound Genie signal (RE_CAPTURE_REQUESTED) to the Wiom customer app. This is outside today's Genie I/O (which only talks to D&A OS + CL OS). Needs Satyam sign-off — flagged in `solution_synthesis.md` §8 as Open Question #1.

**What can ship without Satyam sign-off:** the V1 trust-layer refinement (rules → classifier). The re-capture loop itself requires architectural expansion.

### 7.3 V1 classifier upgrade (optional, parallel)

Replace the hand-weighted rule from V0 with a gradient-boosted classifier trained on:
- Features: trust_score components (a_score, b_score, c_score), `booking_accuracy`, `time_bucket`, mobile_jitter_p95, text-cosine similarity to nearest install's address
- Label: self-supervised — CSP "reached on first try" flag from CRM (Swiggy-style labelling)

Target: AUC ≥ 0.80 on a held-out Delhi cohort. Swiggy reports 0.89 — our upper bound.

---

## 8. V2 — Partner-side closure (2-3 weeks post-V1)

**Goal:** Close the partner-side loops. Add the novel anchors and the UX for decline-side feedback.

### 8.1 Temporal navigation anchor (novel)

New 8th anchor in the address packet:
- For each past install within 200m of a new booking, with install date within 90 days
- Mine the coordination transcript (if exists) for landmark phrases via `flag_address_chain.py` outputs
- Rank by (recency × install_success × chain_engagement_level) — optimistic aggregate
- Surface the top landmark phrase + partner who used it: *"Partner Ram went to 'SBI near the water tank' on 2026-04-03 — installed same day"*

This is the Dunzo-style behavioral recognition signal. Static NER gets you "near SBI"; this anchor gets you "near **the SBI that actually worked** for a partner like you."

### 8.2 what3words + photo/video (when app ready)

Additional packet anchors:
- **w3w code** (API call at capture; cached). Two languages: EN + HI.
- **Optional customer photo** — "building entrance or landmark" uploaded at capture
- **Optional reel-style video** — 15-30 sec walk from nearest landmark to home, captured when trust is LOW or MED

Photo/video only required on MED/LOW trust bands. HIGH trust leads skip this to avoid friction.

### 8.3 Partner-side hex-reddening with decay

Maanas's proposal, with my decay fix to avoid prior poisoning:

**Mechanism:**
- Partner declines → a decay-weighted negative mass is added to that partner's B_spatial field at the booking hex
- The negative mass is added with `decline_weight = -1.0 × time_decay × evidence_factor`
  - `time_decay = exp(-days_since_decline / 90)` (90-day half-life equivalent)
  - `evidence_factor = min(1.0, n_decisions_in_hex / 10)` (low-evidence hexes don't redden hard on one decline)
- Partner app visualizes the field:
  - Green hex: high positive KDE value (likely install)
  - Orange: neutral
  - Red: negative (likely decline)
  - Intensity decays visibly over weeks
- Partner sees their own service zone evolving → calibrates where they will + won't get leads

**Why this works without the prior-poisoning bug:** single declines decay within weeks; repeated declines in established hexes redden harder and persist longer. New partners entering a reddened hex see orange (not red) because the decline evidence is weighted against hex total decisions, not partner-specific history.

### 8.4 Decline → customer signal (with Critique 4 guard)

On partner decline:
- Customer app receives notification
- UX: **structured re-capture**, NOT "confirm your inputs." Present the customer with a live map showing Wiom's current best-guess coord + a pincode-based ward boundary. Ask: *"Is your home inside this area? If not, let's try the GPS again."*
- Avoids adversarial doubling-down because the UI shows a different representation (map + boundary) rather than echoing what the customer typed
- Also: CRE callback queue if re-capture also LOW

### 8.5 Gaming-detection sub-signal (novel)

Features:
- Repeat-GPS variance from the same mobile (low variance + high drift = gaming suspect)
- Accuracy self-report plausibility (consistent 5m self-reports from a known-noisy mobile profile = suspect)
- Time-since-app-install (very new install + bad GPS = noise; very new install + repeated bad GPS with same coord = suspect)
- Mobile-phone-number reputation (flagged in prior abuse data)

Emits `gaming_score` separately from `trust_score`. Treated differently:
- High trust + high gaming → block, human review
- Low trust + low gaming → re-capture (noise case)
- Low trust + high gaming → block

---

## 9. V3 — PMBM integration (when Phase 5 of NEXT_STEPS_BELIEF_MODEL_EVOLUTION.md lands)

By V3, the following artifacts we'll have built are all PMBM inputs:

- `location_trust_band` + `trust_score` → feeds shrinkage `α(i)` (low trust → more pull toward prior)
- `mobile_jitter_p95` → feature for spatial uncertainty
- `gaming_score` → behavioral feature (eventually B_behavioral)
- Address packet NER fields → features for R's threshold application
- New cause codes in H → cleaner training signal for B_spatial retrain

**Integration work at V3:** wire the trust gateway output into `B/compute/compute.py`'s Bayesian shrinkage prior computation. Adjust B_spatial's KDE weights to differentiate cause-coded declines. No V0-V2 artifact is thrown away; all are consumed.

---

## 10. Meadows leverage ranking (Donna-validated)

Per Donna's systems review. The prize is the pre-commit re-capture loop; everything else is either diagnostic or recovery.

| # | Intervention | Meadows LP | Why | Cost |
|---|---|:-:|---|:-:|
| **V1.2** | **Pre-commit re-capture loop (Genie → customer app)** | **LP3 (structure) / LP6 (new info flow)** | Creates a feedback channel that doesn't exist today. Changes what Genie *is* (from internal learner to bidirectional agent). Bordering on LP2 (goal shift — Genie as truth-seeker, not scorer). | High |
| V3 | Full PMBM integration | **LP4 (rules)** | Rewrites scoring rules within existing stock structure. | Very high |
| V0.3 | New cause codes (GPS_TRUST_FAILURE, ADDRESS_RESOLUTION_FAILURE) | **LP6 (information)** | Changes what H *can see*. Every downstream learner gets richer signal. | Low-medium |
| V0.2 | 7-anchor address packet in D&A OS | **LP6 (info flow)** | New information surface for partner. Doesn't change structure. | Medium |
| V2.1 | Temporal navigation anchor | **LP6 + LP5 (self-organization)** | System learns its own anchors from its own behavior — self-organizing neighborhood memory. | Medium |
| V1.1 | Per-mobile jitter profile | **LP6 (info flow)** | Uses a stock we already have. Personalizes an existing constant (global p95). | Low |
| V2.4 | Customer-side feedback on decline (structurally-different re-capture) | **LP6** if structured differently; **LP12** if "confirm inputs" | Depends entirely on form. Adversarial risk if wrong. | Medium |
| V2.3 | Partner-side hex-reddening WITH decay | **LP5 (self-organization)** | Partner sees their own service map evolve; learns. **Decay is the guardrail.** | Medium |
| V0.1 | 3-check trust layer (HIGH/MED/LOW) | **LP9 (parameters) alone; LP6 if coupled to V1.2** | Alone, a diagnostic. Coupled with re-capture, a control loop. | Low |
| V2.5 | Gaming-detection sub-signal | **LP8 (balancing loop against adversary)** | Adds a B-loop against a reinforcing adversarial loop. | Medium |

**Key takeaway (Donna):** Eight of ten are PMBM-independent. The prize (V1.2) is structural; everything else is either diagnostic (V0.1 alone) or recovery (packet, hex-reddening). Ship V1.2 even if you have to build a thin V0.1 to justify it — because V1.2 is the loop closure that changes what the system *is*, not just how well it scores.

---

## 11. Metrics — both diagnostic and NUT-linked

Geoff's validation flagged a metric design flaw in my original targets. Both **<5% structural drift** and **<1.3 calls/pair** are proxies that can be gamed or mis-optimized:

- *"Structural drift <5%"* is achievable by tightening the 25m gate to reject everyone — drift drops, but so do promises. The metric improves while the business gets worse.
- *"Calls/pair <1.3"* is dangerous because **zero calls with a failed install is worse than three calls with a success**. Per `coordination/`, chain engagement (+10pp install) proves calls are sometimes *the mechanism* of success, not a defect.

So the design tracks **two metric tiers**: diagnostic (operational health, proxy) AND NUT-linked (company value, outcome). Ship both. Optimize the second; monitor the first.

### NUT-linked outcome metrics (primary)

| Problem | NUT-linked metric | Closes which original Wiom pain |
|---|---|---|
| **P1** | **Promise-to-install conversion rate** at held promise volume | *"30% drop-off after commitment"* — the founding pain of Genie's scope |
| **P2** | **First-visit-install rate** and **median minutes-from-notification-to-technician-at-door** (segmented by install success/failure) | *"50% of bookings not installed"* — the other founding pain |
| Both | **Install throughput per partner-week** | Partner productivity → supply-side scaling |

### Diagnostic / proxy metrics (secondary, for operational monitoring)

| Metric | Baseline | Target | Use |
|---|---|---|---|
| Structural drift rate (% installs with drift > Stage A p95) | 25.7% | <10% | Trust layer health |
| Drift p75 | 162.7m | <80m | Capture quality |
| Calls per (mobile, partner) pair | 1.92 | <1.5 (directional, not target) | Coordination load |
| Gali-stuck call-level rate | 7.4% | <3% | Address resolution health |

### Learning-loop health metrics (tertiary, for self-correction)

Per Geoff: cause-code rates are not performance metrics — they are health metrics for the learning loop.

| Metric | What it tells us |
|---|---|
| `GPS_TRUST_FAILURE` rate | Is the trust layer actually catching bad captures? |
| `ADDRESS_RESOLUTION_FAILURE` rate | Is the packet resolving address ambiguity, or still leaking to calls? |
| `gaming_score` distribution | Is adversarial behavior stable, rising, or decaying? |
| Cause-code decomposition of SPATIAL_FAILURE | Can B_spatial distinguish capture failure from actual spatial un-servability? |

### Benchmark references (from HTML Gate 0 + research)

| Source | Intervention | Outcome | Relevance |
|---|---|---|---|
| Swiggy (2023) | Location Inaccuracy Classifier | AUC 0.89, +32pp recall over text-only | Ceiling for V1 classifier upgrade |
| Dunzo (2021) | Full Maps Platform rebuild | −90% support calls, −14% missed ETAs | Aspirational for joint P1+P2 outcome |
| Dunzo | Building-name anchoring specifically | −9.3% location-tagged support | Justification for past-install anchor in V0 packet |
| Pidge + what3words (2022) | w3w alongside raw text | **−63% first-visit failures** | Aspirational for V2 packet |
| India Post (2018) | 3-word addresses in the field | 91% preferred over alphanumeric | Validates w3w feasibility in Indian field-ops |
| Google Maps India (2023) | Address Descriptors API | 98.5% success rate | V2 alternative to Shiprocket NER for landmark extraction |
| Shiprocket (2025) | Open-source Indian-address NER | Free, Apache 2.0, 11 entity types | V0 tool of record |

---

## 12. Phasing summary (Donna-sequenced, 8-week MVP)

Donna's proposed sequence — dependency-ordered, PMBM-independent throughout:

| Week | Deliverable | Why this order | Dep on PMBM? | Dep on Wiom app? |
|---|---|---|:-:|:-:|
| **1-2** | V1.1 (per-mobile jitter profile from `jitter_mobile_v4.csv`) + V0.1 (3-check trust layer, shadow mode) | Profile feeds the layer; layer emits a score nobody consumes yet. Zero downstream risk. | ❌ | ❌ |
| **3-5** | **V1.2 (pre-commit re-capture loop)** — the structural unlock | Requires Wiom-app contract; *start negotiation in parallel with Week 1*. Launches the new Genie → customer-app outbound channel. | ❌ | ✓ (re-capture UI) |
| **4** | V0.3 (new cause codes: GPS_TRUST_FAILURE, ADDRESS_RESOLUTION_FAILURE) | Cheap H-schema extension. **Ship BEFORE V1.2 goes live** so the loop's first failures are cause-coded correctly. | ❌ | ❌ |
| **5-7** | V0.2 (7-anchor packet in D&A OS `genie_context_manager`) + V2.1 (temporal navigation anchor from coordination transcripts) | Lives in D&A OS, depends on Ryan's `/commit` contract. Can be built in parallel with V1.2. | ❌ | ❌ (partner-app only) |
| **6** | V2.5 (gaming-detection sub-signal as trust-layer sibling) | Needs V0.1 live so gaming can be detected vs baseline trust. | ❌ | ❌ |
| **8+** | V2.3 (hex-reddening with decay) + V2.4 (customer-decline re-capture, structurally-different form) | Partner and customer UX layers riding on top of trust + cause-code infra. Decay mandatory. | ❌ | ✓ (both apps) |
| **Later** | V3 (PMBM integration — trust → shrinkage α(i), cause codes → B retrain) | When PMBM Phase 5-6 lands. Nothing in V0-V2 becomes obsolete. | ✓ | ❌ |

### Sequencing guidance (revised post-Donna)

- **Do NOT ship V0.1 alone.** Donna's warning: if trust-layer ships without re-capture, the metric won't move much and leadership concludes "trust layer doesn't work" — then re-capture never gets built. **Either ship V0.1 + V1.2 together, OR frame V0.1 as explicit "Phase 1 of 2, scaffolding for the re-capture loop, not an intervention in itself."**
- **Zero-app-change path (if Wiom app team is bottlenecked):** V0.1 + V0.2 + V0.3 — trust-band tagging, NER-augmented partner packet, cause-code extension. Three moves, pure-backend, measures the problem and gives partners better anchors without a single customer-app change. But *communicate internally as Phase 1 of 2* — don't let the metric underwhelm.
- **Max-value single intervention (both agents unanimous):** V1.2 (pre-commit re-capture loop). Ship it.

---

## 13. Open questions (mirrored from `solution_synthesis.md` §8, for resolution before V1 ships)

1. **Is a Genie → customer-app signal** (RE_CAPTURE_REQUESTED) architecturally in scope for V5? Violates current "Genie only talks to D&A OS + CL OS" boundary. Either add a new outbound contract (Wiom-app OS), or route through CL OS.
2. **New cause codes** (GPS_TRUST_FAILURE, ADDRESS_RESOLUTION_FAILURE) — are these additions to existing taxonomy or new top-level categories? What's the governance for extension?
3. **Who owns the address packet construction** — Genie (violates SAT-01), D&A OS `genie_context_manager` (needs spec), or shared service? Preference: D&A OS builds it, consuming narrow Promise Packet + `booking_logs` directly.
4. **Hex-reddening decay parameters** are LP1 (tuning); the decay *function* (exponential vs linear, time-weighted vs evidence-weighted) is LP4 (rules). Who decides the function, who tunes the parameters?

---

## 14. Known risks (Donna-expanded)

Donna mapped the reinforcing loops hidden in the design. These are the risks that actually matter:

### Already-in-system reinforcing loops to retrofit

1. **L3 — Bayesian shrinkage K=30 prior poisoning (EXISTS TODAY).** Per Donna: same class as hex-reddening — small-n partners converge to the prior and never escape. New-entrant market-expansion risk. **Retrofit evidence-depth-weighted decay to existing shrinkage, don't just apply it to new hex-reddening.** Flagged as CRACK 3 in Promise Maker's own stress tests.

### Reinforcing-loop risks this design introduces

2. **Hex-reddening without decay (V2.3).** Already flagged by me; Donna confirms. Decay function must be load-bearing:
   - `decline_weight = -1.0 × exp(-days/90) × min(1, n_decisions/10)`
   - Single decline in low-evidence hex: soft + transient
   - Repeated declines in high-evidence hex: hard + persistent
3. **Customer-side decline feedback (V2.4) is adversarial if shipped as "confirm your inputs."** Donna: structurally-different re-capture defuses it. Must show fresh evidence (map + boundary) rather than echo inputs.
4. **Gaming detection (V2.5) creates defender-attacker co-evolution.** Classic cat-and-mouse. Mitigation: don't surface detection signature to gamers; keep `gaming_score` separated from `trust_score`; accept 12-18 month decay and plan for refresh.
5. **Pre-commit re-capture (V1.2) is a B-loop that could over-correct.** If τ_retry too aggressive, forces too many re-captures → customer abandonment → funnel destruction. **Mitigation:** ship in shadow mode first, tune τ_retry against observed drop-off before enforcing.
6. **Temporal anchor (V2.1) partner-herding.** Same landmark reinforced; partners stop exploring better anchors. Mild, probably fine, but monitor landmark entropy over time.

### Missing balancing loops (system trying to self-correct, cut)

Per Donna's missing-loops audit — these are the loops the system *should have* but doesn't:

- Genie → capture layer (our V1.2)
- Partner → Genie real-time (beyond 30-day H cycle)
- Coordination outcome → capture UX (gali-stuck in a pincode should shape next booking's capture UI in that pincode)
- CP (Control Pane) — ghost stock; the meta-balancing loop
- Jitter profile → trust threshold (data exists, loop missing — our V1.1)
- Cross-engine signal (coordination failures never reach B_spatial in differentiable form — our V0.3 cause codes)

### Operational risks

7. **Trust layer alone (V0) without re-capture (V1.2) is diagnostic-only.** 25.7% drift rate doesn't decrease because bad coords still enter the gate. Donna warns: if metric moves little in shadow mode, leadership concludes "trust layer doesn't work" and V1.2 never gets built. **Ship V0.1 + V1.2 together, or explicitly frame V0.1 as scaffolding for V1.2.**
8. **Notification-payload size bloat.** Packet has 7-8 anchors + photo/video. Needs app-side rendering prioritization — "strongest clue first" is not optional.
9. **SAT-01 violation risk** — if `trust_score` leaks into Promise Packet, Satyam rejects. All scoring artifacts stay in `genie_context_manager`.
10. **New Genie outbound contract for V1.2** (Genie → customer-app) doesn't exist in current architecture. Needs Satyam sign-off before V1.2 ships. Start negotiation in parallel with V0.

---

## 15. Integration with Promise Maker (when PMBM lands in full)

Each phase's artifact has a named consumer in PMBM:

| V0-V2 artifact | PMBM consumer |
|---|---|
| `location_trust_band` + `trust_score` | B_spatial shrinkage α(i) modifier |
| `mobile_jitter_p95` | Feature in upcoming per-partner spatial scoring |
| `gaming_score` | Eventually B_behavioral input (deferred) |
| NER components + temporal anchor | Partner-app context; can inform R's threshold tuning via CP |
| New cause codes | Directly drives B_spatial's cause-coded KDE retrain |
| Hex-reddening decay | UX layer over existing B_spatial output; no PMBM change |

Nothing we build becomes obsolete when PMBM Phase 5/6 ships. Every V0-V2 artifact is either a feature for PMBM or a UX layer on top of it.

---

## 16. Agent validation — findings + design revisions

Both agents ran in parallel. **Findings converge unanimously on the pre-commit re-capture loop (V1.2) as the single highest-leverage move.**

### Geoff's findings (first-principles RCA)

**Reframes already integrated** (see §1):
- The pain is **not** bad GPS — apparatus is fine (p50 = 7.7m). The pain is that Genie makes a promise on an input it has never interrogated.
- The promise is **structurally premature** — violates Genie's own founding principle that "promise-making and promise-fulfillment are structurally separated."
- Problem 2 is a **structural asymmetry** — customer has gali knowledge Wiom's app never captured; everything else is compensation.

**Metric critique integrated** (see §11):
- *"<5% structural drift"* and *"<1.3 calls/pair"* are gameable proxies.
- NUT-linked metrics adopted: **promise-to-install conversion rate at held promise volume** (P1) and **first-visit-install rate + minutes-from-notification-to-door** (P2). These close directly to Wiom's two founding pains ("30% drop-off" and "50% not installed").
- Cause-code rates (`GPS_TRUST_FAILURE`, `ADDRESS_RESOLUTION_FAILURE`) reclassified as **learning-loop health metrics**, not performance metrics.

**RCA trees** (full versions in Geoff's return): six root causes for P1, five for P2. Each leaf mapped to a specific intervention in this design.

**Geoff's verdict:** *"Ship the pre-commit re-capture loop this quarter. Everything else waits until you can measure promise-to-install conversion on clean captures."*

### Donna's findings (systems thinking)

**Stock-and-flow map integrated** (see §14). Key observations:
- Booking coord stock and text-address stock are both **leaking** (no re-capture, no structural anchors, shown to partner late).
- Per-mobile jitter profile is an **unused stock** (substrate we uniquely have — Swiggy/Dunzo didn't).
- The system currently has **mostly 30-day balancing loops** and **one accidentally-reinforcing loop** — Bayesian shrinkage K=30 **already in production** is a prior-poisoning R-loop. Same class as hex-reddening; needs decay retrofit.

**Missing balancing loops** integrated (see §14):
- Genie → capture layer (the V1.2 unlock)
- Partner → Genie real-time
- Coordination outcome → capture UX
- CP (ghost stock)
- Jitter profile → trust threshold
- Cross-engine signal (coordination → B_spatial)

**Meadows leverage ranking integrated** (see §10). Eight of ten interventions are PMBM-independent.

**Donna's critical sequencing warning** integrated (see §12 and §14):
> "If V0.1 ships without V1.2, the trust score becomes a diagnostic with weak downstream coupling. Leadership may conclude 'trust layer doesn't work' when the metric moves little — then V1.2 never gets built. Ship both together, or explicitly frame V0.1 as scaffolding."

**Reinforcing-loop risks** integrated (see §14): hex-reddening decay, adversarial customer feedback, gaming cat-and-mouse, pre-commit over-correction, temporal-anchor partner-herding. Mitigations specified for each.

**Donna's verdict:** *"Ship V1.2 now, even if you have to build a thin V0.1 to justify it — because V1.2 is the loop closure that changes what the system is, not just how well it scores. Decay is mandatory on every behavioral-reinforcement mechanism. Retrofit the existing K=30 shrinkage too."*

### Design revisions driven by agent validation

| # | Revision | Driver | Where landed |
|---|---|---|---|
| 1 | Reframe: pain is "promise made on pre-evidence", not "bad GPS" | Geoff | §1 (framing) |
| 2 | Metrics shift: NUT-linked conversion + time-to-door replace drift-rate as primary target | Geoff | §11 |
| 3 | Sequencing: V0.1 must not ship alone as an intervention — bundle with V1.2 or frame as scaffolding | Donna | §12 + §14.7 |
| 4 | Decay retrofit to existing Bayesian shrinkage K=30 (pre-existing reinforcing loop) | Donna | §14.1 |
| 5 | Meadows leverage ranking re-ordered; V1.2 placed at LP3/LP6 (structural) | Donna | §10 |
| 6 | Risk inventory expanded from 6 to 10 items + missing balancing loops enumerated | Donna | §14 |
| 7 | Phasing re-sequenced to 8-week MVP (Donna's explicit sequence) with parallel tracks | Donna | §12 |

### Points of unanimous convergence

Both agents, working independently:
1. **Pre-commit re-capture loop (V1.2) is the single highest-leverage move.** Geoff argues from first principles (it's the only intervention that prevents rather than recovers). Donna argues from systems (it's the only intervention that changes what Genie *is*, not how well it scores).
2. **Decay is mandatory on every behavioral-reinforcement mechanism.** Both call out the K=30 shrinkage prior-poisoning loop as already-in-system.
3. **Customer-side decline feedback must be structurally different from "confirm your inputs"** — both flag adversarial risk.
4. **The capture moment is the leverage point.** Everything downstream is compensation.

---

## 17. TL;DR

**The real pain is not bad GPS. It's that Genie makes a promise — and takes Rs. 100 — on an input it has never interrogated.** Geoff's reframe. The promise is structurally premature. It violates Genie's own founding principle: promise-making and promise-fulfillment should be structurally separated. Today they aren't, in spirit.

The capture layer is the leak. Everything downstream is compensation.

**The single highest-leverage intervention (both Geoff and Donna unanimous):** the **pre-commit re-capture loop (V1.2)**. It adds a balancing feedback loop from Genie back to the customer app that doesn't exist today. Changes what Genie *is*, not just how well it scores. Every other intervention (trust bands, packets, hex-reddening, PMBM) is either diagnostic or recovery. This is the only one that prevents.

**The 8-week MVP sequence (Donna):**
- **Weeks 1-2** — V0 backend: per-mobile jitter profile + 3-check trust layer (shadow mode) + new cause codes + NER-augmented packet. Zero customer-app dependency. Pure measurement and partner-side enrichment.
- **Weeks 3-5** — V1.2 ships (Genie → customer-app re-capture loop). Start Satyam architectural negotiation in parallel with Week 1.
- **Weeks 5-7** — V2 partner-side: temporal navigation anchor from coordination transcripts + packet enrichment in D&A OS.
- **Week 8+** — V2 UX closure: hex-reddening with decay, structurally-different customer re-capture, gaming-detection.
- **Later (parallel to PMBM Phase 5-6)** — V3: trust score feeds Bayesian shrinkage, cause codes retrain B_spatial.

**The three critical disciplines (both agents):**
1. **Do not ship V0.1 alone** as an intervention. Either bundle with V1.2, or explicitly frame as "Phase 1 of 2, scaffolding." Donna's warning: a diagnostic without action becomes an argument against the action.
2. **Decay is mandatory on every behavioral-reinforcement mechanism.** Retrofit to the existing Bayesian shrinkage K=30 too — it's a prior-poisoning loop already in production.
3. **Primary metrics are NUT-linked**, not proxy. Promise-to-install conversion at held volume (P1) and first-visit-install rate + minutes-to-door (P2). These close directly to Wiom's two founding pains. Cause-code rates are learning-loop health metrics, not performance metrics.

Maanas's reset ask — *"start simple, no PMBM assumption"* — is structurally honoured. Eight of ten interventions are PMBM-independent. Nothing ships that presumes PMBM Phase 5-6 is live; nothing we ship becomes obsolete when it does.
