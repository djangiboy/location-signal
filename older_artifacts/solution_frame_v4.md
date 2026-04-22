# Solution Frame v4 — Location Signal

**Drafted:** 2026-04-21
**Predecessor:** `solution_frame_v3.md` (kept; v4 rebuilds the mental model, preserves the flow)
**Primary audience:** Wiom functional leaders — design head, product head, and anyone seeing this problem for the first time.
**Companion files:** `master_story.md` + `master_story.csv` (the data backbone this frame cites throughout); two Gate 0 thinking contracts in `problem_statements/`.

---

## §1 — What this document is for

Two customer complaints land on Wiom's doorstep every week:

> *"Mujhe Wifi chahiye but Wiom mana kar raha hai."*
> (I want WiFi but Wiom is refusing me.)

> *"Mera connection aaj lagna tha, but koi lagane nahi aaya."*
> (My connection was supposed to be installed today, but nobody came.)

They sound like one problem. They are two. This document names what the solution is for, explains the mental model the build rests on, and lists the capabilities that implement it. Engineering mechanics — thresholds, decay formulas, write-contracts, API shapes — are the subject of the system spec that follows.

**Who wins what when this lands.**
- *Customer:* gets a promise that actually converts to an install. No refusal on a coord he didn't know was wrong. No no-show on a gali his partner never learned.
- *Partner:* gets a lead he can recognise in his own memory — landmark, gali, floor — and sees the consequences of his own accept/decline decisions evolve visibly over time.
- *Wiom:* gets a learning loop that tightens capture and serviceability with every install. The 25.7% drift, the 1.92 calls per pair, the 77.5% within-ANC confusion are not permanent taxes — they are what the system pays today because nothing flows back.

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

---

## §3 — What the data establishes

Three evidentiary claims, each quoted from the master story, each load-bearing for the rest of this document. If any of these is wrong, the frame collapses — so they are stated before the frame is built.

### Claim 1 — GPS jitter does not corrupt partner decisioning

**Evidence.** Install rate separates **43.81pp** across booking-partner distance deciles (D1 = 50.46% → D10 = 6.66%). When Wiom's R&D GNN scores the same bookings, install rate separates **56.77pp** (D1 = 3.72% → D10 = 60.49%) and address-not-clear dropdown concentration sharpens **2.5×**. Area-decline ladders monotonically on both — 19.64pp on distance, 23.43pp on GNN probability. *(Master story Part B.)*

**What this means.** Partners respond systematically to coordinate-based geometry, and the GNN — which prices partner willingness on top of raw geometry — wins every operational metric. **Partner-side decisioning is robust to customer-side GPS noise.** The two workstreams are orthogonal: cleaner captures will sharpen model precision, but the belief models can be activated without waiting for capture to be clean.

### Claim 2 — Partners prefer installing inside their dense, familiar zones

**Evidence.** Inside the partner's serviceable polygon (built from his own SE-weighted install/decline history), bookings install at **55.3%**; outside, at **38.6%** — a **16.7pp** gap. When the partner is in the locality but stuck on the gali, inside-polygon installs at **62.5%**; outside, at **25.4%** — the sharpest single-cell gap in the audit (+37.1pp). Chain engagement (landmark → gali → floor touched on any call) lifts install rate **+11.2pp** inside polygon. *(Master story Part C.D, C.E.)*

**What this means.** Serviceability is not a radius from any install — it is a shape the partner has drawn with his own decisions, and that shape governs whether he can recover from ambiguity. Outside his polygon, he doesn't know the gali grid and can't resolve on a call. A build that ignores this shape pays for it in every stuck call.

### Claim 3 — Address confusion is post-acceptance and rank-invariant

