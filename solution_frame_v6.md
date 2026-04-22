# Solution Frame v6 — Location Signal (Two Confidences)

**Drafted:** 2026-04-22
**Predecessor:** `solution_frame_v5.md` (kept; v6 preserves v5's structural gains — phased rollout, payment mechanics, decay-on-every-loop, triplet state, named drains — and moves the Partner Integrity Channel out of the body into Appendix C so the frame stays answerable to the two problems Satyam posed)
**Primary audience:** Wiom functional leaders — design head, product head, and anyone seeing this problem for the first time.
**Companion files:** `master_story.md` + `master_story.csv` (the data backbone this frame cites throughout); two Gate 0 thinking contracts in `problem_statements/`.

---

## §1 — What this document is for

Two customer complaints land on Wiom's doorstep every week:

> *"Mujhe Wifi chahiye but Wiom mana kar raha hai."*
> (I want WiFi but Wiom is refusing me.)

> *"Mera connection aaj lagna tha, but koi lagane nahi aaya."*
> (My connection was supposed to be installed today, but nobody came.)

The data also surfaces a third corruption channel (partner-side booking-coord gaming). It is out of scope for this frame because the signal lives in per-partner state owned by other Wiom OSes (Q-OS / XS-OS / Enforcement OS), not inside Genie's gate geometry. The response is in Appendix C and will ship as a separate cross-OS workstream.

They sound like one problem. They are two. This document names what the solution is for, explains the mental model the build rests on, and lists the capabilities that implement it. Engineering mechanics — thresholds, decay formulas, write-contracts, API shapes — are the subject of the system spec that follows.

**Who wins what when this lands.**
- *Customer:* gets a promise that actually converts to an install. No refusal on a coord he didn't know was wrong. No no-show on a gali his partner never learned.
- *Partner:* gets a lead he can recognise in his own memory — landmark, gali, floor — and sees the consequences of his own accept/decline decisions evolve visibly over time.
- *Wiom:* gets a learning loop that tightens capture and serviceability with every install. The 25.7% drift, the 1.92 calls per pair, and the 77.5% within-ANC confusion are not permanent taxes — they are what the system pays today because nothing flows back.

---

## §2 — Primer for first-time readers

If this is your first exposure to the problem, read this section first. Everyone else can skip to §3.

### 2.1 — How Wiom works today, in one minute

A customer opens the Wiom app. The app asks him for his neighbourhood GPS (pre-filter on unserviceable cities), then asks him a second time for his home GPS — explicitly prompted to be at home. If an install or splitter exists within 25 metres of that home coord, Wiom collects Rs. 100 and commits: *"we will install at your home."* That is the promise. **Only after payment does the app ask for the text home address** — a free-text string, typed by the customer in one go. The address string is then passed downstream to a partner (CSP — Customer Service Partner) who accepts the lead, opens the address, often cannot parse it, calls the customer, negotiates landmark → gali → floor on voice, and sends a technician.

### 2.2 — Three parties, two decisions

Wiom's matchmaking system has exactly two decision points:

- **Point A — Wiom makes a promise.** Wiom decides whether to commit on the GPS the customer submitted. Get this wrong → customer is refused incorrectly (loss of demand) or gets a promise Wiom cannot keep (loss of trust).
- **Point B — the partner decides whether to install.** Partner accepts the lead, navigates to the home, attempts the install. Get this wrong → promised install never lands.

Three parties are present at every step: **Wiom, partner (CSP), customer.** Each holds a different fragment of ground truth. The customer knows where his home is. The partner knows where he can actually install. Wiom sits between them and today lets neither speak before the promise is made.

### 2.3 — The two problem statements (Satyam's framing)

- **Problem 1 — Location estimation.** What is the best way to take location from the customer? (Lives at Point A.)
- **Problem 2 — Address translation for CSP.** How do we ensure consistency of the location across all three parties? (Lives between Point A and Point B.)

### 2.4 — R&D concepts we'll invoke

Two models exist in Wiom's R&D but are not wired into production today. We will refer to them throughout:

- **BM1 — Promise Maker belief model.** Answers *"can we serve this booking?"* Built on a hex grid (roughly 100m cells), each partner's install history seeded as a Gaussian kernel on that grid (KDE), summed into a continuous serviceability field per partner. Bayesian shrinkage protects low-evidence hexes. Output: a confidence per booking.
- **BM2 — Allocation ranking model.** Answers *"among eligible partners, who ranks highest?"* A Graph Neural Network (GNN) learns from (partner, booking) decision edges — accept / decline / install / cancel — and outputs a probability per pair.

**In production today**, only one rule runs at the promise gate: *"is there any install or splitter within 25m of the booking coord?"* BM1 and BM2 are trained, validated on historical data, and idle. Activating them is part of what this build enables.

### 2.5 — Promise Maker as one organ inside a larger system

Promise Maker is the commitment engine inside Genie (Wiom's matchmaking brain). Think of Genie as the component that decides whether to make a promise, and to which partner to route it. The technical internals (how Genie separates belief from governance from external events) are in Appendix A — the body of this document only needs the idea that Genie has structured stocks for belief, governance, active exposure, and external events.

### 2.6 — Phased rollout — simpler logic first, models later

The frame describes the endpoint: two belief-model gates. But the belief models (BM1 KDE and BM2 GNN) are R&D assets that need production-wiring, calibration, and operational sign-off before they can be consulted at the gate. **The build ships in phases so business value lands before model activation completes.**

- **Phase 1 (Day 1):** Gate 2 runs on **polygon containment only** — a binary "is this booking inside any partner's serviceable polygon?" test. No KDE, no GNN. Tiers reduced to HIGH (inside a dense polygon with recent installs) / MID (edge) / LOW (outside). Simpler, shippable, safe.
- **Phase 2 (Post model-wiring):** BM1 KDE output contributes to the tier decision post-containment. Tier gradations become richer.
- **Phase 3 (Post GNN sign-off):** BM2 GNN feeds ranking among eligible partners.

Each phase's capabilities are tagged by phase in §12. **The user-facing mental model does not change across phases — only the sophistication of the tier computation inside Gate 2 grows.** (Appendix C describes a Phase 4 that adds cross-OS partner-integrity signal; it is orthogonal to the body of this frame and does not block Phases 1-3.)

---

## §3 — What the data establishes

Three evidentiary claims, each quoted from the master story, each load-bearing for the rest of this document. If any of these is wrong, the frame collapses — so they are stated before the frame is built. A fourth claim (partner-side booking-coord gaming) is noted at the end and handed off to Appendix C.

### Claim 1 — GPS jitter does not corrupt partner decisioning

**Evidence.** Install rate separates **43.81pp** across booking-partner distance deciles (D1 = 50.46% → D10 = 6.66%). When Wiom's R&D GNN scores the same bookings, install rate separates **56.77pp** (D1 = 3.72% → D10 = 60.49%) and address-not-clear dropdown concentration sharpens **2.5×**. Area-decline ladders monotonically on both — 19.64pp on distance, 23.43pp on GNN probability. *(Master story Part B.)*

**What this means.** Partners respond systematically to coordinate-based geometry, and the GNN — which prices partner willingness on top of raw geometry — wins every operational metric. **Partner-side decisioning is robust to customer-side GPS noise.** The deeper inference: *BM2 re-ranking has already done what ranking can do; the 40% address-not-clear remainder is not a routing problem — it is a capture problem.* The two workstreams (customer-side capture + activating the R&D belief models) are orthogonal; both can ship in parallel.

### Claim 2 — Partners prefer installing inside their dense, familiar zones

**Evidence.** Inside the partner's serviceable polygon (built from his own SE-weighted install/decline history), bookings install at **55.3%**; outside, at **38.6%** — a **16.7pp** gap. When the partner is in the locality but stuck on the gali, inside-polygon installs at **62.5%**; outside, at **25.4%** — the sharpest single-cell gap in the audit (+37.1pp). Chain engagement (landmark → gali → floor touched on any call) lifts install rate **+11.2pp** inside polygon. *(Master story Part C.D, C.E.)*

**What this means.** Serviceability is not a radius from any install — it is a shape the partner has drawn with his own decisions, and that shape governs whether he can recover from ambiguity. Outside his polygon, he doesn't know the gali grid and can't resolve on a call. A build that ignores this shape pays for it in every stuck call.

### Claim 3 — Address confusion is post-acceptance and rank-invariant

**Evidence.** **40.7% of partner-customer pairs** have a location-reason first call (36.2% address-not-clear + 4.5% partner-reached-can't-find), averaging **1.92 calls per pair**. Within address-not-clear calls, **77.5% still end in confusion** — 46% one-sided (partner confused, customer clear) + 31.5% mutual. At the transcript level, address-not-clear rate is **flat** across distance deciles (range 6.5pp) and GNN probability deciles (range 7.1pp). *(Master story Part C.B, C.C.)*

**What this means.** The pre-accept dropdown pattern was a decline-channel artifact — partners click "address not clear" as a polite exit on low-prob bookings. Once a partner accepts, every partner hits roughly the same address friction regardless of rank. **Address confusion is not solvable by better ranking — it is solvable by giving the partner structure that didn't exist in the capture.** The 46% one-sided case (customer clear, partner confused) is proof the structure already exists at the source. We just never asked for it in a form that travels forward.

### Claim 4 — Partner-side booking-coord gaming (deferred to Appendix C)

Within a single GNN probability decile, partners with >90% of their historical bookings' coords coincident with splitters install at **5.0%**, while partners with <10% splitter-share install at **35.8%** — a **30.8pp gap at the same GNN probability**. *(Master story Appendix lines 371-383.)* This gap is not customer-side capture noise; it is partners submitting booking coords that coincide with splitter infrastructure to pass the 25m gate. Gate 1 cannot see it (customer may be genuinely home); Gate 2 cannot see it (polygon contains the splitter). **The signal lives in per-partner state owned by Quality OS, Exit OS, and Enforcement OS, not in Genie's gate geometry.** Appendix C describes the cross-OS integrity channel that consumes that state; the body below stays focused on the two confidences.

### Together, these three claims shape the build

Claims 1 + 2 justify **activating the R&D belief models as-is** — they are robust to customer-side noise and they price the polygon effect the data surfaces. Claim 3 justifies **rebuilding customer-side capture**. Two workstreams, both parallel.

---

## §4 — The mental model: two confidences

This is the reframe. v3 laid out 31 capabilities in four groups. v4 collapsed them onto two belief models evaluated sequentially. v6 preserves that, with v5's structural upgrades (phased rollout, payment rewrite, decay-on-loops, triplet state) and moves partner-integrity into Appendix C as a cross-OS workstream on its own timeline.

### 4.1 — Why two confidences, not one

The system has to answer two structurally different questions before committing to a promise:

1. **Is the customer telling the truth about where his home is?** — A capture-quality question. Answered by the customer's own actions and the sensors we can observe.
2. **Can a partner actually serve this location?** — A serviceability question. Answered by every partner's decision history and his team's movement on the ground.

These are not the same question. Collapsing them into one belief — as today's 25m gate does — forces the system to accept bad input as long as it lands near infrastructure, and to reject good input as long as no partner has installed there yet.

### 4.2 — Why sequential, not a matrix

Serviceability should only be evaluated against a home location we believe is true. If we aren't sure the customer is at home, asking *"can a partner serve this?"* is asking the wrong question — the coord itself may not be where the customer lives.

### 4.3 — The picture

```
           ┌────────────────────────────┐
           │  GATE 1 — User Address     │
           │  Confidence                │
           │  "Is this really home?"    │
           └────────────┬───────────────┘
                        │
            HIGH ───────┤         LOW / unrecoverable
                        │              │
                        ▼              ▼
           ┌────────────────────────────┐
           │  GATE 2 — Serviceability   │      Reject (no payment)
           │  Confidence                │      Route to retry /
           │  "Can we serve here?"      │      expansion queue
           └────────────┬───────────────┘
                        │
            HIGH ───────┤─────── MID ──────── LOW
             │                    │            │
             ▼                    ▼            ▼
         Promise           Promise + MID    Reject
         + payment at      flag; auto-      (no payment)
         promise time      refund if
                           unbound in 48h
```

### 4.4 — The two confidence surfaces, summarised

| Surface | Question | Owned by | Lives in |
|---|---|---|---|
| User Address Confidence (new) | Is this really home? | Genie B (per-lead) | Genie |
| Serviceability Confidence (R&D, now activated) | Can we serve here? | Genie B (per-lead × partner) | Genie |

A third surface — partner integrity — is a per-partner state owned outside Genie and consumed through the existing shock-ledger contract. It is covered in Appendix C, not here.

---

## §5 — Belief Model 1: User Address Confidence (new)

### 5.1 — Why it has to exist

Today, Wiom commits on a single un-interrogated signal: the customer taps *"yes at home"* and Wiom takes one GPS fix. A one-witness commit system cannot distinguish a true *yes* from a false one. 25.7% of today's installs carry structural drift wider than GPS physics alone can produce. *(Master story Part D.A.)*

A second witness is mandatory. The only entity with ground truth about home-proximity is the customer herself.

### 5.2 — What it consumes (v0, rule-based; becomes learned once data flows)

The model is a function of four classes of signal:

1. **Customer's own structured knowledge** — ≥2 landmarks picked from a curated nearby list (Google Address Descriptors for round 1 + Wiom install-history anchors for round 2); gali name; floor number (required if install is at height); optional home-exterior photo/video.
2. **Sensor agreement** — continuous GPS stream during booking (not a single fix), per-mobile jitter profile, night-GPS ping cluster centre over subsequent days.
3. **Behavioural evidence** — did the customer actually go home? How many corrective-loop rounds did he pass through? Did he upload a video from the landmark to his door?
4. **Gaming-defence probes** — 20-25% of the landmark set are false landmarks; picking probes drops confidence.

**Every scoring artefact is stored as a triplet, not a scalar:** `(tier, evidence_count, last_observed)` per signal class, and per booking. A customer who picked 2 landmarks with 0 probes encountered is not the same booking as one who picked 2 landmarks and survived 3 probe rounds.

**Confidence v0 rule (indicative; tuned in engineering):**
- **HIGH** — ≥2 landmarks confirmed (no probe fails) + GPS jitter within the mobile's historical p80 + continuous GPS stream stable + evidence_count ≥ 3.
- **MID** — 1 landmark confirmed OR landmarks confirmed but with jitter >p80 OR night-GPS diverges OR evidence_count < 3.
- **LOW** — no landmark relates, or probe fails, or customer self-reports not-at-home.

### 5.3 — What happens at each tier

- **HIGH → pass to Gate 2.** No friction.
- **MID → remedy.** Surface Google Street View of the area: *"is this your street?"* If yes, ask for photo/video from the nearest landmark to the home. If the video resolves → promote to HIGH → pass. If not, route to a CRE / AI verification call (see §5.5 for ownership). If that resolves → promote to HIGH. If not → reject.
- **LOW → reject or route back.** If the customer insists he is at home but no landmark is relatable: *"please try again from home."* No payment captured at any LOW point.

### 5.4 — The customer is an active participant, not a passive signal

Today the customer taps *yes* and pays. In the new flow, the customer:

1. Picks landmarks (each pick is an action with information content).
2. Types gali and floor (structured chat, not free-text blob).
3. (If MID) Confirms Street View or shoots a short video from the landmark to the door.
4. Sees transparent feedback on his own submission — *why* rejected, *what next*.
5. Gets rewarded for accurate input — clean-history customers unlock reduced friction on future bookings.

### 5.5 — CRE / AI verification pathway — the named escape hatch

The "CRE or AI verification call" referenced above is not a hand-wave. It is a **Support Resolution OS (SR-OS)** handoff with a named queue, an SLA (10 minutes for first touch; 24h for resolution), and a volume ceiling (engineered to <5% of MID cohort — above which the queue must surface a Shock to CP for ops attention). Engineering mechanics ship in the spec.

---

## §6 — Belief Model 2: Serviceability Confidence (phased activation)

### 6.1 — What already exists

Wiom has spent the past year building a rich R&D stack. This build activates it in phases (see §2.6).

- **Partner serviceable polygons** — each partner has a polygon drawn from his own install/decline history. **This is what Phase 1 consults at the gate.**
- **Serviceability scoring model (BM1)** — a continuous per-partner serviceability field over geography. Joins the gate in Phase 2.
- **Allocation ranking model (BM2)** — ranks partners within the eligible pool. Joins in Phase 3.
- **Cause-coded closure outcomes** — install/decline/cancel tagged by type (SPATIAL / OPERATIONAL / GPS_TRUST / ADDRESS_RESOLUTION).

### 6.2 — What this build adds on top

Three enrichments that feed the activated models:

1. **Technician / team GPS trails** — where the partner's team physically moves each week. Treated as a hex-level visitation-density signal.
2. **Landmark-grounded serviceability** — each partner's polygon cross-indexed with landmarks from his install history.
3. **Governance on the confidence tier** — HIGH/MID/LOW with an action tree per tier.

### 6.3 — Containment is polygon-only; models enrich the tier

Two structurally separate steps:

- **Step 1 — Containment (binary):** is this booking inside any partner's serviceable polygon? Reads **polygons only**, in every phase. This is the eligibility gate. In Phase 1, this also determines the tier.
- **Step 2 — Tier decision (graded):** among eligible partners, what is the confidence? In Phase 1 this is simple polygon depth + freshness. In Phase 2+, the serviceability model and additional signals enrich the tier. **The models never decide eligibility — they only grade what is already eligible.**

This separation matters because it preserves phase independence — the gate ships in Phase 1 without needing the models to be production-ready.

### 6.4 — What the tier decision consumes (by phase)

- **Phase 1:** polygon depth (signed distance from edge), temporal freshness (recent installs in the hex weigh more).
- **Phase 2+:** above + serviceability model output, technician GPS trail density in the hex, landmark-partner install-history match.
- **Phase 3+:** above + allocation ranking model probability (used for ranking among eligible partners, not for tier gating).

### 6.5 — The three tiers + actions

- **HIGH** — inside a dense partner polygon, technician trails present, landmarks match install history. Partner is expected to install. **If he declines, he is shown upfront: the landmarks around this booking will be marked unserviceable for him and his polygon shrinks here.** He confirms with that consequence visible.
- **MID** — edge-of-polygon or landmarks-recognised-but-partner-not-dense. Ask-partner flow fires. Three options, each with a visible consequence shown to the partner **before** he confirms:
  - **Accept** → promise binds → dispatch. Polygon grows on successful install.
  - **Decline** → route to next eligible partner. **Polygon shrinks in this hex** (less steeply than a HIGH decline — a MID was an ask, not an assignment, so the signal is softer but not zero). Partner is shown the shrink consequence pre-confirm, same as the HIGH path.
  - **Verify first** → paid technician visit scheduled. On success: landmark-area opens for partner, success bonus, polygon grows. On verify-visit failure: polygon shrinks similar to a MID decline.
- **LOW** — reject, booking routed to the expansion-demand queue. **Exploration quota (B7) lets a bounded fraction through with explicit partner rotation** — rotation prevents "route-to-nearest" from reinforcing the same partner's blind spot. See §13 for rotation mechanics.

### 6.6 — The verify-visit journey, end-to-end

A MID booking where the partner picks "Verify first" is a two-sided learning transaction, not just a dispatch. The journey connects three capabilities (B8 pay, C7 visibility, Loops 1+2 decay) into one arc the partner experiences as *"Wiom paid me to learn my boundary, and the system remembered what I learned."*

1. **Wiom invokes.** Edge-polygon ask-partner flow presents the booking with confirmed landmarks + pre-confirm consequence: *"Accept a paid verify-visit. If address resolves and install binds, this hex opens for you and a bonus is credited. If it doesn't, polygon shrinks softly here and a consolation fee is credited."*
2. **Partner dispatches technician.** Same dispatch pipeline as install.
3. **Technician verifies on-ground.** Records outcome: reached-door / reached-landmark-not-door / could-not-reach. Landmarks actually used on-ground are logged.
4. **Wiom pays the partner.** Full bonus on reached-door + install-binds; consolation on could-not-reach. **Bonus magnitude < HIGH steady-state install throughput** (B8 damping) — verify-visits cannot outpay installs or the exploration quota gets gamed.
5. **Signal traces back, both directions.**
   - **Success** → Loop 2: polygon grows in this hex for this partner. Loop 1: landmark-confidence rises for the customer-confirmed anchors the technician actually used. Next booking in this hex routes to this partner as HIGH, not MID.
   - **Failure** → Loop 2: polygon shrinks softly (softer than a plain decline — he did the work). Loop 1: if a landmark was confirmed but not used on-ground, it loses confidence for this hex. Next booking in this hex routes to a different partner, or to the expansion queue.
6. **Partner sees the consequence in his app** (C7 + C9): which hexes opened, which closed, attributed to this verify-visit.

This is how the MID tier becomes a learning surface instead of a dispatch hand-wave: Wiom pays for the evidence; the evidence is recorded; the partner is shown what the evidence changed.

---

## §7 — Payment mechanics

The question: when does the fee get captured?

### 7.1 — The principle

**Payment is the intent-lock. Once taken, the customer has committed to Wiom; Wiom has committed to deliver — or to make the customer whole.** Abandonment at intent is unrecoverable; refunds are operationally priced.

### 7.2 — Why v4's rule was wrong

v4 said: *"payment fires on partner acceptance for MID serviceability."* The latency argument: partners respond on their own clock; verify-visits take 24-72h. A customer waiting in limbo between *"book now"* and *"payment captured"* is a customer who books with a competitor. The friction is compounded by the existing Wiom data showing 1.92 calls per pair and p90 = 4 *after* acceptance.

### 7.3 — The rule, by path

| Gate 1 (Address) | Gate 2 (Serviceability) | Payment | Post-payment behaviour |
|---|---|---|---|
| HIGH | HIGH | **At promise (immediate)** | Partner assigned; commit binds. |
| HIGH | MID | **At promise (immediate)** | MID flag set. Ask-partner / verify-visit fires. If no partner binds within **48h**, **auto-refund** + apology + expansion-queue entry. |
| HIGH | LOW | **No payment** | Route to expansion-demand queue; customer notified when coverage arrives. |
| MID-remediated to HIGH | any | As above | Rule applies post-promotion. |
| MID-unrecovered | — | **No payment** | Retry / CRE assist / reject. |
| LOW | — | **No payment** | Ask customer to try from home. |

### 7.4 — The auto-refund SLA is the contract

48h is a deliberate latency ceiling — long enough to allow ask-partner + verify-visit, short enough that a customer who doesn't get bound moves on rather than disappears silently. The auto-refund is unconditional, instant, and comes with an expansion-queue enrolment (the customer becomes first-in-line when coverage arrives).

### 7.5 — Remediated-HIGH × MID is treated differently

A booking that entered at Gate 1 MID and was remediated (Street View + video + CRE) to HIGH, then arrives at Gate 2 MID, carries **two compounding remediation risks**.

**Rule.** Remediated-HIGH × MID bookings require **mandatory verify-visit** (not optional). Verify-visit cost is waived for these bookings — Wiom absorbs the cost because the upstream remediation was already paid for in customer friction. This prevents the double-remediation compounding while preserving the verify-visit loop's integrity.

---

## §8 — Principles of build

**Gate 1 principles (User Address Confidence)**

**P1. Verify before committing.** The system does not take the fee on the customer's self-report alone; before commit, home-presence is corroborated by a second independent channel.

**P2. Capture is not verification.** Neither the 25m infrastructure gate nor the customer's *"yes"* counts as verification.

**P3. Ask the customer in a form that returns structure — textual and visual.**

**P4. Re-capture uses a different surface than initial capture.**

**Gate 2 principles (Serviceability Confidence)**

**P5. The address the partner sees is structured, and that structure is preserved end-to-end.**

**P6. PMBM-independence at containment.** The containment check reads polygons only; KDE enriches the tier decision post-containment, not the containment itself.

**P9. Confidence is field-level, not booking-level.**

**System-wide principles (both gates)**

**P7. Every signal consumed has a feedback channel back to its source.** A signal with no return path is a stock that can only degrade.

**P8. Cause-code fidelity.** Downstream failures tagged by type — GPS_TRUST / ADDRESS_RESOLUTION / SPATIAL / OPERATIONAL. Never lumped. Without this, no loop learns. (A fifth class, INTEGRITY, is reserved for Appendix C's cross-OS workstream and does not need to be wired in Phases 1-3.)

**P10. Scoring artifacts stay internal; only facts cross.** Trust scores, gaming scores, belief probabilities stay inside the OS that owns them. What crosses membranes are facts — verified lat/lng, confirmed landmark/gali/floor, photo URL, bounded state enums.

**P11. Quality vs Confidence separation.** Every scored stock stores a `(quality, confidence, last_observed)` triplet, not a scalar. A HIGH with thin evidence is not the same asset as a HIGH with thick evidence.

**P12. Decay on all stocks.** Every accumulating stock has a declared decay mechanism (time-weighted, evidence-weighted, or explicit recovery on clean evidence). A stock without decay is a leak.

---

## §9 — The system flow

Six stages plus a control pane.

```
            Customer inputs (GPS stream + landmarks + gali/floor + photo/video)
                                    │
                                    ▼
            ┌──────────────────────────────────────────────┐
            │  1. GATE 1 — User Address Confidence         │
            │     landmark relatability, jitter check,     │
            │     corrective loop, Street View, video      │
            └──────────────────────┬───────────────────────┘
                                   │  only HIGH passes
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  2. GATE 2 — Serviceability Confidence       │
            │     polygon containment (eligibility)        │
            │     → tier (phase-dependent enrichments)     │
            └──────────────────────┬───────────────────────┘
                                   │  tier determines path
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  3. GOVERNANCE — tier-based action           │
            │     promise + payment (HIGH or MID-with-SLA) │
            │     / ask-partner / verify-visit / reject    │
            └──────────────────────┬───────────────────────┘
                                   │  on bind
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  4. ACTIVE PROMISE EXPOSURE STOCK            │
            │     drains on install/cancel/48h-SLA-miss    │
            └──────────────────────┬───────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  5. PARTNER-FACING PACKET (BM2 ranking)      │
            │     framed in his install history            │
            └──────────────────────┬───────────────────────┘
                                   │                          ┌──────────────┐
                                   └────────────────────────► │ Install      │
                                                              │ outcome      │
                                                              └──────┬───────┘
                                   ┌◄────────────────────────────────┘
                                   │  on closure
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  6. IMMUTABLE HISTORY LOG                    │
            └──────────────────────────────────────────────┘

    ╔════════════════════════════════════════════════════════════════════════╗
    ║  CONTROL PANE — alongside all six stages                               ║
    ║  Night-GPS divergence · technician visit tracking · landmark-          ║
    ║  confidence accumulation · post-install validation · customer-side     ║
    ║  difficulty signals · cause-coded failure tagging                      ║
    ╚════════════════════════════════════════════════════════════════════════╝
```

Two structural fixes preserved from v5:
- **Stage 4 names its drain** (install / cancel / 48h-SLA-miss) — the active-promise stock is not a leak.
- **Stage 6 labelled "log not state"** — to prevent confusion with state stocks.

---

## §10 — Feedback loops (decay declared on every loop)

Loop shape (same for all six):

```
  source action → immutable memory → control-pane processing
                   → (model update OR real-time nudge) → visible to source
                   + declared decay
```

### Loop 1 — Install outcome → landmark-confidence per hex

**Flow.** Post-install, four signals validate customer-confirmed landmarks: call-transcript mining, second-call escalation, technician field GPS trail, time-to-door distribution. Feed landmark-confidence per hex.
**Stock:** `landmark_confidence = (quality, confidence, last_observed)` per (landmark, hex).
**Decay:** exponential time-decay (half-life engineered separately); explicit decrement when a confirmed landmark is not used on-call despite being in the packet.
**Visible to source:** customer whose landmark validated successfully sees it acknowledged in post-install notification ("*the partner reached your home using the Shiv Mandir landmark you confirmed*").

### Loop 2 — Partner accept/decline → polygon redraws

**Stock:** partner polygon per partner.
**Decay:** recent decisions weigh more (half-life per decision class); single declines in low-evidence hexes don't redline permanently.
**Visible to source:** red zones in partner app (C3), consequence shown at decline time (C4).

### Loop 3 — Partner accept/decline → BM2 ranking

**Stock:** GNN weights.
**Decay:** training-window recency; older edges down-weighted.
**Visible to source:** invisible (ranking is internal; P10). Acceptable because score stays inside.

### Loop 4 — Night-GPS divergence → per-mobile jitter profile

**Stock:** `jitter_profile = (quality, confidence, last_observed)` per mobile.
**Decay:** recovery on clean evidence — a mobile that produces consistent post-move night-GPS over N sessions recovers its profile. A single bad night does not stain forever.
**Visible to source:** customer notified real-time; partner notified real-time.

### Loop 5 — Technician GPS trails → serviceability enrichment

**Stock:** `team_visitation_density` per (partner, hex, week).
**Decay:** rolling 8-week window; older weeks drop out.
**Visible to source:** partner sees his own team's movement-derived polygon expansion in his app, with attribution ("*your team passed through 3 new hexes this week; those hexes are now serviceable for you*"). Closes the silent-membrane gap.

### Loop 6 — Customer outcome transparency → future input quality

**Not a stock — an information flow.** Every booking outcome carries honest messaging: HIGH/HIGH (fast path), HIGH/MID (wait + SLA + auto-refund), any LOW (explanation + next step), partner declined (expansion queue).
**Measurement:** repeat-customer User Address Confidence trend over 90-day rolling window. If the loop is closing, repeat-customer HIGH rate rises.
**Visible to source:** by construction — this IS the visibility to source.

### The six loops at a glance

| # | Source | Stock | Decay | Source sees it? |
|---|---|---|---|---|
| 1 | install outcome | landmark-confidence per hex (triplet) | time + explicit decrement | yes (post-install ack) |
| 2 | partner decisions | polygon | time + evidence | yes (red zones) |
| 3 | partner decisions | GNN weights | training-window recency | no (P10 — correct) |
| 4 | night-GPS | mobile jitter profile (triplet) | recovery on clean evidence | yes (notification) |
| 5 | technician GPS | visitation density per (partner, hex, week) | rolling 8-week window | yes |
| 6 | system outcome messaging | N/A (information flow) | N/A | yes (by construction) |

*(Appendix C adds a seventh loop for the cross-OS integrity channel. It operates outside Genie and does not block Phases 1-3.)*

---

## §11 — User involvement, named explicitly

Three shifts from today.

**1. The customer is the ground truth for home-proximity — not a sensor.**
**2. Every customer action raises or lowers confidence.**
**3. The customer gets honest, structured feedback at every outcome.**

The partner's symmetric role (active participant, not a scored object) is addressed via the cross-OS quality channel in Appendix C; inside this frame the partner sees polygon consequences pre-confirm (C4) and his own team's movement-derived polygon growth (C9).

---

## §12 — Capabilities: what to build, what to reuse

Four groups. Deltas marked **(v6)** for items rewired since v5 to account for integrity moving to the appendix.

### A. Gate 1 capabilities (User Address Confidence)

| # | Capability | N/R | Impact | Q |
|---|---|---|---|---|
| A1 | Continuous GPS stream during booking | N | Medium | Q3 |
| A2 | Nightly passive GPS pings | N | Medium | Q3 |
| A3 | Landmark picker + probes | N | Medium | Q3 |
| A4 | Gali + floor structured chat | N | Medium | Q3 |
| A5 | Home-exterior photo / short landmark-to-door video | N | Medium | Q3 |
| A6 | Two-round corrective loop (round 1 public landmarks → round 2 install-history anchors → on fail, hand off to A14) | N | Medium | Q3 |
| A7 | Fallback text capture | N | Medium | Q3 |
| A8 | Per-mobile jitter-handling path with recovery | N | Medium | Q4 |
| A9 | Google Street View pull | N | Medium | Q4 |
| A10 | NER parsing for A7 | N | Medium | Q4 |
| A11 | User Address Confidence Model v0 scorer storing triplet state | N | Quick | Q1 |
| A12 | Customer transparency UI | N | Quick | Q1 |
| A13 | Repeat-customer friction reduction | N | Medium | Q4 |
| A14 | SR-OS queue for MID remediation — named SLA, volume ceiling, CP shock on breach | N | Quick | Q1 |

### B. Gate 2 capabilities (Serviceability Confidence)

| # | Capability | N/R | Impact | Q |
|---|---|---|---|---|
| B1 | BM1 activation at the gate — polygon-only containment | R | Medium | Q4 |
| B2 | Promise / ask-partner / verify-visit / reject governance | N | Quick | Q1 |
| B3 | Active promise exposure stock with explicit drain on install/cancel/48h-SLA-miss | N | Medium | Q3 |
| B4 | Technician / team GPS ingestion | N | Medium | Q4 |
| B5 | Landmark-grounded serviceability | N | Medium | Q3 |
| B6 | BM2 activation | R | Medium | Q4 |
| B7 | Exploration quota with partner rotation | N | Medium | Q4 |
| B8 | Paid verify-visit flow with bonus < HIGH steady-state | N | Medium | Q3 |
| B9 | **(v6)** Verify-visit outcome capture — technician tag (reached-door / reached-landmark-not-door / could-not-reach) + landmarks-actually-used log; feeds Loops 1 + 2 per §6.6 | N | Medium | Q3 |
| B10 | **(v6)** Remediated-HIGH × MID path tagging + waived-cost accounting (§7.5) — flow flag + finance pathway absorbing verify-visit cost upstream of partner payout | N | Medium | Q3 |

### C. Partner-facing capabilities (Packet + Feedback)

| # | Capability | N/R | Impact | Q |
|---|---|---|---|---|
| C1 | Structured partner notification (landmark + gali + floor, framed in his install history) | N | Quick | Q1 |
| C2 | Partner's own serviceable-area map (live) | R | Quick | Q1 |
| C3 | Decline-zones (with decay + time weighting) | N | Quick | Q2 |
| C4 | Decline consequence shown pre-confirm | N | Quick | Q1 |
| C5 | Edge-polygon ask-partner flow | N | Quick | Q1 |
| C6 | Street View at navigate-time | N | Quick | Q2 |
| C7 | Verify-visit reward + polygon-growth visibility | N | Quick | Q2 |
| C8 | On-ground navigation assist | N | Quick | Q2 |
| C9 | Technician team-trail visibility to partner — closes Loop 5's source-awareness gap | N | Quick | Q2 |

### D. Feedback / control-pane capabilities

| # | Capability | N/R | Impact | Q |
|---|---|---|---|---|
| D1 | Night-GPS divergence detector | N | Medium | Q4 |
| D2 | Technician visit tracking → SLA nudge | N | Quick | Q4 |
| D3 | Install outcome → cause-coded training loop | N | Medium | Q4 |
| D4 | Landmark-confidence accumulation with triplet state + decay | N | Medium | Q4 |
| D5 | Immutable history log (H) | N | Medium | Q3 |
| D6 | Customer-side difficulty signal monitor | N | Medium | Q4 |
| D7 | Post-install landmark validation (4 signals) | N | Medium | Q4 |
| D8 | Cause-code taxonomy (GPS_TRUST / ADDRESS_RESOLUTION / SPATIAL / OPERATIONAL) **(v6)** — INTEGRITY class deferred to Appendix C | N | Quick | Q1 |
| D9 | Customer outcome transparency loop | N | Quick | Q1 |

**Counts.** A = 14, B = 10, C = 9, D = 9. Total **42** capabilities in the body. **R (reuse) = 3** (B1, B6, C2). **N (new) = 39**.

*(Appendix C adds 8 cross-OS integrity capabilities — separate rollout, separate sign-off path.)*

---

## §13 — Prioritisation

|  | Do it now | Do it in next 1 month |
|---|---|---|
| **Quick impact** | Q1 | Q2 |
| **Medium-term impact** | Q3 | Q4 |

**Q1 — Now, Quick impact.** B2 governance gate (Phase 1, polygon-only) · C1 structured notification · C2 serviceable-area map · C4 decline consequence · C5 ask-partner flow · A11 User Address Confidence v0 scorer · A12 customer transparency UI · A14 SR-OS queue · D8 cause-code taxonomy · D9 customer outcome transparency.

**Q2 — Next month, Quick impact.** C3 decline-zones · C6 Street View partner-side · C7 verify-visit reward · C8 on-ground assist · C9 team-trail visibility to partner.

**Q3 — Now, Medium-term.** A1-A7 capture substrate · B3 active promise stock (with drain) · B5 landmark-grounded serviceability · B8 verify-visit flow · B9 verify-visit outcome capture · B10 remediated-HIGH × MID path tagging + cost accounting · D5 immutable history.

**Q4 — Next month, Medium-term.** A8 jitter-handling (with recovery) · A9 Street View customer-side · A10 NER · A13 repeat-customer friction · B1 serviceability model activation (Phase 2) · B4 technician GPS · B6 allocation ranking model activation (Phase 3) · B7 exploration quota (with rotation) · D1-D4 + D6-D7 feedback plumbing.

**Reading the matrix.** **Phase 1 is Q1 + Q3-capture** — polygon-only Gate 2 + capture substrate. Ships business value without waiting for model activation. Phase 2 (serviceability model) and Phase 3 (allocation ranking) layer on. Phase 4 (integrity channel, Appendix C) runs on its own cross-OS timeline.

---

## §14 — How we'll know it worked

Nine signals grouped by claim + one gameability control.

**Gate 1 is calibrated (address confidence works):**
- Structural drift rate > 155m: **25.7% → <5%** on installed cohort.
- ≥2 landmark confirmations before payment: **>90%**.

**Gate 2 is calibrated (serviceability works):**
- Inside-polygon install rate: **55.3% → >65%**.
- MID ask-partner acceptance rate: **>40%**, with verify-visit success rate **>60%**.
- MID → HIGH hex graduation rate over 90 days: target baseline TBD Sprint 1.

**Downstream friction drops:**
- Calls per pair: **1.92 → <1.3**.
- Gali-stuck call rate: **7.4% → <2%**.

**Gameability control:**
- **Promise-to-install conversion at held promise volume**: this is the primary NUT-linked target. Tightening the gate to reject everyone drops the other metrics trivially; this one does not, because volume is held. If held-volume conversion rises, the build landed.
- **Expansion-queue → coverage graduation rate**: LOW bookings routed to the expansion queue cannot be a graveyard. Measured monthly.

*(The 30.8pp same-prob splitter-share gap is an Appendix C target with its own measurement on the cross-OS channel.)*

Lag: most metrics 2-4 weeks. Leading operational signals — verification-completion, ask-partner acceptance — observable in hours.

---

## §15 — Open questions

1. Exploration quota rate + rotation mechanics (B7).
2. Verify-visit pricing and bonus magnitude — must be < HIGH steady-state throughput value (damping).
3. Repeat-customer friction reduction — trust decay intervals.
4. User Address Confidence v0 thresholds — exact rule for HIGH/MID/LOW.
5. Technician GPS ingestion cadence + privacy model.
6. Customer transparency copy.
7. MID serviceability ops throughput ceiling.
8. Remediated-HIGH × MID verify-visit waiver — ops cost absorption mechanism.

*(Integrity-channel open questions live in Appendix C.)*

---

## §16 — Why fixing only one side leaves installs broken

- **Only Gate 1 →** cleaner GPS; partner still sees unstructured blob; serviceability false-negatives continue because R&D models aren't activated.
- **Only Gate 2 →** BM1/BM2 activated; but address is still noisy; partner still rebuilds the chain on every call.
- **Both →** three parties hold the same location model at the same quality at every handoff; voice call becomes confirmation, not discovery.

The two workstreams share the capture substrate. Fixing them in parallel is cheaper than fixing them serially. *(The partner-side gaming channel in Appendix C is a third, orthogonal workstream owned cross-OS; it does not substitute for Gates 1 and 2 and they do not substitute for it.)*

---

## §17 — What changes from v5 to v6

For readers who know v5:

1. **Integrity channel moved from §6a to Appendix C.** v5's body named a third confidence surface and a phase-4 rollout inside the main frame. v6 keeps that work — unchanged in content — and relocates it to Appendix C so the body stays answerable to the two problem statements Satyam posed.
2. **Claim 4 retained but demoted.** The 30.8pp same-prob splitter-share finding remains in §3 as a one-paragraph acknowledgment; full mechanism and response in Appendix C.
3. **§4 reverted to "two confidences"** (not "two confidences + integrity shock channel"). The three-surface summary table drops the Partner Integrity row; that row lives in Appendix C's summary.
4. **§9 control pane** no longer annotates the integrity cross-connection; same control pane content.
5. **§10 drops Loop 7** from the main loop table; a note points at Appendix C.
6. **§11 drops the v5 partner-dashboard paragraph** from the body; same content in Appendix C.
7. **§12 drops Group E** (8 cross-OS capabilities); they appear in Appendix C with the same IDs.
8. **§13 phase tagging drops Phase 4** from the body quadrants; Appendix C carries its own Phase 4 rollout.
9. **§14 drops integrity metrics and recidivism targets** from the body; they live in Appendix C.
10. **§16 reframed** from "three workstreams" back to "two workstreams" in the body, with the third acknowledged as cross-OS.
11. **Principles P7-P12 preserved verbatim** from v5. They remain load-bearing for the body. P8 (cause-code fidelity) notes the INTEGRITY class as reserved-for-Appendix-C.
12. **Appendix A (Genie internals) preserved verbatim.** The three IC-COMMIT bilateral contracts referenced there are now declared in Appendix C's scope, not in Appendix A's.
13. **Appendix C added** — Partner Integrity Channel, with the v5 §6a content, the v5 Group E capabilities, the v5 §10 Loop 7, the v5 §14 integrity metrics, and the v5 §15 integrity open questions, re-organised as a self-contained cross-OS workstream.

---

## Appendix A — Genie internals (technical note for system-spec readers)

This section is for readers designing the system spec. Functional leaders can skip.

Promise Maker's internal architecture (per Genie V5 Constitution) has six stocks:

- **B (Belief)** — per-lead spatial and operational beliefs; what the system thinks is true. User Address Confidence and Serviceability Confidence both live here.
- **R (Governor)** — thresholds that turn belief into COMMIT / DEFER / REJECT. Dimension-agnostic; holds no behavioural rules.
- **E (Active Exposure)** — stock of live commitments; the active-promise-exposure stock referenced in §9 Stage 4.
- **S (Shock Ledger)** — events from outside Genie that demand re-evaluation. The Partner Integrity channel (Appendix C) enters Genie here.
- **H (History)** — immutable log of closures, for audit and training. §9 Stage 6.
- **CP (Control Pane)** — orchestrates the other five stocks.

**Load-bearing constraints:** B scores a lead (never decides). R decides (never holds domain rules). S is external-only (never populated by Genie internally). Facts cross membranes; scores stay inside.

At the gate, G queries S at the existing `integrity_block` and `execution_path_available` gate points (V5 Spec §5.5.1). When S is empty (Phases 1-3), gate behaviour is exactly as described in §6.

---

## Appendix B — Seeds for the system architect document

- Cause-code taxonomy (GPS_TRUST / ADDRESS_RESOLUTION / SPATIAL / OPERATIONAL) — full definitions.
- Decay mechanics per stock (half-lives, evidence weighting, recovery conditions).
- Scoring-artifacts-internal rule — authoritative list of what crosses which membrane.
- Text-address reverse-lookup storage.
- Layered containment logic (partner polygon → city envelope → truly sparse) — polygon-only at containment; model outputs downstream of containment.
- Temporal navigation anchor mining.
- Street View coverage scoping for Indian residential bookings.
- User Address Confidence Model v0 rules → v1+ learned model migration path.
- Verify-visit paid-visit pricing and success-bonus mechanics — bonus magnitude must be < HIGH steady-state install throughput to prevent the exploration-quota-laundering failure mode.
- Exploration quota governor design with partner rotation.
- Epistemic-uncertainty treatment on B's partner-side features — formal treatment of sparse-evidence down-weighting.
- Remediated-HIGH × MID verify-visit waiver accounting — cost absorption pathway.
- Phase gating criteria — what operational evidence must land before Phase 2 and Phase 3 activate.

---

## Appendix C — Partner Integrity Channel (cross-OS workstream)

This appendix is self-contained. It is scoped outside the body of this frame because the signal it carries lives in per-partner state owned by Quality OS (Q-OS), Exit Enforcement OS (XS-OS), and Enforcement OS — not inside Genie's gate geometry. It ships on its own cross-OS timeline (Phase 4) and has no hard dependency on the body's Phases 1-3. The body's Phases 1-3 have no hard dependency on it either.

### C.1 — The problem

Within one allocation-model probability decile, partners with >90% splitter-share install at **5.0%** vs <10% splitter-share partners at **35.8%** — a **30.8pp gap at the same modelled probability**. *(Master story Appendix lines 371-383.)* This is partners gaming the allocation by submitting bookings whose coords coincide with splitters. Gate 1 cannot see it (customer may be genuinely home). Gate 2 cannot see it (polygon contains the splitter by construction). **The signal lives in per-partner history, not per-booking geometry.**

### C.2 — Why integrity is consumed, not computed inside Genie

Wiom's architecture separates where information lives from where it is used. Partner integrity is a **per-partner state** owned by the OS that observes it:

- Q-OS sees install integrity, rework patterns, complaint patterns.
- XS-OS sees terminal-integrity lifecycle states.
- Enforcement OS sees event-time gaming patterns (fast detection).

If Genie synthesised its own trust score, it would duplicate logic these OSes already own and create drift between three different views of the same partner. **The correct pattern is to consume integrity state from these OSes and act on it at the gate — through the existing integrity-event contract Wiom OSes use to talk to each other.**

### C.3 — Three source OSes, two clocks

| Source OS | Signal class | Clock |
|---|---|---|
| **Enforcement OS** | Event-time gaming (splitter-share anomaly, coord-cluster on a partner's bookings, first-offense patterns detected at booking ingestion) | **Fast** — fires at gate same day |
| **Q-OS** | Chronic quality drift (install-integrity decline, rework, complaint pattern, decline-to-install ratio in low-evidence hexes) | **Slow** — pattern-window (days) |
| **XS-OS** | Terminal-integrity lifecycle states | **Slow** — exit-lifecycle pace |

**Two clocks, one gate.** Fast-path catches first-offense gaming at promise time (critical — without it, new gaming partners run undetected for a full pattern window). Slow-path catches chronic drift.

### C.4 — What crosses the membrane

**Facts, not scores.** What crosses is a bounded state (e.g., "this partner is suspended" or "this partner is in a cooldown") plus an event ID. What does **not** cross is a continuous `partner_trust_score`. A continuous score would force Genie to recalibrate every time the originating OS recalibrates — creating tight coupling and a Goodhart trap. The originating OS owns the score, the evidence, and the resolution. Genie reads state and acts.

### C.5 — Damping and failure modes to engineer

- **Recidivism on auto-clear** → replace auto-clear with a **post-clear probation** window before the partner is fully re-admitted.
- **Supply thinning triggers gate relaxation** → the exploration quota (B7) and polygon-shrink mechanisms must not re-admit flagged partners; flagged status is not rotation-eligible.
- **Signal starvation during recovery** → low-lead partners emit sparse quality signal, so sparse-evidence partners carry **epistemic-uncertainty** in Gate 2 scoring — sparse evidence cannot default to "trusted."
- **State-machine drift** between Genie and the originating OS → the bilateral contract specifies TTL, resolution-signal SLA, and cooldown-ownership explicitly.
- **Graduated severity** — a partner flagged twice in a rolling window gets a longer cooldown than the first flag.

### C.6 — The system-goal flip

Synthesising partner trust inside Genie would set Genie's goal as *"predict and route around bad partners"* — a matching-engine goal. Routing trust through Q-OS / XS-OS / Enforcement OS flips the goal: **"surface partner integrity as a first-class Wiom property; matching simply consumes it."** Gaming becomes a constitutional problem, not a Genie problem. Genie gets smaller, not bigger. The partner sees one trust signal on one dashboard (via Data Access OS), in Q-OS's own language, with a self-correction window before any consequence fires.

### C.7 — Capabilities (Group E)

| # | Capability | N/R | Impact | Q |
|---|---|---|---|---|
| E1 | Enforcement OS → Genie fast-path integrity-event contract | N | Quick | Q1 |
| E2 | Q-OS → Genie slow-path quality-state contract | N | Medium | Q3 |
| E3 | XS-OS → Genie terminal-integrity contract | N | Medium | Q3 |
| E4 | Booking-coord anomaly detector (splitter-share, coord-cluster) — lives in Enforcement OS, not Genie | N | Medium | Q3 |
| E5 | Epistemic-uncertainty treatment for sparse-evidence partners in Gate 2 scoring | N | Medium | Q4 |
| E6 | Partner integrity dashboard (via Data Access OS) — partner sees quality state in Q-OS's own language with a self-correction window | N | Quick | Q2 |
| E7 | Post-clear probation mechanics in Q-OS | N | Medium | Q4 |
| E8 | Bilateral contract terms — TTL, resolution-SLA, cooldown-ownership declarations | N | Quick | Q1 |

### C.8 — Loop 7 — Integrity shocks → partner corrections

**Stock:** external to Genie. Q-OS owns QUAL_STATE; XS-OS owns EXIT_STATE + risk overlay; Enforcement OS owns FPV ledger.
**Decay:** owned by the originating OS (Q-OS cooldown via IC-INT-10a; XS-OS lifecycle transitions; Enforcement FPV TTLs).
**Visible to source:** partner sees quality state on his own dashboard via Data Access OS, in Q-OS's language, before any consequence fires. This is the load-bearing property: **the partner learns why before the gate closes.**

### C.9 — Metrics

- 30.8pp same-prob splitter-share gap: **closes to <10pp within 6 months of E4 deployment**.
- Recidivism on auto-clear: **<15%** (oscillation safeguard).
- Fraction of bookings where Genie queried S and received a shock: visible and audited in H.

### C.10 — Open questions

- Fast-path FPV detector design (E4) — ownership, feature set, false-positive rate tolerance.
- Bilateral shock-commit contract details (E1, E2, E3, E8) — TTL, resolution SLA, cooldown ownership, graduated severity parameters.
- Epistemic-uncertainty floor shape (E5) — how B down-weights sparse-evidence partners.

### C.11 — Bilateral shock-commit contracts

The Partner Integrity Channel enters Genie through **IC-INT-10 / IC-INT-10a** — the Shock Ledger Intake Contract, already specified. The missing engineering work is three bilateral shock-commit contracts:

- **IC-COMMIT-ENF-01** — Enforcement OS → Genie S (fast-path FPV class).
- **IC-COMMIT-QOS-01** — Q-OS → Genie S (slow-path chronic).
- **IC-COMMIT-EXIT-01** — XS-OS → Genie S (terminal integrity).

Each contract specifies: payload schema, TTL, resolution-signal SLA, cooldown ownership declaration, graduated severity semantics.

Q-OS's post-clear probation lives in its **T-ENF-3** mechanism (see Q-OS v1.10). XS-OS's R0/R1/R2 risk overlay on EXIT_STATE S0→S6 provides the terminal-integrity payload. Enforcement OS's FPV ledger provides the fast-path payload.

### C.12 — Cause-code extension

The body's cause-code taxonomy (D8) is GPS_TRUST / ADDRESS_RESOLUTION / SPATIAL / OPERATIONAL. This appendix adds a fifth class — **INTEGRITY** — that fires when a closure's proximate cause traces to a partner-integrity breach rather than a geometric or operational failure. The extension is additive; it does not alter Phase 1-3 code paths.
