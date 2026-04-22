# Solution Proposals — Visual

**Companion to** `solution_design.md` and `solution_synthesis.md`. Same interventions, rendered as flow diagrams rather than prose — intended for quick read when Rohan / Ryan / reviewers want the shape of the change before reading the build spec.

---

## The reframe that shaped both solutions

Before the interventions, the pain itself was reframed (Geoff's validation, agent round):

> **The real pain is not bad GPS.** Stage A proved the apparatus is fine (p50 = 7.7m). The pain is that **Wiom makes a promise — takes Rs. 100 — on an input it has never interrogated.** The promise is *structurally premature*. It violates Genie's own founding principle: "promise-making and promise-fulfillment should be structurally separated." Today they aren't, in spirit.

> **Problem 2 is a structural asymmetry** — the customer *has* the gali knowledge; Wiom's app never captured it. Every downstream intervention (landmark prompts, photos, calls) is compensating for the original capture form asking "free text address" post-payment with no validation.

**The capture layer is the leak. Everything downstream is compensation.**

---

## Problem 1 — Location Estimation (Point A, Wiom's promise decision)

### Today's flow (where it breaks)

```
Customer opens app at home (or not at home)
   │
   ▼
Submits one GPS fix (single-shot)
   │                              ◄── 25.7% structurally wrong (>154.8m drift)
   ▼                                   no validation, no re-capture loop
25m gate checks: infrastructure within 25m of captured coord?
   │                              ◄── gate tests GEOMETRY vs INFRASTRUCTURE,
   ▼                                   not coord vs TRUTH
Pass → Fee (Rs.100) captured
   │
   ▼
PROMISE MADE ◄──── this is the moment the commitment is locked,
   │                 on an input Wiom has never questioned
   ▼
Text address typed (free-form, POST-payment)
   │
   ▼
Allocation → partner arrives at wrong building
```

### Proposed flow (revised — landmark-confirmation)

The earlier 3-check classifier + graceful-degradation ladder was replaced after Maanas pushed back on pincode-size, ladder friction, and typed-address fallback. The revised design interrogates the *customer*, not the coord — via landmark confirmation. It's structurally simpler and **collapses the earlier V0 (trust bands) + V1 (pre-commit re-capture loop) into a single intervention**.

```
Customer submits home GPS
     │
     ▼
┌──────────── LAYERED CONTAINMENT (reads polygons only) ────────────┐
│                                                                   │
│  A. Inside any partner's service cluster polygon?                 │  ← existing
│     (partner_cluster_boundaries.h5)                               │    asset
│                                                                   │
│  B. Else: inside Wiom's city envelope?                            │  ← new derived
│     (convex hull of all installs in that city, daily recompute)   │    stock
│                                                                   │
│  C. Else: truly sparse (never served nearby)                      │
│                                                                   │
│  (+ mobile_jitter_profile as internal plausibility prior —        │  ← retained
│     known-noisy mobiles with borderline fixes get gentle routing) │    for gaming
│                                                                   │    detection
└────────┬──────────────────────────┬───────────────────────────────┘
         │                          │
   A or B (contained)           C (sparse)
         │                          │
         ▼                          ▼
┌──── LANDMARK_CONFIRM ──────┐   ┌──── LANDMARK_SPARSE ─────┐
│                            │   │                          │
│ Google Address Descriptors │   │ Same flow, but confirmed │
│ → 3-5 landmarks near coord │   │ landmarks route to       │
│                            │   │ sparse_area_queue        │
│ + round-2 fallback anchors │   │ (expansion-demand        │
│   from Wiom install        │   │ signal; density-gated,   │
│   history ← LOCAL TRUTH    │   │ not single-point)        │
│   (covers Google's gaps in │   │                          │
│   hyperlocal Indian mandir,│   │ No promise today.        │
│   kirana, gali names)      │   │ Routed to Wiom-product   │
│                            │   │ expansion review.        │
│ + 20-25% false-landmark    │   │                          │
│   probe (gaming defense —  │   └──────────────────────────┘
│   Geoff's refinement)      │
│                            │
│ Customer prompt:           │
│ "Which of these is within  │
│  2-3 min walk of your      │
│  HOME specifically?"       │
│                            │
│ REQUIRES 2 CONFIRMATIONS   │  ← Geoff's refinement:
│ (intersection of "near     │    defuses Priya-at-office
│  home" + "near anywhere    │    case; home∩office set
│  customer might be         │    is smaller than either
│  geographically literate"  │    alone
│  is the real home)         │
│                            │
└───────────────┬────────────┘
                │
   ┌────────────┼─────────────────────────────┐
   │            │                             │
   ▼            ▼                             ▼
confirms ≥2,  denies all                    probe
no probe-fail                               failure
   │            │                             │
   │            ▼                             ▼
   │     Round 2 (install-history      gaming_flag_stock
   │     anchors — hyperlocal)         booking held,
   │            │                      human review
   │     ┌──────┴──────┐
   │     │             │
   │   ≥2 confirm   deny all
   │     │             │
   │     │             ▼
   │     │   "You're not at home.
   │     │    Please go home and
   │     │    submit again."
   │     │    [+ offer CRE callback
   │     │     as PARALLEL path,
   │     │     not only post-failure]
   │     │            │
   │     │   ┌────────┴────────┐
   │     │   │                 │
   │     │   │          second attempt
   │     │   │          fails similarly
   │     │   │                 │
   │     │   ▼                 ▼
   │     │ re-submit    CRE_callback_queue
   │     │ restart      (no infinite loop)
   │     │ flow
   │     │
   │     ▼
   │  proceed
   │
   ▼
25m gate (on validated coord)
   │
   ▼
Fee (Rs.100) + Promise ◄── now with interrogated evidence
   │
   ▼
confirmed_landmarks_per_booking ─────────────►  PROBLEM 2 partner packet
     ↑                                          (★ DUAL-PURPOSE — Donna's
     │                                            non-negotiable)
     │  This is the NON-NEGOTIABLE data flow:
     │  the same customer interaction that
     │  validates Problem 1 feeds Problem 2's
     │  partner packet with customer-affirmed
     │  landmark anchors. Without this,
     │  leverage halves.
```

**Core insight (revised per agents):** the revision doesn't just interrogate the *coord* — it interrogates the *customer's relationship to the location*. Geoff's framing: "the only entity with ground truth about home-proximity is the customer." The earlier trust-score classifier was system-talking-to-system; landmark-confirmation is system-talking-to-human. Different question, different answer.

**Why this is leverage-positive vs the earlier ladder (Donna):** the earlier design had V0 (trust bands) at LP9 (parameters — weighted heuristic sum) and V1 (pre-commit loop) at LP3 (structure). The revision collapses both into one LP5 (self-organizing — uses the system's own emergent partner-polygon structure) + LP6 (information flow — customer's own knowledge as a new signal). One shipment, higher leverage, no "don't ship V0 alone" discipline needed.

**Three non-negotiables (Donna):**
1. `confirmed_landmarks_per_booking` MUST propagate downstream into Problem 2's partner packet as a first-class field (not nice-to-have). Without this, the customer did the work and only Problem 1 benefits.
2. Containment check reads **polygons only** (not KDE). Keeps the pre-promise gate PMBM-independent. KDE can enrich the packet later, post-promise.
3. Instrument "go home" abandonment from day 1. If >8-10%, soften the message (CRE callback as parallel path, not only post-failure).

**Operational cushions (Donna):**
- Cache Google AD responses per hex (rolling 7-day) for API-outage resilience. Fail-OPEN, never fail-closed on external dependency.
- Sparse-area queue density-gated: require ≥5 confirmations in a 500m hex within 30 days before triggering expansion review.
- Rotate gaming-probe style over time (false landmarks + ambiguous-but-real landmarks); accept 12-18 month cat-and-mouse cycle.

---

## Problem 2 — Address Translation for CSP (Point B, Partner's decision)

### Today's flow (where it breaks)

```
Customer types address POST-payment (free text, one blob)
   │                      ◄── "Flat 3B Green Apts, near SBI, Lajpat Nagar-III, Delhi 110024"
   ▼                          (3 SBIs in Lajpat, 2 Green Apts — ambiguous)
Stored as raw string
   │
   ▼
Allocation → partner notification
   │                      ◄── MAP + STRAIGHT-LINE DISTANCE only
   │                          text address HIDDEN until click-through
   ▼
Partner decides (on geometry, not content)
   │
   ▼
Partner clicks through → finally sees raw string
   │
   ▼
Partner calls customer
   │                      ◄── 1.92 calls per pair average
   │                          7.4% stuck at gali (biggest bottleneck)
   │                          46% of "address unclear" calls = partner
   │                               confused, customer CLEAR (one-sided)
   │                          41% of ANC pairs never reach the gali step
   ▼
Technician dispatched → wrong building → reschedule
```

### Proposed flow

```
Customer types address
   │
   ▼
┌──────────── CAPTURE UPGRADE (customer-side) ───────────┐
│  + Shiprocket NER parses → structured fields           │  ← free, Apache 2.0
│    (unit, building, landmark, locality, pincode)       │
│  + Landmark confirmation via chat (Google Address      │  ← Maanas's addition
│    Descriptors API)                                    │
│  + Photo of street/building entrance (if trust MED)    │
│  + 15-30 sec reel-style video from landmark (if LOW)   │
│  + what3words code generated                           │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
   ┌───────── PACKET BUILDER (D&A OS's genie_context_manager) ─────────┐
   │   Lives in D&A OS, NOT in Promise Packet (SAT-01 compliance)      │
   │   7 anchors, over-determined by design:                           │
   │                                                                   │
   │   1. verified lat/lng (from Problem 1's trust layer)              │
   │   2. NEAREST PAST INSTALL ANCHOR ★ STRONGEST                      │
   │      "Same building as install I8831213, 18m NE,                  │
   │       2F, installed 12 days ago"                                  │
   │   3. what3words code: "filled.count.soap" / "भरा.गिनती.साबुन"       │
   │   4. NER components: unit=3B, building=Green Apts, landmark=SBI   │
   │   5. Ward admin: ward_id=101, ward_name=Lajpat Nagar (S)          │
   │   6. Customer photo/video (optional)                              │
   │   7. Raw text (preserved, bottom of packet)                       │
   │                                                                   │
   │   + 8. TEMPORAL NAVIGATION ANCHOR (novel):                        │
   │        "Partner Ram went to 'SBI near water tank' last Tuesday"   │
   │        ← mined from coordination transcripts; the landmark        │
   │           a SUCCESSFUL partner actually used for the              │
   │           nearest recent install                                  │
   └────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
Partner notification (packet visible PRE-click)
   │                      ◄── partner decides on CONTENT, not just geometry
   │                          "strongest clue first" rendering
   ▼
Partner decision:
   │
   ├─── ACCEPT ────┐      ◄── confident because they see the packet
   │               │
   │               ▼
   │         Technician dispatched (often no call needed — address
   │         resolution baked into the packet, not deferred to voice)
   │
   │
   └─── DECLINE ──────────────┐
                              ▼
   ┌──────── FEEDBACK LOOPS (novel, both sides) ────────────┐
   │                                                        │
   │  Partner side (Maanas's idea + decay fix):             │
   │    Hex reddens in partner's service map                │
   │    decline_weight = -1.0 × exp(-days/90)               │  ← DECAY
   │                        × min(1, n_decisions/10)        │    mandatory
   │    Partner sees their polygon evolve; future leads     │
   │    in that hex won't auto-notify this partner          │
   │                                                        │
   │  Customer side (structurally-different, not adversarial):│
   │    Map + ward boundary shown: "Is your home inside     │
   │    this area? If not, let's re-capture your GPS."      │
   │    ← fresh evidence, not "confirm your inputs"         │
   │                                                        │
   │  Optional: "Need human help?" → triggers CRE call      │
   └────────────────────────────────────────────────────────┘
                              │
                              ▼
              New cause code emits: ADDRESS_RESOLUTION_FAILURE
              (orthogonal to SPATIAL_FAILURE — B_spatial learns
               coordination fragility separately from spatial hardness)
```

**Core insight:** replace one fragile free-text string with **over-determined** multi-anchor structure. If any anchor fails, others still point to the right door. Partner sees content *before* deciding, not after. Decay on partner-side hex feedback prevents service-zone calcification (same class as Bayesian shrinkage K=30 prior-poisoning in the existing Promise Maker).

**The shift (Maanas's framing):** from *address intelligence* → *place intelligence*. The system sends a **verified, behaviorally grounded, partner-recognizable install location**, not an address string.

---

## How the two interlock

```
   Problem 1 (Point A)                  Problem 2 (Point B)
        │                                     │
        ▼                                     ▼
   Trust layer emits                    Packet builder consumes
   verified lat/lng ─────────►  Anchor #1 (verified lat/lng)
                                       + 7 other anchors
        │                                     │
        ▼                                     ▼
   GPS_TRUST_FAILURE                   ADDRESS_RESOLUTION_FAILURE
   cause code in H ◄────────────┬─────► cause code in H
                                │
                                ▼
                   B_spatial learns THREE failure modes
                   instead of one "spatial":
                   - gps capture failure (upstream fix)
                   - spatial hardness (partner not servicing area)
                   - coordination fragility (address hard to resolve)
                                │
                                ▼
                   Richer self-learning signal for PMBM
                   when Phase 5-6 lands
```

**Solving only one leaves the other's failure mode dominant:**
- Solve only Problem 1: cleaner GPS, still ambiguous text address → partner still calls to resolve gali/floor
- Solve only Problem 2: cleaner address, GPS still drifts → partner arrives at the wrong block despite perfect address text
- Solve both: the three parties (Wiom, partner, customer) hold the **same** location model, at the **same** quality, at every handoff

---

## Phased rollout (Donna's 8-week MVP sequence)

```
Week 1-2 ──── BACKEND ONLY (zero customer-app dependency)
              - Per-mobile jitter profile from jitter_mobile_v4.csv
              - 3-check trust layer (shadow mode — score only, no action)
              - Shiprocket NER packet in D&A OS
              - New cause codes: GPS_TRUST_FAILURE, ADDRESS_RESOLUTION_FAILURE
              ★ Measures the problem in production; prepares the substrate

Week 3-5 ──── THE SIGNATURE MOVE
              - Pre-commit re-capture loop (Genie → customer app)
              - Needs Wiom-app UX change + Satyam architectural sign-off
                on new Genie outbound contract (flagged as Open Question #1)
              ★ 8 of 10 interventions are PMBM-independent; this is the one
                that changes what Genie IS (structural, not parametric)

Week 5-7 ──── PARTNER-SIDE UX
              - Temporal navigation anchor in packet
              - Partner app renders "strongest clue first"
              - Gaming-detection sub-signal

Week 8+ ───── UX CLOSURE
              - Hex-reddening with time+evidence decay
              - Customer-side re-capture (structurally different, not adversarial)

Later ─────── PMBM INTEGRATION (when Phase 5/6 of Belief Model lands)
              - trust_score feeds Bayesian shrinkage α(i)
              - Cause codes drive B_spatial cause-coded retrain
              - Nothing from V0-V2 becomes obsolete
```

---

## Post-install validation loop (closes the learning loop on the confirmation flow)

Full detail in `solution_design.md` §14.5. Four signals that empirically validate whether upstream customer-confirmed landmarks actually functioned as navigation anchors in the field:

```
Install attempt closes (technician-at-door event)
     │
     ├──► Signal B — call transcript mining     ← Phase 1 (ships now, pipeline exists)
     │    Did partner reference a DIFFERENT landmark than the confirmed one?
     │    → packet_completeness_per_booking (negative-signal-only — can decrement,
     │                                        cannot increment)
     │
     ├──► Signal C — second-call escalation     ← Phase 1 (same pipeline)
     │    ≥2 calls on same install = compounding failure, lower noise floor
     │
     ├──► Signal A — partner field GPS trail    ← Phase 2 (gated on telemetry)
     │    Did partner pass through confirmed landmark radius?
     │    Distance from landmark to home reached?
     │    Stratified by partner-familiarity (use only non-local partners' trails)
     │    → landmark_quality_per_hex
     │
     └──► Signal D — time-to-door distribution  ← Phase 2 (same telemetry)
          Partner enters 500m radius → technician-at-door delta
          Population-level outcome: good confirmation shifts distribution LEFT

All four feed factorized estimate:
  install_outcome = partner_fixed_effect + landmark_fixed_effect + residual
  A landmark is "bad" only if fixed effect is negative AFTER controlling for partner

Stock architecture (Donna's non-negotiable):
  landmark_quality_per_hex stores (quality, confidence, last_observed) TRIPLET
  — NOT a single scalar. Prevents R-loop from eating B-loop.

Decay: 90-day half-life. K_landmark ≥ 10 observation floor before policy influence.
Measurement fast (24h); policy surfaces at CP 30-day cadence.
```

**Triple-purpose dividend** — each customer landmark-confirmation interaction now:
1. Validates Problem 1 (upstream trust gate)
2. Enriches Problem 2 packet (downstream partner context)
3. Feeds landmark quality scoring → improves **every future booking in that hex**

---

## The one-sentence version

**We add a feedback loop from Wiom back to the customer that doesn't exist today, we replace a fragile address string with over-determined multi-anchor structure so the partner knows the house before the call ever starts, and we close the learning loop with empirical post-install signals that validate whether the customer's confirmed landmarks actually worked.**

Everything else — the trust classifier, the NER, the what3words, the hex-reddening, even eventually PMBM — is scaffolding around those three moves.
