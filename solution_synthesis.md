# Solution Synthesis — Location Signal Audit

**Author:** `story_teller_part1` (cross-engine synthesis session)
**Drafted:** 2026-04-20
**Scope:** This file is where the *design* lives, kept deliberately separate from the two Gate 0 thinking contracts (`problem_statements/problem_1_*.md`, `problem_statements/problem_2_*.md`) because Satyam's template is a thinking contract, not a design document. I am free here to critique, push back, and propose.
**What I've read to get to this point:**
- The three-engine analyses (`promise_maker_gps/` Stages A+B, `allocation_signal/`, `coordination/`)
- Maanas's `possible_solutioning_approaches/` (his own notes + Gate 0 HTML)
- Promise Maker's system docs, `B/` code, Satyam collaboration, Ryan collaboration (via subagent synthesis)
- The two Gate 0 thinking contracts

---

## 1. The substrate — Promise Maker as it actually exists

Before I critique or innovate, I need to ground in what Promise Maker *already is*. Maanas's `Possible_Solutioning_Approaches.txt` sketches PMBM at a high level ("personalized partner hexes + KDE + composite scores"). The system is actually further along than that framing implies.

### The six-stock architecture (V5, currently in build)

| Stock | Role | State |
|---|---|---|
| **G (Gatekeeper)** | Three hard gates before scoring — 100m distance threshold, integrity blocks from Enforcement OS, execution path checks from Quality/Exit OS. Constitutional-grade. | Built, quarterly cadence |
| **B (Belief Model)** | Parallel physics modules. `B_spatial` is live — KDE adaptive Gaussian fields with log-weighted evidence decay, multiresolution hex grids auto-sized per partner, hex color buckets (lightgreen/orange/crimson by install rate), contested-field overlap signals. `B_operational` is spec'd (Phase 0-6 roadmap). `B_behavioral` deferred. | `B_spatial` in prod (`B/compute/compute.py`); Bayesian shrinkage Phase 5 rolling out |
| **R (Governor)** | Applies composite threshold to B's output, assigns confidence tiers, manages exploration quota, re-evaluates live commitments on shocks | Threshold empirically tuned via CP retro |
| **E (Active Exposure)** | MySQL `t_active_commitments` — live moral debt. Insert on COMMIT, drain to H on resolution. | Built |
| **S (Shock Ledger)** | `t_shock_ledger` — external shocks from Quality/Exit/Enforcement OS | Schema defined, bilateral contracts in negotiation |
| **H (Calibration Memory)** | Immutable append-only. Every evaluation lands here. Learning signal. | Built |
| **CP (Control Pane)** | Conceptual role — reads H/E/S, detects drift, adjusts R thresholds or triggers B re-tune | **Ghost stock — not yet implemented.** |

### What `B_spatial` actually produces per lead × partner

- `predicted_field_hex` — KDE value at the lead location, sourced from the partner's install/decline history (installs +1.0, declines −1.5/−2.0), lambda-decay 0.005, max radius 15km
- `parent_color_super` — hex installation-rate bucket (lightgreen >60%, orange 30-60%, crimson <30%, indeterminate <4 installs)
- `contested_field` — overlap with another partner's coverage
- `parent_total` — evidence depth in the hex (used for shrinkage weight)
- `parent_se` — install rate in the hex

Composite (current, pre-shrinkage):
```
spatial_raw = w1·norm(predicted_field_hex) + w2·color_numeric/3
```

With Bayesian shrinkage (Phase 5):
```
α(i) = parent_total(i) / (parent_total(i) + K)        # K ≈ 30
prior = weighted_avg(spatial_raw, log(1+parent_total))
spatial_shrunk(i) = α(i)·spatial_raw(i) + (1-α(i))·prior
partner_score(i) = spatial_shrunk(i) × operational_score(i)
lead_score = aggregation(partner_scores[])
```

### The self-learning loop

```
Evaluation (B→R) → COMMIT to D&A OS → Partner allocated → Install attempt
    ↓
ALLOC_CONTEXT from D&A OS (resolution_type, csp_decline_flag, reallocation_cause)
    ↓
CAUSE-CODING (SPATIAL_FAILURE / OPERATIONAL_FAILURE / ALLOCATION_FAILURE / USER_DROP / …)
    ↓
E drain → H insert with cause code
    ↓
B retrain (daily) — field weights update on cause-matched records
CP reads H → adjusts R threshold / K / weights
```