**Evidence.** **40.7% of partner-customer pairs** have a location-reason first call (36.2% address-not-clear + 4.5% partner-reached-can't-find), averaging **1.92 calls per pair**. Within address-not-clear calls, **77.5% still end in confusion** — 46% one-sided (partner confused, customer clear) + 31.5% mutual. At the transcript level, address-not-clear rate is **flat** across distance deciles (range 6.5pp) and GNN probability deciles (range 7.1pp). *(Master story Part C.B, C.C.)*

**What this means.** The pre-accept dropdown pattern was a decline-channel artifact — partners click "address not clear" as a polite exit on low-prob bookings. Once a partner accepts, every partner hits roughly the same address friction regardless of rank. **Address confusion is not solvable by better ranking — it is solvable by giving the partner structure that didn't exist in the capture.** The 46% one-sided case (customer clear, partner confused) is proof the structure already exists at the source. We just never asked for it in a form that travels forward.

### Together, these three claims shape the build

Claim 1 + Claim 2 justify **activating the R&D belief models as-is** — they are robust to customer-side noise and they price the polygon effect the data surfaces. Claim 3 justifies **rebuilding customer-side capture** — the downstream call cannot recover what was never captured upstream. The two workstreams are parallel, not sequential.

---

## §4 — The mental model: two confidences, evaluated in order

This is the reframe. v3 laid out 31 capabilities in four groups and a six-stage flow. v4 keeps the flow but replaces the inventory with a simpler spine: **two belief models, evaluated sequentially.**

### 4.1 — Why two, not one

The system has to answer two structurally different questions before committing to a promise:

1. **Is the customer telling the truth about where his home is?** — A capture-quality question. Answered by the customer's own actions and the sensors we can observe.
2. **Can a partner actually serve this location?** — A serviceability question. Answered by every partner's decision history and his team's movement on the ground.

These are not the same question. The first is about *input trust*. The second is about *downstream feasibility*. Collapsing them into one belief — as today's 25m gate does — forces the system to accept bad input as long as it lands near infrastructure, and to reject good input as long as no partner has installed there yet.

### 4.2 — Why sequential, not a matrix

The v3 frame flirted with a 3×3 governance matrix (address confidence × serviceability confidence). **That framing is wrong.** Serviceability should only be evaluated against a home location we believe is true. If we aren't sure the customer is at home, asking *"can a partner serve this?"* is asking the wrong question — the coord itself may not be where the customer lives.

So the two confidences sit in order:

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
         Promise           Ask-partner /    Reject
         (payment)         verify-visit     (no payment)
                           (payment on
                            acceptance)
```

Each gate outputs **HIGH / MID / LOW**. The tiering is the same at both gates; the action conditioned on the tier is different. Payment is the commitment and only fires when the system is willing to keep the promise.

### 4.3 — The two models, named

| Belief Model | Question | Inputs | Built from | Output |
|---|---|---|---|---|
| **User Address Confidence Model** (new) | Is this really home? | ≥2 customer-confirmed landmarks, gali, floor, continuous GPS stream during booking, per-mobile jitter profile, night-GPS ping cluster, Street View agreement, photo/video | **New — v0 is a rule-based scoring; v1+ becomes a learned model once data flows** | HIGH / MID / LOW tier |
| **Serviceability Confidence Model** (already in R&D) | Can we serve here? | Partner polygon containment, GNN probability, partner install density around confirmed landmarks, partner team/technician GPS trails, landmark-grounded serviceability | **Existing** — BM1 (KDE + hex + Bayesian shrinkage) + BM2 (GNN) + new enrichment from technician GPS | HIGH / MID / LOW tier |

The User Address Confidence Model is the load-bearing new artefact of this build. The Serviceability Confidence Model is already built in R&D — the build activates it, enriches it with new signals (technician GPS, landmark grounding), and exposes it through a governance layer.

---

## §5 — Belief Model 1: User Address Confidence (new)

### 5.1 — Why it has to exist

Today, Wiom commits on a single un-interrogated signal: the customer taps *"yes at home"* and Wiom takes one GPS fix. A one-witness commit system cannot distinguish a true *yes* from a false one. 25.7% of today's installs carry structural drift wider than GPS physics alone can produce — because the one witness is never questioned. *(Master story Part D.A.)*

A second witness is mandatory. The only entity with ground truth about home-proximity is the customer herself — she knows whether she is standing in her kitchen or at a kirana three blocks away. We just have to ask her in a form that returns structure.

### 5.2 — What it consumes (v0, rule-based)

The model is a function of four classes of signal:

1. **Customer's own structured knowledge** — ≥2 landmarks picked from a curated nearby list (Google Address Descriptors for round 1 + Wiom install-history anchors for round 2); gali name; floor number (required if install is at height); optional home-exterior photo/video.
2. **Sensor agreement** — continuous GPS stream during the booking session (not a single fix), per-mobile jitter profile (does this phone drift >20m indoors?), night-GPS ping cluster centre (does it match the booking coord over the following days?).
3. **Behavioural evidence** — did the customer actually go home after being prompted, or did he insist from near-home? How many rounds of corrective loop did he pass through? Did he upload a video from the landmark to his door?
4. **Gaming-defence probes** — 20-25% of the landmark set are false landmarks that shouldn't exist near a real home. Picking probes drops confidence.

**Confidence v0 rule (indicative; tuned in engineering):**
- **HIGH** — ≥2 landmarks confirmed (no probe fails) + GPS jitter within the mobile's historical p80 + continuous GPS stream stable during booking.
- **MID** — 1 landmark confirmed OR landmarks confirmed but with jitter >p80 OR night-GPS (post-booking) diverges from the submitted coord.
- **LOW** — no landmark relates, or probe fails, or customer self-reports not-at-home.

### 5.3 — What happens at each tier

- **HIGH → pass to Gate 2.** No friction. The customer's structured input becomes the packet.
- **MID → remedy.** Surface Google Street View of the area: *"is this your street?"* If yes, ask for photo/video from the nearest landmark to the home (treat it like a Reel). If the video resolves the ambiguity → promote to HIGH → pass. If not, route to a CRE / AI verification call. If that resolves → promote to HIGH. If not → reject.
- **LOW → reject upfront or route back.** If the customer insists he is at home but no landmark is relatable: *"please try again from home."* If he is genuinely home but the area is underserved, he falls into the LOW serviceability branch at Gate 2 — different path, different handling. No payment captured at any LOW point.

### 5.4 — The customer is an active participant, not a passive signal

This is a deliberate redesign of the customer's role. Today the customer taps *yes* and pays. In the new flow, the customer:

1. **Picks landmarks.** Each pick is an action with information content.
2. **Types gali and floor.** Structured chat, not a free-text blob.
3. **(If MID) Confirms Street View or shoots a short video from the landmark to the door.** An active gesture that raises confidence.
4. **Sees transparent feedback on his own submission.** If rejected, he is told *why* — *"we couldn't relate the landmarks you picked to this area. Please try again from home, or talk to our team."*
5. **Gets rewarded for accurate input.** Customers whose captures survive to successful install unlock reduced friction on future bookings (priority slot, skipped re-verification).

Every customer action is both a signal (feeds the model) and a contract (his input is the basis on which Wiom commits).

---

## §6 — Belief Model 2: Serviceability Confidence (already in R&D, now activated)

### 6.1 — What already exists

Wiom has spent the past year building a rich R&D stack. **These are not things this build invents — they are things this build finally consults at the gate.**

- **Partner serviceable polygons** — each partner has a polygon drawn from his own SE-weighted install/decline history (stored in `partner_cluster_boundaries.h5`). Installs grow the polygon; declines shrink it. Already built, snapshotted monthly.
- **BM1 — KDE serviceability fields** — Gaussian kernels on a hex grid, multi-resolution, with Bayesian shrinkage to prevent low-evidence hexes from driving decisions.
- **BM2 — GNN allocation ranking** — learns from partner-booking decision edges.
- **Cause-coded closure outcomes** — every install/decline/cancel in the system can be tagged by type (SPATIAL / OPERATIONAL / GPS_TRUST / ADDRESS_RESOLUTION), which lets the models train on separated signals.

### 6.2 — What this build adds

Three enrichments, not three new models:

1. **Technician / team GPS trails as a new signal.** Each partner's on-ground team moves through the city every day. Their GPS traces are a high-resolution map of where they actually navigate — richer than install density alone. A booking in a hex where the partner's technicians pass through weekly has higher true serviceability than the polygon alone implies. This signal is new; the model that consumes it is BM1/BM2 (already built).
2. **Landmark-grounded serviceability.** Today the partner's polygon is in lat/lng space. After this build, it is also in *landmark space* — each partner's polygon is cross-indexed with which landmarks feature in his install history. A booking confirming *"Shiv Mandir"* and *"Jai Maa Ganga Kirana"* is matched against partners whose install history contains those landmarks. The effect is stronger partner-booking matching than coord geometry alone provides.
3. **Governance on the confidence tier.** BM1 already outputs a continuous score; this build adds the HIGH/MID/LOW tiering and the action tree per tier.

### 6.3 — What it consumes

- **Partner polygon containment** — is the booking inside any partner's polygon?
- **Polygon depth / density** — if inside, how deep? How many installs in this hex?
- **GNN probability** — BM2's per-pair score for every eligible partner.
- **Technician GPS trail agreement** — does any partner's team physically move through this hex?
- **Landmark-partner install match** — do the confirmed landmarks feature in an eligible partner's install history?
- **Temporal freshness** — recent installs weigh more; stale ones decay.

### 6.4 — The three tiers

- **HIGH** — inside a dense partner polygon, technician GPS trails pass through, confirmed landmarks feature in his recent installs. This partner can install here, has installed here, and his team moves through here.
- **MID** — inside the city envelope but at the edge of any single partner's polygon, OR landmarks are recognised but no partner is dense here yet. A capable partner exists but has not yet absorbed this hex into his serviceable footprint.
- **LOW** — outside any meaningful polygon, no technician trails, no landmark match. Nobody in the current partner base serves here.

### 6.5 — What happens at each tier

- **HIGH → promise + payment captured.** Lead dispatched. Partner's notification frames the install in his own memory: *"between your Install I-X (landmark A, 5 days ago) and Install I-Y (landmark B, 2 days ago)."* Partner is expected to install. **If he declines, he is shown upfront: the landmarks around this booking will be marked as unserviceable for him, and his polygon will shrink here.** He confirms the decline with that consequence visible.
- **MID → ask-partner flow, no payment yet.** Notification to the top-ranked partner: *"this booking is at the edge of your serviceable boundary. Your nearest install is ~90m away. Confirmed landmarks: X, Y. Can you install?"* Three options:
  - **Accept** → payment captures → promise binds → dispatch. His polygon grows.
  - **Decline** → routed to next eligible partner. Polygon does not shrink (he was asked, not assigned).
  - **Verify first** → paid technician visit scheduled. Technician goes, drops a location pin, confirms *"I will install."* The area opens up for him, he gets a success bonus, and his polygon grows. Future bookings in this hex route to him first.
- **LOW → reject, no payment.** Booking routed to the expansion-demand queue so Wiom sees where coverage should grow. A small exploration quota (rate engineered separately) lets some LOW bookings through to selected partners — this prevents the model from reinforcing its own blind spots by never sampling underserved zones.

---

## §7 — Payment mechanics

The question: *when does the fee get captured?*

### 7.1 — The principle

**Payment = promise. Promise only fires when the commitment can be kept.** No conditional payments, no take-and-refund loops — refund loops create customer distrust, are operationally expensive, and violate the architecture principle that promise-making is structurally separated from promise-fulfilment.

### 7.2 — The rule, by path

| Gate 1 (Address) | Gate 2 (Serviceability) | Payment | Why |
|---|---|---|---|
| HIGH | HIGH | **At the moment of promise** | Both witnesses agree; Wiom can commit. |
| HIGH | MID (ask-partner) | **On partner acceptance** (after ask-partner, or after verify-visit confirms) | Promise isn't binding until a specific partner commits. Customer doesn't pay for ambiguity. |
| HIGH | LOW | **No payment.** | No partner exists to serve. Route to expansion queue. |
| MID (remedied to HIGH) | → re-enters above | As above | Confidence was upgraded; rule applies. |
| MID (unrecovered) | — | **No payment.** | Route to retry / CRE assist / reject. |
| LOW | — | **No payment.** | Ask customer to try again from home, or escalate. |

### 7.3 — What the customer experiences

- **HIGH / HIGH path:** same latency as today. Single payment, immediate promise.
- **HIGH / MID path:** *"We're checking with a nearby partner — this will take a few minutes. We'll only charge once someone confirms."* Notification on partner accept or verify-visit success. This is slower but truthful — today's equivalent silently takes the money and fails downstream.
- **Any LOW path:** *"We can't commit to this location right now — here's why."* No money moves. If the area is simply underserved, the customer is put on an expansion-demand list and notified when coverage reaches him.

### 7.4 — What the partner experiences

- **HIGH serviceability lead:** a direct assignment, payment already captured, partner must install (decline visible with consequence).
- **MID serviceability lead:** an *ask* rather than an *assign*, payment conditional on his acceptance, with an optional paid verify-visit that grows his polygon on success.

---

## §8 — Principles of build

The v3 frame listed nine. v4 preserves them verbatim (they are structural, not preference) and re-sorts by which gate they serve.

**Gate 1 principles (User Address Confidence)**

**P1. Verify before committing.** The system does not take the fee on the customer's self-report alone; before commit, home-presence is corroborated by a second independent channel.

**P2. Capture is not verification.** Neither the 25m infrastructure gate nor the customer's *"yes"* counts as verification. Both operate on the same untrusted input. Verification requires a signal independent of the coord and the self-report.

**P3. Ask the customer in a form that returns structure — textual and visual.** GPS knows where the phone is; only the customer knows whether the phone is at home. 46% one-sided confusion on address-not-clear calls proves the customer *has* the signal. We just never asked in a form that travels forward.

**P4. Re-capture uses a different surface than initial capture.** Round 2 changes what the customer is answering against — different landmark set, forced live re-acquisition, new probes. Never *"confirm your earlier submission."*

**Gate 2 principles (Serviceability Confidence)**

**P5. The address the partner sees is structured, and that structure is preserved end-to-end.** Landmark / gali / floor are captured as separate fields, travel as separate fields through every handoff, and render as separate fields in the partner's UI. No handoff flattens them back into a blob.

**P9. Confidence is field-level, not booking-level.** Each structured field in the partner packet carries its own confidence tier. A booking where the customer confirmed the landmark but fell back to text for the gali is not the same artefact as one where all fields were confirmed.

**System-wide principles (both gates)**

**P6. Every signal consumed has a feedback channel back to its source.** A signal with no return path is a stock that can only degrade.

**P7. Cause-code fidelity.** Downstream failures are tagged by type — GPS_TRUST / ADDRESS_RESOLUTION / SPATIAL / OPERATIONAL. Never lumped. Without this, neither belief model can learn.

**P8. Scoring artifacts stay internal; only facts cross.** Trust scores, gaming scores, belief probabilities stay inside Genie. What crosses membranes are facts — verified lat/lng, confirmed landmark, gali, floor, photo URL.

---

## §9 — The system flow (unchanged from v3)

Six stages plus a control pane running alongside. The mental model above maps onto this flow; the flow itself does not change.

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
            │     polygon + landmark-grounded BM1 +        │
            │     technician GPS trails + GNN              │
            └──────────────────────┬───────────────────────┘
                                   │  tier determines path
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  3. GOVERNANCE — tier-based action           │
            │     promise / ask-partner / verify-visit /   │
            │     reject (payment fires only on bind)      │
            └──────────────────────┬───────────────────────┘
                                   │  on bind
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  4. ACTIVE PROMISE EXPOSURE STOCK            │
            │     bookings + per-field confidence +        │
            │     landmark anchors + partner assigned      │
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
            │  6. IMMUTABLE MEMORY — full booking trace    │
            └──────────────────────────────────────────────┘

    ╔════════════════════════════════════════════════════════════════════════╗
    ║  CONTROL PANE — alongside all six stages                               ║
    ║  Night-GPS divergence · technician visit tracking · landmark-          ║
    ║  confidence accumulation · post-install validation · customer-side     ║
    ║  difficulty signals · cause-coded failure tagging                      ║
    ╚════════════════════════════════════════════════════════════════════════╝
```

---

## §10 — Feedback loops (strengthened)

The v3 frame identified four loops. v4 preserves all four, strengthens the signal-back-to-source clarity, and adds an explicit customer-side feedback loop that v3 had not named as first-class.

Every loop has the same shape:

```
  source action → immutable memory → control-pane processing
                   → (model update OR real-time nudge) → visible to source
```

### Loop 1 — Install outcome → User Address Confidence model sharpens

**Flow.** Every install outcome is tagged by cause code. Post-install, four signals validate the landmarks the customer confirmed: call-transcript mining (did the partner reference the customer's landmark or a different one?), second-call escalation (≥2 calls = compounding failure), technician field GPS trail (did he pass through the confirmed-landmark radius?), time-to-door distribution (did good landmarks shift this distribution left?). These feed **landmark-confidence per hex**, which feeds the picker the next customer in that hex sees.

**What changes over time.** Landmarks that function as real anchors rise in the picker. Landmarks that don't — drop. The customer in the same hex next month sees a sharper list.

### Loop 2 — Partner accept/decline → Serviceability Confidence polygon redraws

**Flow.** Every accept / decline / install / cancel feeds BM1. Installs grow the partner's polygon; declines shrink it (with decay — recent decisions weigh more, single declines in low-evidence hexes don't redline permanently). Zones turning red surface back to the partner in his own app so he sees the consequences of his own decisions.

**What changes over time.** A booking MID confidence today may be HIGH six months from now because the partner's install history has filled in. The polygon is a living stock.

### Loop 3 — Partner accept/decline → BM2 ranking sharpens

**Flow.** Each decision edge updates how BM2 ranks that partner for similar future bookings. Partners who consistently install in a hex rise in ranking; partners who decline or fail drop.

**What changes over time.** Within the eligible partner pool, ranking tightens as decision edges accumulate.

### Loop 4 — Night-GPS divergence → capture apparatus learns (the loop that was never closed)

**Flow.** The customer's mobile emits passive GPS pings at night. If the cluster centre diverges from the booking coord beyond a threshold, two channels fire: (a) immediate — notify customer and partner, trigger verification; (b) long-term — that mobile's jitter profile updates, and similar-profile mobiles get weighed differently at capture next time.

**What changes over time.** The 25.7% structural drift doesn't just get rejected going forward — the profile of *which mobiles produce it* gets learned and pre-empted before the fee captures.

### Loop 5 — Technician GPS → Serviceability Confidence enriches (new)

**Flow.** Partner's technician team streams GPS continuously during the workday. Trails are summarised as hex-level visitation density per partner per week. A hex the team passes through weekly is a serviceable hex even if no install has happened there yet. BM1 consumes this as a new feature.

**What changes over time.** Serviceability is no longer lagged on install events alone — the partner's actual footprint is visible in near-real-time.

### Loop 6 — Customer visibility of outcome → calibrates future input (new, user-side)

**Flow.** When a customer's booking flows through the system, he sees explicit feedback:

- *"Your landmarks matched — dispatch in progress."* (HIGH / HIGH)
- *"We're checking with a partner — you haven't been charged yet."* (HIGH / MID)
- *"We couldn't confirm you're at home — please try from home or talk to our team."* (MID unrecovered or LOW)
- *"The partner declined this area — we're working on bringing coverage. You haven't been charged."* (HIGH / LOW or MID-declined)

**What changes over time.** Customers whose inputs survive to successful install learn that accurate submission → fast dispatch. Customers whose inputs don't survive get honest feedback instead of silent failure. Repeat-customer input quality rises. **User involvement is treated as first-class — the customer is not a signal to be measured, she is a participant whose behaviour the system shapes through transparency.**

---

## §11 — User involvement, named explicitly

User involvement is load-bearing enough to deserve its own section. Three shifts from today.

**1. The customer is the ground truth for home-proximity — not a sensor.**
Today she is treated as a sensor: tap *yes*, submit GPS, done. After this build she is the only entity in the system with ground truth about where her home is, and the system asks her accordingly — structured landmarks, gali, floor, video if needed.

**2. Every customer action raises or lowers confidence.**
Landmark picks, probe survival, whether she actually goes home, rounds of corrective loop, video uploads — each is a gesture that enters the model. This makes her an active participant in the promise, not a passive submitter.

**3. The customer gets honest, structured feedback at every outcome.**
- Rejected upfront → told why, given a path (try from home / CRE call / expansion queue).
- Mid-confidence → told the system is checking and no money has moved.
- Partner declined an area → told honestly, put on expansion list, not billed.
- Successful install → surface that her landmark submission contributed (*"the partner reached your home using the Shiv Mandir landmark you confirmed"*).
- Repeat customers with clean history → lower friction on future bookings (priority slot, skipped re-verification).

Transparency is not ornamentation. It is what closes Loop 6 — future customer behaviour calibrates on past system honesty.

---

## §12 — Capabilities: what to build, what to reuse

Four groups. Each capability is tagged **N (new — this build)** or **R (reuse — already exists in R&D or production)**, with **Impact** (Quick / Medium-term) and **Q** (prioritisation quadrant — see §13).

### A. Gate 1 capabilities (User Address Confidence)

| # | Capability | N/R | Nature | Impact | Q |
|---|---|---|---|---|---|
| A1 | Continuous GPS stream during booking (not single fix), with jitter logging | N | BE + FE | Medium | Q3 |
| A2 | Nightly passive GPS pings for verification | N | BE + FE | Medium | Q3 |
| A3 | Landmark picker (Google Address Descriptors + Wiom install-history fallback + 20-25% probes). Customer confirms ≥2. | N | BE + FE + CN | Medium | Q3 |
| A4 | Gali + floor as structured chat input | N | FE + CN | Medium | Q3 |
| A5 | Home-exterior photo / short landmark-to-door video ("Reel-style") | N | BE + FE | Medium | Q3 |
| A6 | Two-round structurally-different corrective loop; parallel CRE callback path | N | BE + FE + CN | Medium | Q3 |
| A7 | Fallback text capture when no landmark relates | N | FE + CN | Medium | Q3 |
| A8 | Per-mobile jitter-handling path (uses A1 profile to flag noisy captures) | N | BE + FE + CN | Medium | Q4 |
| A9 | Google Street View pull for customer-side mid-confidence verification | N | BE + FE + CN | Medium | Q4 |
| A10 | NER parsing for A7 fallback text | N | BE + FE | Medium | Q4 |
| A11 | **User Address Confidence Model v0 — rule-based scorer** over A1-A10 inputs | N | BE | Quick | Q1 |
| A12 | Customer-side transparency UI (tier feedback, next steps, "you haven't been charged") | N | FE + CN | Quick | Q1 |
| A13 | Repeat-customer friction reduction for clean-history customers | N | BE + FE | Medium | Q4 |

### B. Gate 2 capabilities (Serviceability Confidence)

| # | Capability | N/R | Nature | Impact | Q |
|---|---|---|---|---|---|
| B1 | **BM1 activation at the gate** — consult existing KDE / hex / Bayesian shrinkage at promise time | R | BE | Medium | Q4 |
| B2 | Promise / ask-partner / verify-visit / reject governance (replaces 25m-only test) | N | BE + FE | Quick | Q1 |
| B3 | Active promise exposure stock — schema for committed bookings + per-field confidence | N | BE | Medium | Q3 |
| B4 | **Technician / team GPS ingestion as serviceability signal** | N | BE + FE | Medium | Q4 |
| B5 | Landmark-grounded serviceability — cross-index each partner's polygon with landmarks from his install history | N | BE + FE + CN | Medium | Q3 |
| B6 | **BM2 activation** (GNN) consuming A3/A4/B4/B5 enrichments | R | BE | Medium | Q4 |
| B7 | Exploration quota governor for LOW serviceability (sampled pass-through to prevent model blind-spot reinforcement) | N | BE | Medium | Q4 |
| B8 | Paid verify-visit flow — partner's product construct (visit, drop pin, confirm, bonus) | N | BE + FE + CN | Medium | Q3 |

### C. Partner-facing capabilities (Packet + Feedback)

| # | Capability | N/R | Nature | Impact | Q |
|---|---|---|---|---|---|
| C1 | Structured partner notification — landmark + gali + floor as separate fields, framed in his install history | N | BE + FE + CN | Quick | Q1 |
| C2 | Partner sees his own serviceable-area map (live) | R | BE + FE | Quick | Q1 |
| C3 | Partner sees decline-zones he is creating (with decay + time weighting) | N | BE + FE + CN | Quick | Q2 |
| C4 | Partner sees what happens when he declines (polygon shrink + consequence confirmation step) | N | FE + CN | Quick | Q1 |
| C5 | Edge-polygon "ask partner" flow for MID serviceability | N | BE + FE + CN | Quick | Q1 |
| C6 | Google Street View visible inside the booking at navigate-time | N | BE + FE | Quick | Q2 |
| C7 | Verify-visit reward + polygon-growth visibility for successful MID conversions | N | BE + FE + CN | Quick | Q2 |
| C8 | On-ground navigation assist (technician taps "stuck" → customer GPS + photos + 3-way CRE call) | N | BE + FE | Quick | Q2 |

### D. Feedback / control-pane capabilities

| # | Capability | N/R | Nature | Impact | Q |
|---|---|---|---|---|---|
| D1 | Night-GPS vs booking-GPS divergence detector (Loop 4) | N | BE + FE | Medium | Q4 |
| D2 | Technician visit tracking → nudge if no visit inside SLA | N | BE + FE | Quick | Q4 |
| D3 | Install outcome → cause-coded training loop for both models (Loops 1, 2, 3) | N | BE | Medium | Q4 |
| D4 | Landmark-confidence accumulation per hex → sharpens A3 picker (Loop 1) | N | BE | Medium | Q4 |
| D5 | Immutable memory of full booking trace | N | BE | Medium | Q3 |
| D6 | Customer-side difficulty signal monitor → interventions | N | BE + FE + CN | Medium | Q4 |
| D7 | **Post-install landmark validation (4 signals: transcript mining, second-call escalation, technician GPS, time-to-door)** | N | BE | Medium | Q4 |
| D8 | Cause-code taxonomy extension (GPS_TRUST / ADDRESS_RESOLUTION / SPATIAL / OPERATIONAL) in closure outcomes | N | BE | Quick | Q1 |
| D9 | Customer outcome transparency loop (Loop 6) | N | BE + FE + CN | Quick | Q1 |

**Counts.** A = 13, B = 8, C = 8, D = 9. Total 38 capabilities (vs. 31 in v3; the delta is mostly splitting v3 composites and adding user-transparency + exploration quota + verify-visit as first-class).

**Reuse vs new.** **R (reuse) = 3** (B1, B6, C2). **N (new) = 35**. The Serviceability model was largely pre-built in R&D; the build's effort is mostly in the User Address Confidence side, governance, user transparency, and the feedback plumbing.

---

## §13 — Prioritisation

**Axes.**
- **Impact type:** Quick (UI / surface changes, visible short-term) vs Medium-term (data, model training, feedback-loop accumulation).
- **When:** Now vs Next 1 month.

|  | Do it now | Do it in next 1 month |
|---|---|---|
| **Quick impact** | Q1 | Q2 |
| **Medium-term impact** | Q3 | Q4 |

**Q1 — Now, Quick impact.** B2 governance gate · C1 structured notification · C2 serviceable-area map · C4 decline consequence · C5 ask-partner flow · A11 User Address Confidence v0 scorer · A12 customer transparency UI · D8 cause-code taxonomy · D9 customer outcome transparency.

**Q2 — Next month, Quick impact.** C3 decline-zones · C6 Street View partner-side · C7 verify-visit reward visibility · C8 on-ground assist.

**Q3 — Now, Medium-term.** A1 continuous GPS stream · A2 night GPS · A3 landmark picker · A4 gali+floor · A5 photo/video · A6 corrective loop · A7 fallback text · B3 active promise stock schema · B5 landmark-grounded serviceability · B8 verify-visit flow · D5 immutable memory.

**Q4 — Next month, Medium-term.** A8 jitter-handling · A9 Street View customer-side · A10 NER · A13 repeat-customer friction · B1 BM1 activation · B4 technician GPS · B6 BM2 activation · B7 exploration quota · D1-D4 feedback loops · D6 customer difficulty monitor · D7 post-install validation.

**Reading the matrix.** Q3 is the substrate — if it doesn't ship, Q4 has nothing to train on. Q1 is the visible governance change and the transparency layer that makes user involvement concrete. Q2 is chain-dependent polish. Q4 is the compounding layer.

---

## §14 — How we'll know it worked

Six plain-language signals, grouped by which claim they test.

**Gate 1 is working (address confidence is well-calibrated):**
- Structural drift rate (install drift > 155m) drops from **25.7% → <5%** on the installed cohort.
- % bookings completing ≥2 landmark confirmations before payment > **90%**.

**Gate 2 is working (serviceability confidence is well-calibrated):**
- Inside-polygon install rate rises from **55.3% → >65%** (the polygon is tighter; what's inside is truly serviceable).
- MID ask-partner acceptance rate > **40%**, with verify-visit success rate > **60%**.

**The two together are working (downstream friction drops):**
- Calls per pair drops from **1.92 → <1.3**.
- Gali-stuck call-level rate drops from **7.4% → <2%**.

**The feedback loops are working (the stock is calibrating):**
- Repeat-customer User Address Confidence rises over 3-month window.
- Partner polygons show visible growth in previously-MID hexes as verify-visits accumulate.

Lag: most of these take 2-4 weeks to observe because installs accumulate on that timeline. Leading operational signals — verification-completion rate, ask-partner acceptance rate — are observable in hours.

---

## §15 — Open questions

Carried forward from v3 + new ones from the v4 reframe:

1. **Exploration quota rate** for B7 (LOW serviceability pass-through to prevent model blind-spot reinforcement) — % of LOW bookings, how partner selected, reward structure.
2. **Verify-visit paid model** (B8) — who pays (customer / Wiom / partner), how priced, success-bonus structure.
3. **Repeat-customer friction reduction** (A13) — what skipping is safe (re-verification intervals, trust decay).
4. **User Address Confidence v0 thresholds** — exact rule for HIGH/MID/LOW (landmarks × jitter × night-GPS agreement).
5. **Technician GPS ingestion cadence** (B4) — streaming vs batch, privacy model, retention.
6. **Cause-code taxonomy extension** (D8) — final list, which team owns tagging.
7. **Customer transparency copy** (A12, D9) — exact messaging for each outcome path (HIGH/HIGH fast-path, HIGH/MID wait-message, LOW rejection, partner-declined-area).
8. **MID serviceability ops throughput ceiling** — at what % of volume does ask-partner become a queue bottleneck.

---

## §16 — Why fixing only one side leaves installs broken

- **Only Gate 1 →** cleaner GPS; partner still sees an unstructured blob; still calls to parse landmark → gali → floor; 1.92 calls per pair barely moves; serviceability false-negatives continue because the R&D models aren't activated.
- **Only Gate 2 →** BM1/BM2 activated; serviceability well-priced; but the address the gate consumes is still noisy (25.7% structural drift), and partners still arrive at the wrong block; landmarks in the notification are not customer-confirmed.
- **Both →** the three parties hold the same location model at the same quality at every handoff. The voice call becomes a confirmation step, not a discovery step. The promise lands.

The two gates share infrastructure — the structured capture at flow steps 4-6 feeds both. Fixing them as parallel workstreams is cheaper than fixing them separately.

---

## §17 — What changes from v3 to v4

For readers who know v3:

1. **Mental model re-centred on two confidences.** v3 listed 31 capabilities grouped A/B/C/D. v4 groups them under the two belief models (User Address Confidence + Serviceability Confidence) that gate the flow.
2. **The two gates are sequential, not a matrix.** Serviceability is only evaluated once address is HIGH.
3. **Payment mechanics are explicit.** Payment = promise; no take-and-refund; MID serviceability holds payment until partner binds.
4. **User involvement is first-class.** Customer is an active participant with transparent feedback (Loop 6 is new).
5. **Technician GPS is an explicit serviceability signal.** New Loop 5.
6. **Verify-visit is a first-class product construct** for MID serviceability conversion.
7. **Exploration quota** protects against model blind-spot reinforcement in LOW zones.
8. **Examples removed.** The Sunita / Naveen walkthroughs from v3 are cut. The mental model now carries itself.
9. **System flow diagram preserved.** Six-stage flow + control pane unchanged.
10. **Principles preserved.** P1-P9 unchanged in wording, re-sorted by gate.

---

## Appendix — seeds for the system architect document

(Carried forward from v3 — engineering handoffs.)

- Cause-code taxonomy extension details (GPS_TRUST / ADDRESS_RESOLUTION / SPATIAL / OPERATIONAL) on closure outcomes.
- Decay mechanics on partner-side feedback (half-life, evidence weighting for C3 hex-reddening).
- Scoring-artifacts-internal rule (which scores stay inside Genie vs cross to partner app / D&A OS).
- Gaming-score vs trust-score separation (trust drives re-capture; gaming drives human review — two distinct score channels).
- Text-address reverse-lookup storage (A7 + A10 parsed output stored against captured GPS).
- Layered containment logic (partner polygon → city envelope → truly sparse) feeding BM1 confidence tier.
- Temporal navigation anchor mining (landmark phrase a successful partner actually used for nearest recent install).
- Street View coverage scoping for Indian residential bookings (sample ~1,000 Delhi bookings to measure ZERO_RESULTS rate before A9 rollout).
- User Address Confidence Model — v0 rules → v1+ learned model migration path.
- Verify-visit paid-visit pricing and success-bonus mechanics (B8).
- Exploration quota governor design (B7) — rate, partner selection, telemetry.