**Loop latency: ~30 days.** **Linchpin: cause-coded ALLOC_CONTEXT from D&A OS** — if that signal doesn't arrive or isn't cause-coded, `B` can't distinguish spatial failure from allocation failure from user drop. The learning loop collapses. This is DEP-07 in Ryan's product-team-outreach docket.

### Satyam's closures worth knowing

- **SAT-01 (pending):** Promise Packet narrows to decision-only (decision, evaluation_id, validity_window, exploration_flag, confidence_tier). **Scoring artifacts stay internal.** Implication: a 7-anchor address packet for partners **cannot ride in Genie's Promise Packet**. It must live in D&A OS's `genie_context_manager` or as a separate downstream contract.
- **SAT-02 (withdrawn):** Reject-cause description retained for CL OS.
- **SAT-03 (pending):** SPR registration for CL OS deferral governance parameters.

---

## 2. Where Problem 1 and Problem 2 actually plug in

This is where the subagent's architectural synthesis clarifies things the Gate 0 contracts alone couldn't.

### Problem 1 (Location Trust) plugs in as **pre-B_spatial**

```
Raw booking GPS (lead_lat, lead_lng, booking_accuracy)
    ↓
[TRUST LAYER — PROBLEM 1]
    3-check (cluster, pincode, near-past-install) + classifier + Stage A p95=154.8m jitter floor
    Output: trust_score ∈ [0,1], clean_(lat,lng), gps_confidence, drift_vector
    ↓
B_spatial (existing)
    predicted_field_hex computed on trusted coord
    Bayesian shrinkage can incorporate gps_confidence (lower conf → more pull toward prior)
    ↓
R + E + Promise Packet
```

New module location: `B/compute/trust_location_gateway.py` (per subagent's integration note), called from `compute.py` before `compute_adaptive_gaussian_field`.

### Problem 2 (Address Packet) plugs in as **D&A OS context, NOT Promise Packet**

Per SAT-01, scoring artifacts stay internal. The packet is a **downstream artifact that enriches D&A OS allocation context**, not a Genie output.

```
Genie emits Promise Packet (narrow): decision, evaluation_id, validity_window, confidence_tier
    ↓
D&A OS receives Promise Packet + builds enriched dispatch context
    ↓
[PACKET BUILDER — PROBLEM 2]
    7-anchor packet (verified lat/lng from trust layer, past-install anchor, w3w, NER, ward, photo, raw)
    Lives in D&A OS's genie_context_manager, consumed by partner app
    ↓
Partner app renders "strongest clue first" view
    ↓
Coordination call (if needed) — with structured fields + optional photo/video
    ↓
Outcome → ALLOC_CONTEXT → cause-code → H → B retrain
```

If the address packet resolution fails (gali-stuck, partner can't find), that fires a **new cause code** back into H. Genie learns not just "this area is spatially hard" but "this area has *coordination* fragility" — a signal orthogonal to B_spatial's distance geometry.

### The bidirectional channel Maanas's design implies but doesn't spell out

Maanas's feedback loops (hex-reddening on partner decline, customer sees submitted details + video link) hint at a loop that currently doesn't exist in Promise Maker's formal architecture: **Genie → capture layer**. Today Genie reads from H and adjusts internal parameters. It does not push signal back to the customer app to say *"your GPS was untrustworthy, please re-capture."*

Adding this loop is actually the biggest structural leverage in either problem. More on this in §4.

---

## 3. What Maanas's solution approach gets right

Before I critique, the high-fidelity parts — these don't need innovation, they need execution:

1. **PMBM as the ML destination is on-target.** It's not hypothetical; it's Phase 5 + Phase 6 of `NEXT_STEPS_BELIEF_MODEL_EVOLUTION.md`. Per-partner spatial scoring + Bayesian shrinkage + multiplicative fusion with operational is already in the pipeline.

2. **Hex + KDE + composite scores mechanics are already built.** `B/compute/compute.py` has this. Maanas's notes describe the system Wiom *already has* more than a system to build.

3. **Three-check trust layer (Swiggy/Dunzo playbook) is the right MVP.** Cheap, composed from existing repo assets (`partner_cluster_boundaries.h5`, ward enricher, install history), produces a numeric signal `B_spatial` can consume immediately.

4. **Place intelligence reframe ("system should send a verified, behaviorally grounded, partner-recognizable install location, not an address") is correct.** This is the same structural observation SAT-01 makes from the opposite direction — scores are internal; only facts cross membranes.

5. **Hex-reddening on partner decline is a genuinely novel operational proposal.** Promise Maker currently reflects decline signal into B_spatial's KDE weights (declines at −1.5/−2.0). Surfacing that gradient *to the partner in real time on their service map* — so they can see their polygon reddening in regions they declined — is a UX closure the current system doesn't have. This extends the feedback loop from system-internal to partner-visible.

6. **Customer-side re-submission with video/photo** when partner declines is good, with caveats (see §4).

---

## 4. What I'd critique or push back on

### Critique 1 — Static trust layer misses the real leverage

Maanas's 3-check trust layer operates on a single captured coord. It's Stage A-blind — it doesn't know that *this* capture, from *this* phone, in *this* environment, has high or low intrinsic jitter.

Stage A gave us the apparatus noise floor (p95 = 154.8m). That number is a population average. A mid-range Android indoors at 11pm has a much wider distribution than a flagship outdoors at noon. Treating them identically wastes the signal.

**What I'd add:** per-phone × per-environment jitter buckets, learned from the repeat-ping data we already have (`gps_jitter/investigations/jitter_mobile_v4.csv`). Known-device profiles give us a personalized p95 instead of a global one. A cheap Android with a history of wide jitter should get LOW-trust at a much tighter drift threshold than a clean flagship.

**This is only possible because Wiom has the repeat-ping data.** Swiggy and Dunzo built their trust layers without this substrate. We have it.

### Critique 2 — The 7-anchor packet over-indexes on static anchors

The packet Maanas sketched is mostly static: lat/lng, w3w, NER, ward. These are useful but they don't *learn*. Dunzo's −9.3% from building names came from **behavioral recognition** — showing the partner the building name *the last partner used* to find this building. That's a temporal, partner-navigation-corridor signal, not a static geocode.

**What I'd add as the 8th anchor:** `recent_partner_navigation_trace` — for the last 5 installs within 100m of this booking, what landmark did the partner actually call out to the customer? (Minable from `../coordination/` transcripts + address-chain tags.) This anchor *learns* — it reflects what partners in this neighborhood actually navigate by. It's the Donna-flavored "neighborhood-memory artifact" suggested in `../coordination/README.md`, made concrete.

### Critique 3 — Hex-reddening as proposed has a prior-poisoning bug

Maanas's proposal: partner declines → hex reddens → no future leads in that hex for that partner. This is exactly the same shape as Bayesian shrinkage's K=30 convergence-lag vulnerability the Promise Maker stress tests flagged (CRACK 3 in subagent output).

A single decline in a new hex shouldn't permanently remove the partner from that area's allocation pool. Otherwise:
- A partner has a bad day, declines one booking in a new zone
- That zone reddens for them
- No future leads route there
- They never get the chance to calibrate their own serviceability
- The reddening becomes a self-fulfilling prophecy

**What I'd add:** hex-reddening decays with time AND with evidence depth. A single decline in a low-evidence hex reddens it softly and transiently. Repeated declines in a high-evidence hex redden it harder and longer. This is Bayesian shrinkage's logic applied to UX, not just scoring. Without time/evidence decay, this feature will calcify partner service zones in a way that hurts market expansion.

### Critique 4 — Customer-side feedback can create adversarial pressure

"On partner decline, customer sees their submitted details + video link with a 'confirm or correct' CTA."

The unspoken assumption: the customer will correct if they were wrong.

The adversarial case: the customer is *committed* to a wrong location (they want service at a location Wiom doesn't actually serve, or they gamed GPS to pass the 25m gate). Showing them their own submission + asking for confirmation invites **doubling down**, not correction. Per `../allocation_signal/`, there's an existing splitter-share-gaming pattern where partners submit self-serving splitter lat/lngs (31pp install-rate gap at matched prob decile). The analogous customer-side gaming — repeat bad captures from same mobile, or deliberate wrong-address declaration — is real and would be amplified by this feedback loop.

**What I'd add:** the re-capture UX should be **structurally different from the original capture**, not a "confirm your earlier inputs" flow. Force a live GPS re-acquisition with environmental checks (stationary for ≥10 seconds, accuracy self-report within threshold, time-of-day validation). Also cross-validate against third-party signals the customer can't fake (pincode reverse-geocode, IP-based geolocation).

### Critique 5 — No explicit signal for Genie → capture layer

This is the most important structural gap in Maanas's design. Currently:
- Genie reads H and adjusts itself
- Genie sends decisions forward to D&A OS
- **Genie does NOT tell the customer app "your input was low-trust, please try again before I promise"**

The trust layer, as sketched, produces a score used internally. But the capture layer (Wiom app) doesn't receive this score. So bad captures keep happening at the same rate.

**What I'd add (biggest leverage of anything in this synthesis):** a formal **LOW-trust → re-capture** signal from Genie back to the customer app, *before* the 25m gate fires, *before* the fee is captured, *before* the promise is made. This closes Layer 4 (Learning loop) of the 4-layer architecture Maanas's AI conversation described but the code doesn't implement.

Concrete form:
```
Customer submits GPS (step 4 of flow)
    ↓
Trust layer evaluates (not yet part of Promise Maker — new)
    ↓
If trust_score < τ_retry:
    → App shows "Let's try that again — please make sure you're at your home with clear sky if possible"
    → Force live re-acquisition, min accuracy, min stationary duration
    → Re-evaluate
    → If still LOW after N retries: escalate to structured-address capture (pincode, landmark, floor) BEFORE fee capture, use as pre-promise cross-validation
If trust_score ≥ τ_retry:
    → Proceed to 25m gate
```

This is a **pre-commit** loop. It operates before Genie ever sees the coordinate. Every call reduces the rate at which bad coords enter Genie at all.

### Critique 6 — Gaming and GPS noise currently collapse into one signal

Stage B's 25.7% structural drift lumps together: a genuine GPS fix 500m off due to multipath, and a deliberately misrepresented lat/lng. Both look the same to the measurement. But they have different fix profiles:

| Pattern | Genuine noise | Gaming |
|---|---|---|
| Repeat-ping variance from same mobile | High (GPS jitter) | Low (repeated deliberate coord) |
| `booking_accuracy` self-report | Often high | Often artificially low |
| Time-of-day clustering | Yes (indoor/night skew) | No |
| Correlation with partner-side decline pattern | Negative (good partners help) | Positive (all partners decline when gaming is detected) |

**What I'd add:** a gaming-detection sub-signal inside the trust layer. Currently Stage A excludes the 250m home-move pings to keep the jitter distribution clean; the excluded pings are a cohort we should mine. Repeated same-mobile wide-drift captures are gaming suspects, not noise.

### Critique 7 — Cause-code fidelity for new failure modes

Per the Promise Maker subagent: ALLOC_CONTEXT without cause-coding collapses the learning loop. If Problem 1 and Problem 2 fix their respective symptoms but keep dumping all declines into `SPATIAL_FAILURE`, the system learns nothing new.

**What I'd add:** two new cause codes in H's taxonomy:
- `GPS_TRUST_FAILURE` — the booking's coord was low-trust; downstream failure probably tracks upstream capture, not spatial or operational
- `ADDRESS_RESOLUTION_FAILURE` — partner reached the right block but couldn't resolve gali/floor; coordination failure orthogonal to spatial

These become new first-class learning signals for `B_spatial` (weights them differently from spatial failure) and `B_operational` (when online, it learns the address resolution dimension separately).

---

## 5. What I'd innovate

Five additions on top of Maanas's base design:

### Innovation 1 — The pre-commit trust loop (restated as an architectural contribution)

This is the biggest one. Detailed in Critique 5. The punchline: **every problem downstream of a bad capture is downstream of a bad capture**. If Wiom intercepts bad captures at Layer 1 (user truth capture), Layers 2-4 don't have to heroics to recover. This is the Meadows-grade systems intervention — it adds a balancing loop (the "I don't trust this, try again" feedback) that currently doesn't exist.

Concretely: this is a **signal to the customer app from Genie**, formally outside the current Promise Maker architecture (Genie today only emits to D&A OS and CL OS). A new outbound contract, but a constitutional addition.

### Innovation 2 — Per-phone × per-environment jitter profiles

From Critique 1. We have the data (repeat pings per mobile). Build a per-mobile jitter percentile that replaces the global Stage A p95 for trust-layer thresholding. A known-clean mobile with p95 = 25m gets a tighter drift tolerance than a known-noisy mobile with p95 = 400m. Fails gracefully for new mobiles (fall back to global p95).

Implementation: `gps_jitter/per_mobile_profile.py` — reads `jitter_mobile_v4.csv`, emits a per-mobile p50/p75/p95. Cache. Trust layer looks it up on each call.

### Innovation 3 — Temporal anchor in the address packet

From Critique 2. New 8th anchor: `recent_partner_navigation_trace` — minable from `../coordination/` transcripts, specifically the `addr_chain_evidence` field + partner install outcome. Rank nearby past installs by (recency × install-success) and extract the landmark phrase the successful partner actually used. Show that phrase to the next partner.

This replaces "near SBI" (which has 3 branches) with "near the SBI that Ram from Partner-P0037 went to last Tuesday" — a behaviorally validated anchor.

### Innovation 4 — Gaming-detection sub-signal

From Critique 6. The trust layer should emit not one score but two: `trust_score` and `gaming_score`. Treated differently downstream — trust_score calls for re-capture; gaming_score calls for human review or block. Features for gaming_score include: repeat-ping variance from same mobile, implausible accuracy self-report, time-since-app-install, correlation with known fraud patterns.

### Innovation 5 — New cause codes + B retraining with them

From Critique 7. Add `GPS_TRUST_FAILURE` and `ADDRESS_RESOLUTION_FAILURE` to the cause taxonomy in H. Update cause-coding logic. Version H schema (which the subagent flagged as a gap — no versioning today). Retrain `B_spatial` with the new codes: spatial failures now have three sub-types, each weighted independently.

This lets the system *learn the difference* between "this area is hard to serve" and "this area has bad GPS capture" and "this area has good GPS but bad addresses" — three different interventions, three different operational actions.

---

## 6. Integration plan — phased

| Phase | Goal | What lands | Blocks on |
|---|---|---|---|
| **Phase 0 (pre-build, 1 week)** | Close analysis open items | Stage B × time_bucket + booking_accuracy correlation + declined-cohort comparison (in `promise_maker_gps/booking_install_distance/`); frequency table of landmark/gali/floor taxonomy from `coordination/` | Maanas to execute; data pulls |
| **Phase 1 (1-2 sprints)** | Build the trust layer as pre-B_spatial module | `B/compute/trust_location_gateway.py` — 3-check + classifier + Stage A p95 floor + per-mobile profile (Innovation 2). Shadow mode first. | Phase 0 closure; downstream audit ("does `booking_lat/lng` flow anywhere that matters?" — flagged in the HTML report); CRM label setup for self-supervised classifier training |
| **Phase 2 (1 sprint, parallel)** | Pre-commit re-capture loop (Innovation 1) | New customer-app signal from Genie: LOW-trust → force re-capture UI. Requires Wiom app change. | Phase 1 trust-layer threshold; Wiom customer-app team |
| **Phase 3 (1-2 sprints)** | Address packet in D&A OS context | Packet builder in `genie_context_manager` (per Ryan's Round 7 architecture); 7 anchors + Innovation 3 (temporal anchor); partner app renders "strongest clue first" | SAT-01 ratification (narrow Promise Packet); D&A OS contract agreement; Shiprocket NER + w3w infra |
| **Phase 4 (1 sprint)** | Gaming-detection sub-signal + new cause codes | Innovation 4 (gaming_score) + Innovation 5 (new cause codes in H + B retrain) | Phase 1 live; H schema versioning resolved (subagent's flagged gap) |
| **Phase 5 (ongoing)** | Partner-side hex-reddening feedback with time/evidence decay | Maanas's proposal, with Critique 3's decay fix. Partner app shows service-zone evolution. | Phase 3 partner-app UI infra; time-decay parameter calibration |
| **Phase 6 (long-term, parallel to PMBM Phase 6)** | Continuous GPS streaming into B_spatial | New L1 feature in 4-layer architecture. Rebuild trust layer as adaptive (learns per-phone × per-environment jitter online). | Wiom app telemetry change; `B_spatial` training pipeline extension |

---

## 7. Bright-line principles I'd hold

These are structural invariants I'd defend throughout the build:

1. **SAT-01 is non-negotiable.** Scoring artifacts don't cross from Genie to D&A OS. Packet lives in `genie_context_manager`, not Promise Packet.
2. **The pre-commit re-capture loop is the signature intervention.** Everything else is recovery; this is prevention. Don't let it get descoped under timeline pressure.
3. **Cause-code fidelity is the learning-loop linchpin.** Don't ship new capture mechanisms without extending the cause taxonomy; otherwise B learns nothing.
4. **Decay is mandatory on any partner-side behavioral feedback.** Hex-reddening without time/evidence decay poisons priors and locks in service zones.
5. **Trust score is an internal Genie artifact.** It can gate re-capture (Innovation 1) and it can feature into B (shrinkage weight adjustment). It does not appear in Promise Packet.
6. **Customer re-capture must be structurally different from initial capture.** Not "confirm your inputs" but "let's try this again, actively, differently."

---

## 8. Open questions for Satyam

These need conversation, not just analysis:

1. **Is a Genie → customer-app signal** (Innovation 1) architecturally in scope for V5? It violates the current "Genie only talks to D&A OS + CL OS" boundary. Either add a new outbound contract (Wiom-app OS), or route through CL OS.
2. **New cause codes** (GPS_TRUST_FAILURE, ADDRESS_RESOLUTION_FAILURE) — are these additions to existing taxonomy or new top-level categories? What's the governance for taxonomy extension?
3. **Who owns the address packet** — Genie emits it (breaks SAT-01), D&A OS builds it (needs spec), or a new shared service? My preference: D&A OS's `genie_context_manager` builds it, consuming narrow Promise Packet + `booking_logs` directly. Ryan has sketched this; needs closure.
4. **Hex-reddening decay parameters** are LP1 in Meadows terms (parameter tuning). But the decay *function* (exponential vs linear, time-weighted vs evidence-weighted) is LP4 (rules). Who decides the function, who tunes the parameters?

---

## 9. Where I'd differ from the HTML Gate 0 report

The HTML report (`possible_solutioning_approaches/wiom_location_address_gate0_report.html`) is excellent but under-weights four things I think matter:

1. **It treats the trust layer as a post-hoc validator.** My read: it should be pre-commit, not post-hoc. The report's LOW-trust → SMS map-pin fallback happens *after* the lead has already entered Genie. Better: it happens *before* the 25m gate evaluates.
2. **It doesn't mention per-mobile jitter profiles.** Swiggy/Dunzo don't have the substrate; Wiom does. This is a competitive edge the report doesn't claim.
3. **Its packet is static.** No temporal anchor from partner-navigation transcripts. Missing the Dunzo-style behavioral signal.
4. **It doesn't engage with Promise Maker's architecture.** The report reads as if B_spatial + Bayesian shrinkage + PMBM don't exist. They do, and they change where the trust layer plugs in and how the feedback loop closes.

Framing difference: the HTML is a *pitch*. My synthesis is an *architecture review*. Both are useful; the pitch gets stakeholders aligned, the review gets engineers building the right thing.

---

## 10. Where the storyline goes next

Once `promise_maker_gps/` closes its open analyses (declined cohort, time_bucket slice, booking_accuracy correlation), we'll have the data to calibrate:
- Per-mobile jitter profile thresholds (Innovation 2)
- Trust-classifier features (Phase 1)
- Re-capture τ_retry threshold (Phase 2)

The full story I'll assemble once those land: **the customer's booking GPS is 3-8× noisier than the apparatus. The downstream systems (allocation, coordination, install) heroically absorb most of this noise, but ~26% of bookings still carry structural capture error that no downstream system can recover. The fix is at the capture moment, and the mechanism is a bidirectional trust channel that Wiom's existing Promise Maker architecture almost-but-not-quite implements today. Everything else — better addresses, better partner anchors, better allocation ranking — is downstream compensation. Solving the capture layer unlocks the rest.**

That's the one-paragraph version of the audit. The three-engine work in PWD proves it. The solutions here enact it.