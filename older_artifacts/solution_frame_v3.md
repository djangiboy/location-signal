# Solution Frame v3 — Location Signal

**Drafted:** 2026-04-21
**Primary audience:** Wiom functional leaders — including design head and product head. Read alongside the master story — the data backbone (shared separately as `master_story.md` + `master_story.csv`).
**Companion thinking contracts:** two Gate 0 submissions, one per problem, shared separately with Satyam.

---

## §1 — The two customer voices

The audit started from two customer complaints that land on Wiom's doorstep every week:

> *"Mujhe Wifi chahiye but Wiom mana kar raha hai."*
> (I want WiFi but Wiom is refusing me.)

> *"Mera connection aaj lagna tha, but koi lagane nahi aaya."*
> (My connection was supposed to be installed today, but nobody came.)

These sound like one problem. They are two. Different failure sites, different mechanisms, different fixes — and both leak into the same bottom-line number.

---

## §2 — The two decision points

Satyam's decomposition, preserved as the spine of this document:

Two decisions and three parties:

- **Point A — Wiom makes a promise** using the GPS the customer submits. If this decision is wrong, the customer either gets refused incorrectly or gets a promise Wiom cannot keep.
- **Point B — the partner decides** whether to install, then physically navigates to the home. If this decision is wrong, a promised install never lands.

Three parties involved at every step: **Wiom, partner (CSP), customer.**

Two guiding questions drive the two problems:

- **Problem 1 — Location estimation:** what is the best way to take location from the customer? (lives at Point A)
- **Problem 2 — Address translation for CSP:** how do we ensure consistency / understanding of the location across all three parties? (lives between Point A and Point B)

---

## §3 — The two objectives

**O1.** Inputs should be verified before making a promise — the customer's self-report that he is at home is not enough evidence to commit on.

**O2.** The address the partner sees should carry the same structure the customer holds in her head — landmark, gali, floor as separate confirmed fields, not a single typed blob.

These are the two claims the entire build rests on. Every capability in §11 is answerable to one or the other. The numbers (25.7% drift, 1.92 calls per pair, etc.) are measurable sub-objectives under these structural claims — not the claims themselves.

---

## §4 — This is a system build, not a point fix

Two things this doc asks functional leaders to hold simultaneously:

1. **It's a system, not two UI patches.** Capture → verify → commit → notify → install → memory — with feedback loops at every stage. Install outcomes teach the landmark picker which anchors actually work. Partner decline patterns redraw the serviceability polygon. Post-install transcripts teach the next booking's notification. The stock of knowledge grows; individual fixes don't.

2. **Self-correction is the goal.** Every partner accept / decline / install / cancel decision feeds both belief models — **BM1** (Promise Maker, *"can we serve this booking?"*) and **BM2** (Allocation ranking, *"who is the best partner?"*). They learn both **temporally** (recent decisions weigh more; boundaries shift month-over-month as install density changes) and **geographically** (a partner's serviceable polygon expands where he installs, contracts where he repeatedly declines). Landmark-confidence per hex accumulates from successful installs. Team / executive GPS trails update as they cover new zones. A promise made in month 6 is more accurate than a promise made in month 1 because the stock has learned from everything in between. Calibration, not growth.

The capability tables in §11 are the inventory. The feedback loops in §9 are what turn that inventory into a system.

---

## §5 — Problem 1: what the data says

**The apparatus is fine.** Stage A measured per-ping GPS jitter across 8,317 mobiles and 20,231 subsequent pings (`master_story.md` Part A). Per-ping jitter is tight — p75 = 20m, p95 = 155m. **70% of mobiles (5,821 of 8,317) have their worst single fix within 25m of home.** GPS physics is not the leak for most of the population.

**But install drift is much wider.** For installed bookings (Delhi Dec-2025 non-BDO, n = 3,855) we measure the distance between the booking-GPS and the GPS of the WiFi connection after install. **991 of 3,855 installs (25.7%) have drift beyond the apparatus p95 of 155m.** We call this *structural drift* — it is wider than GPS physics alone can produce. An additional **3.2%** drift >1km, **0.4%** drift >10km, max 213km — a hygiene tail that no downstream system can recover.

**Mechanism.** Customer captured GPS from not-home. Two sub-populations:
- **Near-home-but-not-home (~22% of installs):** drift 155m–1km. Café, shop, street, neighbour's house.
- **Hygiene tail (~3%):** drift >1km. Wrong-locality or tap error.

**What today's flow actually does.** The customer first submits his ilaaka (locality) pre-payment, then later is asked for his home address as free text post-payment. At the home-GPS moment, the app shows *"Are you at your home?"* — he says yes — Wiom takes one lat/long — Wiom checks the coord against the 25m infrastructure gate — if it passes, the fee captures and the promise is made. One question, one answer, one coord, one test. The customer's self-report is the entire evidence basis for the commit. There is no second channel.

Full decomposition in `master_story.md` Part A (apparatus) + Part D.A (install drift).

---

## §6 — Problem 2: what the data says

From `master_story.md` Part C (Delhi Jan-Mar 2026 non-BDO, n = 2,561 pairs / 4,930 calls):

- **40.7% of partner-customer pairs** have a first call about the location (36.2% *address-not-clear* + 4.5% *partner-reached-can't-find*).
- **1.92 calls per pair on average.** If the address were clear at notification, most pairs would need zero or one call, not two.
- **77.5% of "address not clear" calls still end in confusion** — 46% one-sided (partner confused, customer clear) + 31.5% mutual failure. Only 20% resolve on-call.

**Partner's serviceable boundary matters — a lot.** Each partner's boundary is built from *his own* accept / decline decisions over time — the shape of where he has chosen to serve. Bookings **inside** the boundary install at **55%**; **outside**, at **39%** — a **17pp gap**. When address confusion lands on a voice call, inside-boundary calls recover to 63% install; outside, they collapse to 44%. The sharpest case: when the partner is in the locality but stuck on the gali, inside-boundary = 63% install; outside = 25%. Outside the boundary, the partner doesn't know the lane grid — he can't recover from ambiguity on a call.

**What the partner actually sees today at notification.** A map + straight-line distance + his own install history + the text address. The text address is visible — he reads it — but it is a hurriedly-typed single-string blob from the customer. He cannot parse it into landmark → gali → floor without a voice call. He has information he cannot use.

**Chain-engagement is protective.** When the landmark → gali → floor chain gets touched on any call, install rate lifts by +11pp inside polygon. The chain is not a theoretical taxonomy — it's the sequence partners *already use* on voice calls to resolve addresses. Upstream capture in the same chain removes the call.

Full decomposition in `master_story.md` Parts C.B, C.C, C.D, C.E.

---

## §7 — Principles of build (9)

These nine principles constrain every capability in §11. Each is a rule of construction, not a preference. Tagged by which problem it serves.

**P1. Verify before committing. [P1]**
*Rule:* The system does not take the fee on the customer's self-report alone; before commit, home-presence is corroborated by a second independent channel.
*Why:* A one-witness commit system cannot distinguish a true "yes at home" from a false one. 25.7% of today's bookings carry structural drift because the one witness is never questioned.

**P2. Capture is not verification. [P1]**
*Rule:* Neither the 25m infrastructure gate nor the customer's "yes" counts as verification. Both operate on the same untrusted input.
*Why:* A test that consumes only the signal it is testing cannot lift trust. Verification requires a signal *independent of* the coord and the self-report.

**P3. Ask the customer in a form that returns structure — textual and visual. [P1]**
*Rule:* The second channel is the customer's own structured knowledge — we surface nearby landmarks and ask her to pick the ones near home, collect gali name, collect floor. For mid-confidence bookings we add visual structure: Google Street View confirmation or a short customer-uploaded video, which the partner also sees downstream.
*Why:* GPS knows where the phone is; only the customer knows whether the phone is at home. 46% one-sided confusion on address-not-clear calls (customer clear, partner confused) proves the customer *has* the signal. We just never asked for it in a form that travels forward to the partner.

**P4. Re-capture uses a different surface than initial capture. [P1]**
*Rule:* If Round 1 fails verification, Round 2 changes what the customer is answering against — different landmark set, forced live re-acquisition, new probes. Never *"confirm your earlier submission."*
*Why:* Asking the same question twice has no information value. A customer committed to a wrong location on Round 1 doubles down on Round 2 if the surface is identical.

**P5. The address the partner sees is structured, and that structure is preserved end-to-end. [P2]**
*Rule:* Landmark / gali / floor are captured as separate fields, travel as separate fields through every handoff (Wiom DB → allocation payload → partner notification → partner app), and render as separate fields in the partner's UI. No handoff flattens them back into a blob.
*Why:* The partner's call happens not because the text is hidden but because he can't parse an unstructured blob into the chain he navigates by. Structure is only useful if it is preserved end-to-end.

**P6. Every signal consumed has a feedback channel back to its source. [both]**
*Rule:* Install outcomes flow back to the capture apparatus (did this landmark actually function as an anchor? did this coord land at install?) and to the structured-address schema (did this gali name resolve?).
*Why:* A signal with no return path is a stock that can only degrade. Capture stays noisy today because nothing tells it otherwise.

**P7. Cause-code fidelity. [both]**
*Rule:* Downstream failures are tagged by type — `GPS_TRUST_FAILURE` (bad capture), `ADDRESS_RESOLUTION_FAILURE` (structured-address chain didn't work), `SPATIAL_FAILURE` (partner doesn't serve this area), `OPERATIONAL_FAILURE`. Never lumped.
*Why:* The two bounded problems have different roots. If their failure modes collapse into one tag, neither can learn. Lumping silently deletes everything this build adds.

**P8. Scoring artifacts stay internal; only facts cross. [both]**
*Rule:* Trust scores, gaming scores, belief probabilities stay inside Genie. What crosses membranes is facts — verified lat/lng, confirmed landmark, gali, floor, photo URL.
*Why:* If scores cross, downstream systems optimise against the score and Goodhart eats the signal. Facts are Goodhart-robust; instruments of reasoning are not.

**P9. Confidence is field-level, not booking-level. [P2]**
*Rule:* Each structured field in the partner packet carries its own confidence tier — high for a customer-confirmed landmark, high for structured gali/floor chat, lower for NER-parsed fallback text.
*Why:* A booking where the customer confirmed the landmark but fell back to text for the gali is not the same artefact as one where all fields were confirmed. Collapsing them forces the partner to trust the weakest link equally with the strongest.

---

## §8 — The shared substrate

Both problems rest on one upstream change:

**Structured capture at flow steps 4-6, before the fee is taken.** The customer confirms ≥2 landmarks near home (Google Address Descriptors for round 1; Wiom install-history anchors for round 2 fallback), types gali, types floor (required if install is at height), optional photo. Gaming-defence false-landmark probes run inside this flow at ~20-25%.

**This also consolidates today's two-step capture.** Today the customer submits his ilaaka (locality) at one step and his home address as free text at a later step (post-payment). The proposed flow collapses both into a single pre-promise capture — home GPS + near-home landmarks + gali + floor — all before the fee.

This substrate serves both problems:

- **P1 (Point A, verification):** the ≥2 landmark confirmations are the independent second channel that verifies the self-report. Without them, the gate has nothing to test the "yes at home" against. With them, the commit only fires when home-presence is corroborated.
- **P2 (Point B, address translation):** the same confirmed landmark, gali, floor become the structured fields in the partner's notification. Same capture, dual purpose.

**Not invented — behavioural.** The landmark → gali → floor chain is the sequence partners *already* use on voice calls to resolve addresses (evidence: Wiom coordination call transcripts; protective effect +11pp install inside polygon, master story Part C.E). This substrate captures upstream what partners currently rebuild on every call.

**Parallel workstreams.** P1 and P2 are not sequenced — both workstreams ship alongside. The capture is shared; each problem consumes it for its own purpose.

---

## §9 — System flow

Six stages, plus a control pane running alongside.

```
            Customer inputs (GPS + landmark + gali/floor + photos)
                                    │
                                    ▼
            ┌──────────────────────────────────────────────┐
            │  1. GATE — input verification                │   ← A1–A10
            │     jitter check, landmark relatability,     │
            │     corrective loop, fallback text, photo    │
            └──────────────────────┬───────────────────────┘
                                   │  only verified inputs pass
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  2. BELIEF MODEL 1 — can we serve this?      │   ← B1, B4, B5
            │     serviceability + confidence tier         │
            └──────────────────────┬───────────────────────┘
                                   │  confidence tier
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  3. GOVERNANCE — tier-based decision         │   ← B2
            │     promise / defer / reject                 │
            └──────────────────────┬───────────────────────┘
                                   │  on promise
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  4. ACTIVE PROMISE EXPOSURE STOCK            │   ← B3
            │     bookings + confidence + landmark anchor  │
            └──────────────────────┬───────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  5. BELIEF MODEL 2 — best partner ranking    │   ← B6
            └──────────────────────┬───────────────────────┘
                                   │                          ┌──────────────┐
                                   └────────────────────────► │ Partner-side │
                                                              │  C1 – C7     │
                                                              └──────┬───────┘
                                   ┌◄────────────────────────────────┘
                                   │  on closure
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  6. IMMUTABLE MEMORY — full booking trace    │   ← D5
            └──────────────────────────────────────────────┘

    ╔════════════════════════════════════════════════════════════════════════╗
    ║  CONTROL PANE — alongside all six stages                               ║
    ║  D1–D8: monitors, triggers interventions, trains both belief models    ║
    ║  night-GPS divergence · visit tracking · customer-difficulty signals   ║
    ║  on-ground assist · training loop · landmark confidence · D8 post-     ║
    ║  install validation closes the loop                                    ║
    ╚════════════════════════════════════════════════════════════════════════╝
```

**Feedback loops that produce self-correction:**
- Install outcome → D4 landmark-confidence → A3 picker learns which anchors work → next customer sees a sharper suggestion set.
- Partner decline pattern → C5 zones turning red → B1 can-we-serve model retrains → fewer unfit dispatches.
- Post-install transcript (D8) → addr_chain mined for actually-used landmarks → B5 landmark-grounded serviceability updates.
- Night-GPS vs booking-GPS divergence (D1) → flagged to both customer and partner → capture apparatus learns which mobiles drift.

---

## §10 — The proposed journey, step by step

The diagram in §9 shows the architecture. Here is what actually happens at each stage, in order — followed by two examples grounded in real Delhi regions.

### Step 1 — Verify inputs at capture

**This is the single step where the customer's home address gets established — prior to booking.** No more separate ilaaka-then-home-address flow. One capture: home GPS + near-home landmark confirmations + gali + floor — all pre-payment, all pre-promise.

1. App reads GPS. If the per-mobile jitter profile says this phone is noisy indoors / at night, nudge the customer to step into an open area, or trigger manual intervention.
2. App shows 3-5 nearby landmarks (Google Address Descriptors for round 1 + Wiom install-history fallback for round 2, plus 20-25% false-landmark probes for gaming defence). Customer picks ≥2 that are within 2-3 minutes' walk of **home** — not of where he happens to be at the moment.
3. If round 1 landmarks don't relate: round 2 uses Wiom's own install-history anchors. These cover hyperlocal Indian references (mandirs, kiranas, gali names) that public data misses.
4. If round 2 still fails: *"You're not at home — please try again from home."* Parallel CRE callback option always present.
5. If the customer insists he is home but no landmark is relatable: text fallback + NER parsing + lower confidence tag on downstream capture.

**The principle:** landmark relatability *is* the at-home inference. If landmarks don't fit, he isn't home — regardless of what he said when he tapped "yes."

**Edge case.** Customer books from near a landmark but not from home. The control pane's night-GPS check (below) catches this after the fact and triggers re-verification.

### Step 2 — Belief model scores serviceability

Inputs combined here: partner polygon containment, partner install density in the surrounding hex, partner familiarity with the confirmed landmarks (from his own install history), partner team / executive GPS trail, per-mobile jitter prior, landmark-grounded serviceability (B5).

Three output tiers:

- **HIGH** — inside a dense partner network, confirmed landmarks feature in the partner's install history, team-GPS trail agrees that he moves through the area.
- **MID** — inside city envelope but at the edge of any single partner's polygon; or landmarks are recognised but no partner is dense there yet.
- **LOW** — outside any serviceable address, no partner density nearby.

Today, only the 25m infrastructure check runs. The R&D Promise Maker belief model exists but is not consulted at the production gate.

**BM1 is not static.** It updates from partner accept / decline decisions over time. The same physical neighbourhood can move from MID to HIGH confidence as the partner's install history fills in. Boundaries redraw temporally (recent decisions weigh more) and geographically (installs in a hex grow the polygon; repeated declines contract it).

### Step 3 — Governance on the confidence tiers

- **HIGH:** ask for gali name and floor (floor required if install is at height). Proceed to promise.
- **MID:** pull Google Street View imagery. Ask the customer *"is this your area?"* If yes → proceed with a mid-confidence flag, optional photo. If no → route back through the A6 corrective loop.
- **LOW:** reject upfront. No fee taken. No false promise. Route to the expansion-demand queue so Wiom learns where coverage should grow next.

### Step 4 — Promise committed; BM2 ranks partners; packet handed

Booking lands in the active promise exposure stock with its confidence tier + verified landmark + gali + floor + (optional) photo.

A second belief model (**BM2**) now ranks eligible partners within the confidence tier — using each partner's historic install performance, accept / decline patterns, and landmark familiarity. BM2 is intended to sit on a scoring layer that **passes ranked scores into D&A OS**; D&A OS then uses those scores to make the final allocation decision. BM2 itself does not live inside D&A OS. The top-ranked partner (from D&A OS, on BM2 scores) gets the notification.

The notification is framed in *his* memory, not in absolute map terms:

- **Inside his polygon (HIGH):** *"Serve around this landmark. Between your Install I-X (side A, 5 days ago) and Install I-Y (side B, 10 days ago). Gali and floor as helpful context."*
- **Margin of his polygon (MID):** *"Can you install at this landmark? Your nearest install is ~90m away but this hex sits on the edge of your serviceable boundary."* Yes / no / not sure.
- **Accept → technician dispatched.** Call happens only if the technician taps "stuck" on-ground, at which point A5 photos, live customer GPS, and a three-way CRE call open on his screen.

### Real-time monitoring — the control pane

Runs alongside every booking post-commit:

- **Night-GPS divergence.** If night-time GPS pings from the mobile don't cluster near the booking coord, the customer likely doesn't actually live where he submitted. Notify both customer and partner; trigger manual verification.
- **Partner visit tracking.** If no visit-GPS trail inside the SLA window, nudge the partner and offer assistance.
- **Zone reddening on decline.** Partner's decline pattern updates his own serviceable polygon, with decay — a single decline in a new hex dims it softly; repeated declines in an evidence-rich hex redden it harder.
- **Training feedback.** Install outcome feeds the belief model (cause-coded — `GPS_TRUST_FAILURE` vs `ADDRESS_RESOLUTION_FAILURE` vs `SPATIAL_FAILURE`, never lumped). Landmarks actually used by the partner on-call feed D4 landmark-confidence, sharpening A3's picker for the next customer in the same area.

This is what makes it a system, not a feature. Every decision produces signal; every signal produces a better next-iteration decision.

---

### Example 1 — Sunita in New Usmanpur (HIGH confidence, happy path)

Sunita lives in Block E, New Usmanpur (North East Delhi — dense Wiom install zone, narrow galis, 3-4 floor walk-ups). 7:20am. She opens the Wiom app from her kitchen.

**Step 1.** GPS reads. App shows five landmarks: Shiv Mandir, Jai Maa Ganga Kirana, Naveen General Store, New Usmanpur Metro Gate 2, Hanuman Chowk. Prompt: *"Which are within 2-3 minutes' walk of your HOME?"*

Sunita picks Jai Maa Ganga Kirana and Shiv Mandir — both on her daily path. No probes fail.

**Step 2.** Belief model runs. Inside partner Ravi's polygon (he's installed eight homes within 200m in the last two months). "Shiv Mandir" features in three of his recent install notifications. Team-GPS trail shows his executives visit the block weekly. **HIGH confidence.**

**Step 3.** Ask for gali and floor. She types *E Block Gali 4* and *2*. Optional staircase photo — she skips.

**Step 4.** Promise made. Fee captures.

Ravi's notification, 7:41am:
> **Landmark:** Jai Maa Ganga Kirana *(customer-confirmed)*
> **Gali:** E Block Gali 4. **Floor:** 2.
> **Reference:** between your Install I882 (Shiv Mandir side, 5 days ago) and I891 (E-Block main road, 2 days ago). Inside your polygon. HIGH confidence.

He accepts without opening a map or calling. 11am, his technician Ramu walks from the kirana to E-Block Gali 4, third house on the right, second floor. Rings the bell. Installs by 11:45.

No call, no revisits, no `partner_reached_cant_find`. One install, zero coordination overhead.

### Example 2 — Naveen in Uttam Nagar Phase 3 (MID confidence, edge path)

Naveen lives in Uttam Nagar Phase 3 (West Delhi — phases 1 and 2 are dense, Phase 3 is a newer extension where Wiom's install density is thinner). 6:14pm. He books from home.

**Step 1.** GPS reads. App shows five landmarks: Om Sweets, Little Flower School, Uttam Nagar West Metro, Raj Bagh Gurudwara, Madhu Market. He picks Little Flower School and Raj Bagh Gurudwara. No probes fail.

**Step 2.** Belief model runs. Inside the Wiom city envelope. Naveen's hex sits on the edge of partner Suresh's serviceable boundary — Suresh's nearest installs (I4451, I4477) are about 90m away, but this specific hex has not yet been absorbed into his polygon (boundaries are drawn from density of install decisions, not just distance to nearest install). Team-GPS shows Suresh's executives in Phase 2 but not yet Phase 3. **MID confidence.**

**Step 3.** Governance pulls Google Street View. Shows the approach road. *"Is this your street?"* Naveen taps yes.

**Step 4.** Promise made with mid-confidence flag. Fee captures.

Notification routes to Suresh via the edge-polygon ask-partner flow, 6:31pm:
> *"Can you install at Little Flower School, Uttam Nagar Phase 3? Your nearest installs (I4451 five weeks ago, I4477 six weeks ago) are about 90m away but this hex sits on the edge of your boundary. Confirmed landmarks: Little Flower School, Raj Bagh Gurudwara."*
> Yes / No / Not sure.

Suresh thinks. He's been past that school twice recently — a cousin lives in the next block. He taps **Yes**.

Promise converts to dispatch. Next morning his technician arrives at the school. One short targeted call to Naveen — *"kaunsi gali aur kaunsa floor?"* — forty seconds. Naveen: *"school ke peeche wali gali, teesra ghar, pehli manzil."* Installs by noon.

**Feedback loop in action.** That install becomes the first dense anchor in Phase 3 for Suresh. Next time a customer in Phase 3 books, Suresh's polygon has grown to include this block — the ask-partner flow may not need to fire. The system calibrated itself in one install.

---

## §11 — Capability changes

Four groups. Each capability carries two tags: **Impact** (Quick / Medium-term) and **Quadrant** (Q1/Q2/Q3/Q4 per the prioritisation matrix in §13). Details of Impact and Quadrant decoded in §13.

### A. Customer-facing capabilities (pre-promise)

| # | Capability | Nature | Impact | Q |
|---|---|---|---|---|
| A1 | Capture GPS at booking time with jitter-profile logging | BE + FE | Medium | Q4 |
| A2 | Capture GPS at night passively (nightly pings) | BE + FE | Medium | Q3 |
| A3 | Show 3-5 nearby landmarks to customer (Google Address Descriptors + Wiom install-history fallback). Customer picks ≥2 near home; 20-25% false-landmark probes for gaming defence. Dual-purpose output feeds BM1 and partner notification. | BE + FE + CN | Medium | Q3 |
| A4 | Gali + floor as structured chat input | FE + CN | Medium | Q3 |
| A5 | Home-exterior photo / short video | BE + FE | Medium | Q3 |
| A6 | Two-round structurally-different corrective loop. Round 1 = public landmarks; Round 2 = install-history anchors; on still-fail = "go home and try again" + parallel CRE callback. | BE + FE + CN | Medium | Q3 |
| A7 | Fallback text capture when customer cannot relate to any landmark | FE + CN | Medium | Q3 |
| A8 | Per-mobile jitter-handling path (uses A1 profile to flag noisy captures) | BE + FE + CN | Medium | Q4 |
| A9 | Google Street View pull for customer-side visual confirmation | BE + FE + CN | Medium | Q4 |
| A10 | NER parsing for A7 fallback text | BE + FE | Medium | Q4 |

### B. Promise-making capabilities

| # | Capability | Nature | Impact | Q |
|---|---|---|---|---|
| B1 | Belief Model 1 — can we serve this booking? Activates the existing R&D Promise Maker belief model at the gate. | BE | Medium | Q4 |
| B2 | Promise / defer / reject governance. Replaces 25m-only test. Defer = await verification; reject = no promise. | BE + FE | Quick | Q1 |
| B3 | Active promise exposure stock — schema for committed bookings + confidence tier + landmark anchor | BE | Medium | Q3 |
| B4 | Partner team / executive GPS as belief-model signal | BE + FE | Medium | Q4 |
| B5 | Landmark-grounded serviceability — inferred mode from install history (day-1 shippable) + explicit partner contract (later) | BE + FE + CN | Medium | Q3 |
| B6 | Belief Model 2 — best-partner ranking, enriched with A3/A4/B4/B5 inputs | BE | Medium | Q4 |

### C. Partner-facing capabilities (post-promise)

| # | Capability | Nature | Impact | Q |
|---|---|---|---|---|
| C1 | Partner notification with structured landmark + gali + floor fields + confidence tier per field + framing in partner's own install history ("between your Install X and Install Y") | BE + FE + CN | Quick | Q1 |
| C2 | Partner sees his own serviceable-area map | BE + FE | Quick | Q1 |
| C3 | Partner sees the decline-zones he is creating | BE + FE + CN | Quick | Q2 |
| C4 | Partner sees what happens when he declines (customer-side + zone-reddening) | FE + CN | Quick | Q1 |
| C5 | Zones turning red — low install rate / high decline surface in partner app, with time + evidence decay | BE + FE | Quick | Q2 |
| C6 | Google Street View visible inside the booking (partner-side, at navigate-time) | BE + FE | Quick | Q2 |
| C7 | Edge-polygon "ask partner" flow — for bookings at the margin, system asks instead of dispatching | BE + FE + CN | Quick | Q1 |

### D. Feedback / control-pane capabilities

| # | Capability | Nature | Impact | Q |
|---|---|---|---|---|
| D1 | Night-GPS vs booking-GPS divergence detector → notifies customer and partner | BE + FE | Medium | Q4 |
| D2 | Partner visit tracking → nudge if no visit before SLA | BE + FE | Quick | Q4 |
| D3 | Install outcome → belief-model training loop (closes the install → capture loop) | BE | Medium | Q4 |
| D4 | Address-confidence per landmark / gali accumulates from successful installs → sharpens A3 picker over time | BE | Medium | Q4 |
| D5 | Immutable memory of full booking trace | BE | Medium | Q3 |
| D6 | Customer-side difficulty signal monitoring → interventions | BE + FE + CN | Medium | Q4 |
| D7 | Partner on-ground navigation assist (live customer call, push photos, request live GPS) | BE + FE | Quick | Q2 |
| D8 | Post-install landmark validation — four signals: call-transcript mining, second-call escalation, partner field GPS trail, time-to-door distribution. Factorised estimate. Feeds D4 and D3. | BE | Medium | Q4 |

Total: 31 capabilities. **Nature** = backend (BE) / frontend (FE) / content (CN).

---

## §12 — Feedback loops

**The principle (P6):** every signal the system consumes has a feedback channel back to its source. Signals with no return path are stocks that can only degrade. Today there is one closed loop (in R&D only) and one critical open loop — install outcomes never flow back to the capture apparatus, which is why capture stays noisy.

The proposed build closes four loops explicitly. These are what turn the 31 capabilities in §11 from an inventory into a self-correcting system. Each loop runs alongside the primary flow (§9) — they don't block; they learn.

### Loop 1 — Install outcome → landmark picker sharpens (customer-side)

**Capabilities:** A3 (picker) ← D4 (landmark-confidence accumulation) ← D8 (post-install landmark validation) ← D5 (immutable memory).

When a customer-confirmed landmark is actually used as a navigation anchor by the partner on-call, *and* the install lands successfully, that landmark's confidence for its hex goes up. When the customer confirmed a landmark but the partner referenced a *different* landmark on-call (or took ≥2 calls, or overshot the landmark radius), the confidence drops.

Four source signals feed this loop (D8 expanded in Appendix A2):
- **Call-transcript mining** — did partner use the customer-confirmed landmark or a different one? Negative-signal-only: can decrement, cannot increment.
- **Second-call escalation** — ≥2 calls on the same install = compounding failure, lowers landmark validation.
- **Partner field GPS trail** — did partner pass through confirmed-landmark radius? Stratified by partner familiarity (use only non-local partners' trails; local partners don't need the anchor).
- **Time-to-door distribution** — partner enters 500m radius → technician-at-door delta. Good confirmations shift this distribution left at the population level.

Factorised estimate: `install_outcome = partner_effect + landmark_effect + residual`. A landmark is "bad" only if its effect is negative *after* controlling for partner.

**What changes over time:** the next customer booking in the same hex sees a sharper landmark list. Public anchors that don't function drop in rank; Wiom install-history anchors that *do* function rise. The picker is not a static dropdown — it is a stock that calibrates.

### Loop 2 — Partner decisions → BM1 serviceability polygon redraws (gate-side)

**Capabilities:** B1 (BM1) ← D3 (install outcome → training) ← D5 ← C2 / C3 / C5 (partner-visible surfaces).

Every partner accept / decline / install / cancel decision feeds **BM1** (Promise Maker belief model). The polygon each partner draws via his own decisions evolves:
- Installs in a hex grow the polygon in that direction.
- Repeated declines contract the polygon away from that hex.
- Hexes going red in C5 (with time + evidence decay per P8) surface back to the partner in his own app (C2, C3).

The polygon redraws temporally (recent decisions weigh more — half-life calibrated in engineering) and geographically (install density shifts the boundary shape). A booking that was MID confidence six months ago can become HIGH confidence today because the partner's install history has filled in the surrounding hexes.

**What changes over time:** the same customer booking from the same GPS, six months apart, can receive different confidence tiers — not because the GPS changed, but because the partner's serviceable boundary grew (or shrank) in the interim.

### Loop 3 — Partner decisions → BM2 allocation ranking sharpens

**Capabilities:** B6 (BM2) ← D3 ← D5 ← B4 (partner team GPS) ← B5 (landmark-grounded serviceability).

**BM2** (Allocation ranking model) learns from partner-booking decision edges. Each accept / decline / install outcome updates how BM2 ranks that partner against similar future bookings. Partners who consistently install in a hex rise in ranking; partners who decline or fail to install drop.

BM2 scores pass into D&A OS, which uses them for the final allocation decision (per §10 Step 4). BM2 itself does not live inside D&A OS — it is a scoring layer upstream that D&A OS consumes.

**What changes over time:** within the eligible partner pool for a booking, ranking tightens as decision edges accumulate. Partners earn higher ranks through installs in the area, not through proximity alone.

### Loop 4 — Night-GPS divergence → capture apparatus learns (closes the open loop)

**Capabilities:** A1 (capture with jitter logging) ← A2 (nightly passive GPS pings) ← A8 (jitter-handling path) ← D1 (night-GPS vs booking-GPS divergence detector).

This is the loop that was **not closed anywhere** in the old Promise Maker. Install outcomes never flowed back to the capture moment — the apparatus stayed as noisy in month 12 as it was in month 1.

Night-GPS pings from the customer's mobile (A2) cluster around wherever the mobile actually sits at night. If the cluster centre diverges from the booking coord beyond a threshold, **D1** fires:
- **Immediate channel:** notify customer and partner; trigger manual verification (the customer may not actually live at the submitted coord).
- **Long-term channel:** that mobile's jitter profile updates. Next time the same mobile or a similar-profile mobile books, A8 (jitter-handling) weighs it differently at capture.

**What changes over time:** the capture apparatus gets better at detecting "customer not at home" cases at booking time rather than discovering them post-install. The 25.7% structural drift doesn't just get rejected going forward — the profile of *which mobiles produce it* gets learned, and A3 can pre-empt it before the fee captures.

### Control-pane nudges (real-time feedback, not training loops)

These are interventions, not learning — they route signal back to the source in real time without training a model.

- **D2** — partner visit tracking → nudge the partner if no visit-GPS trail inside SLA window.
- **D6** — customer-side difficulty signals (partner calling repeatedly, stuck at gali, `partner_reached_cant_find`) → fire customer-side interventions (slot change, direct customer-partner contact, detail nudge, manual-ops escalation).
- **D7** — partner on-ground navigation assist: when the technician taps *stuck* on-ground, push A5 photos to his screen, request live GPS from customer, open three-way CRE call.

### The shape every loop shares

```
          signal source (customer / partner action)
                         │
                         ▼
              captured in immutable memory (D5)
                         │
                         ▼
            processed by control-pane module (D1–D8)
                         │
                         ▼
       either (a) training signal → belief model update
              or (b) real-time nudge → source app / UI
                         │
                         ▼
            next customer / partner sees sharper
            suggestion · updated polygon · faster help
```

Nothing is silently discarded. Nothing sits in a write-only stock. Every signal either trains a model or triggers an intervention — and the model or intervention is visible to the party that generated the signal.

### The cause-code discipline that makes the loops learn

Every closure outcome (install / cancel / decline) is tagged by type — `GPS_TRUST_FAILURE`, `ADDRESS_RESOLUTION_FAILURE`, `SPATIAL_FAILURE`, `OPERATIONAL_FAILURE`. Without this (per P7), all failures collapse into one tag and neither BM1 nor BM2 can separate "bad coord" from "unparseable address" from "partner doesn't serve this area." Cause-code fidelity is the precondition for every loop above to produce real learning instead of noise.

---

## §13 — Prioritisation matrix

**Axes:**
- **Impact type:** Quick impact (UI / surface changes, visible short-term) vs Medium-term impact (data captures, model training, feedback-loop accumulation).
- **When to do:** Do it now vs Do it in next 1 month.

**Sequencing principle:** Q3 ships alongside Q1; Q2 and Q4 follow as Q1/Q3 stabilise.

|  | **Do it now** | **Do it in next 1 month** |
|---|---|---|
| **Quick impact** (UI / surface, short-term visible) | **Q1** | **Q2** |
| **Medium-term impact** (data, model, feedback loops) | **Q3** | **Q4** |

### Q1 — Do it now, Quick impact (5 capabilities)

Partner-side UI surface changes that go live immediately once built. Visible to CSPs this month, low cost per unit effort, high behavioural impact.

- **C1** Structured partner notification with landmark + gali + floor + partner-install framing
- **C2** Partner's own serviceable-area map
- **C4** Partner sees consequences of decline
- **C7** Edge-polygon ask-partner flow
- **B2** Promise / defer / reject governance at gate

### Q2 — Do it in next 1 month, Quick impact (4 capabilities)

UI surfaces that need a preceding capability or data pull.

- **C3** Decline-zones visible (needs C5 signal computed first)
- **C5** Zones turning red (needs decline signal to accumulate, with decay)
- **C6** Street View on partner side (depends on A9 coverage scoping)
- **D7** Partner on-ground navigation assist (needs A5 photos + live GPS plumbing)

### Q3 — Do it now, Medium-term impact (9 capabilities)

The shared substrate. Build capture stock now; value compounds as downstream systems consume it. If Q3 doesn't ship, Q4 has nothing to train on.

- **A3** Landmark picker with ≥2 confirmations + probes
- **A4** Gali + floor structured chat
- **A5** Home-exterior photo / video
- **A6** Two-round corrective loop
- **A7** Fallback text capture
- **A2** Nightly GPS pings
- **B3** Active promise exposure stock (schema)
- **B5** Landmark-grounded serviceability (inferred mode)
- **D5** Immutable memory (schema)

### Q4 — Do it in next 1 month, Medium-term impact (13 capabilities)

Model training, telemetry, feedback-loop activation. Start building now; value lands in month 2+.

- **A1** GPS capture with jitter-profile logging
- **A8** Per-mobile jitter-handling
- **A9** Street View customer-side
- **A10** NER fallback parsing
- **B1** Belief Model 1 activation at gate
- **B4** Partner team GPS telemetry
- **B6** Belief Model 2 upgrade
- **D1** Night-GPS divergence detector
- **D2** Partner visit tracking
- **D3** Install outcome → training loop
- **D4** Address-confidence accumulation per landmark
- **D6** Customer-side difficulty monitor
- **D8** Post-install landmark validation (four signals)

### Reading the matrix

**Q3 is the spine.** Capture substrate must ship in the first sprint even though full benefit lands over weeks.
**Q1 is the visible win.** Partner UI changes CSPs notice this month.
**Q2 is small and chain-dependent.** Wait for the Q1/Q3 element it needs.
**Q4 is the compounding layer.** Begin now; impact accumulates.

Tally: 5 + 4 + 9 + 13 = 31. ✓

---

## §14 — Why fixing only one leaves installs broken

- **Only Problem 1 →** cleaner GPS; partner still sees an unstructured blob; still calls to parse landmark → gali → floor; 1.92 calls per pair barely moves.
- **Only Problem 2 →** structured address; GPS still drifts; partner arrives at the wrong block despite a perfect address; `partner_reached_cant_find` at site unchanged.
- **Both →** the three parties hold the same location model at the same quality at every handoff. The voice call becomes a confirmation step, not a discovery step. The promise lands.

The two problems share infrastructure — the structured capture at flow steps 4-6 is one build that serves both. Fixing them as parallel workstreams is cheaper than fixing them separately.

---

## §15 — How we'll know it worked

Four plain-language signals:

- **P1 check:** 25.7% drift-beyond-apparatus-noise starts dropping on the installed cohort (target <5%).
- **P2 check:** 1.92 calls-per-pair drops below 1.3.
- **P2 check:** 7.4% gali-stuck call-level rate drops below 2%.
- **Joint check:** installs per partner-week rise *at held promise volume* — calibration improving, not volume pumping.

These lag the intervention by 2-4 weeks because installs take that long to come in. Leading operational signal — % of bookings completing ≥2 landmark confirmations at capture — is observable in hours.

---

## §16 — Companion files + open questions

**Companion files shared alongside this document:**
- The master story (`master_story.md` + `master_story.csv`) — the data backbone this frame cites throughout. Read both together.
- Two Gate 0 thinking contracts, one per problem, shared with Satyam — the rigourous measurement-and-learning versions of Problem 1 and Problem 2.

**Open questions carried forward:**
1. When does the fee capture in the defer path — conditional on night-GPS validation (refund if fails), or only after full verification?
2. A3 landmark picker — exact number of landmarks shown, confirmation threshold, re-capture limit before A6 fires.
3. A8 jitter threshold — learned per mobile, or population floor.
4. C3/C5 decline-zone visibility — real-time or daily snapshot; own-partner only or cross-partner (privacy mask).
5. BM1 output — binary promise/defer/reject or tiered (High/Mid/Low with different downstream paths).
6. C7 medium-confidence routing — ops throughput ceiling before this becomes its own queue bottleneck.

---

## Appendix — seeds for the system architect document

### A1. R&D concepts used in this document — a brief introduction

The main body references terms from Wiom's R&D belief-model work. Two models exist — a gate-side belief model (**BM1**) and an allocation-side ranking model (**BM2**). Neither is wired into production today. A functional-leader glossary so the rest of the appendix reads without friction.

**Building blocks (shared across both models)**

- **Hex grid.** Geography divided into uniform hexagonal cells (H3-style, roughly 100m across). Each hex is an accounting unit — installs, declines, call outcomes, landmark mentions counted per hex per partner. Smaller than a neighbourhood, larger than an address.
- **Supply-efficiency (SE) hex grid.** For each (partner, hex) pair, installs ÷ total dispatches — the partner's install rate in that hex. Green / orange / red buckets.
- **Partner serviceable boundary (polygon).** Inferred service zone per partner, built by clustering his SE-weighted hexes. Evolves with his accept / decline / install decisions.
- **Cause-coded closure outcomes.** When a booking closes, the cause is tagged — SPATIAL_FAILURE / OPERATIONAL_FAILURE / GPS_TRUST_FAILURE / ADDRESS_RESOLUTION_FAILURE. Lets either belief model retrain on separated signals instead of one lumped tag.

**BM1 — Promise Maker belief model**

Answers *"can we serve this booking?"* Gate-side. Technique:

- **KDE / adaptive Gaussian fields.** Each install in a partner's history places a Gaussian kernel at that location; fields are summed across his installs to produce a continuous serviceability field — smoother than per-hex step functions.
- **Multi-resolution hex grid.** Coarser hexes where install density is sparse; finer where dense.
- **Bayesian shrinkage.** When a hex has only two installs, its SE rate is unreliable. Shrinkage pulls low-evidence hex rates toward a prior — heavy on the prior when evidence is thin, light when dense. Prevents noise-driven decisions in low-data corners.

Output: a serviceability field per partner → confidence tier per booking.

**BM2 — Allocation ranking model**

Answers *"among partners eligible to serve this booking, who ranks highest?"* Allocation-side. Technique:

- **GNN (Graph Neural Network).** A model that learns from decision edges — (partner, booking) pairs tagged accept / decline / install / cancel. Outputs, per pair, a probability that this partner will install this booking if dispatched. Captures partner-specific area knowledge beyond what raw coord geometry carries.
- **Composite score.** Aggregates GNN probability with other features (distance, partner capacity) into a ranked partner list.

Output: ranked partner list for notification.

**Promise Maker in production today.** A single rule — the 25m infrastructure-proximity check. BM1 (above) exists in R&D but is not consulted at the gate. Similarly, production allocation uses different logic than BM2 does. Both belief models are built, validated on historical data, not yet wired into production. Activating them is part of what this build enables.

---

### A2. Post-install landmark validation (D8 expanded)

Four signals closing the loop on whether customer-confirmed landmarks actually functioned as navigation anchors in the field:

- **Call-transcript mining** — did the partner reference a *different* landmark on-call than the customer-confirmed one? Negative-signal-only: can decrement landmark confidence, cannot increment.
- **Second-call escalation** — ≥2 calls on the same install = compounding failure, lowers landmark validation.
- **Partner field GPS trail** — did partner pass through confirmed-landmark radius? Stratified by partner familiarity (use only non-local partners' trails; local partners don't need the anchor).
- **Time-to-door distribution** — partner enters 500m radius → technician-at-door delta. Good confirmations shift this distribution left at the population level.

Factorised estimate: `install_outcome = partner_effect + landmark_effect + residual`. A landmark is "bad" only if its effect is negative *after* controlling for partner. Output flows back to A3's picker via D4 and to both belief models' training via D3.

### A3. Belief-model note

Two belief models sit in R&D:

- **BM1 — Promise Maker belief model**: KDE Gaussian fields, multiresolution hex grid, Bayesian shrinkage, cluster polygons. Answers *can we serve this?*
- **BM2 — Allocation ranking model**: graph neural network on partner-booking decision edges + composite score. Answers *who ranks highest?*

Both are **not consulted in production today.** The 25m infrastructure check is alone in front of the customer's money; production allocation uses different logic than BM2. Both Problem 1 (verification substrate) and Problem 2 (structured address) give these models the inputs they need to finally activate. Supporting, not primary.

**Note on integrity.** BM2's composite score and GNN are built on partner-side decision edges (accept, decline). These express *partner willingness to serve a geographic area* — a signal generated independently of whether the customer's submitted GPS was accurate. Customer-side noise is an input-side issue, not a signal-side one. Activating the belief models in production does not require customer-side capture to be clean first; the two workstreams are orthogonal. Cleaner captures will sharpen model precision over time, not resurrect it from corruption.

The master story validates this independently:
- Install rate separates 44pp across coord-distance deciles — partners respond systematically to coord-based geometry.
- Area-decline rate ladders monotonically pre-accept (~20pp on distance, ~23pp on GNN probability) — partners decline far or unfamiliar areas before seeing anything else.
- The GNN's +3.8pp edge on area-decline concentration reflects partner-specific area knowledge picked up from install + decline history, beyond what raw geometry carries.

### A4. Out-of-scope handoffs to the system spec

These land in engineering, not frame:

- **Cause-code taxonomy extension** — add `GPS_TRUST_FAILURE` + `ADDRESS_RESOLUTION_FAILURE` to closure outcomes. Without this, new capture produces no new learning.
- **Decay mechanics on partner-side feedback** — specific half-life and evidence weighting for C5 hex-reddening. First-principles says decay is mandatory; shape is empirical.
- **Scoring-artifacts-internal rule** — which exact scores stay inside Genie versus cross membranes. P8 states the principle; spec ratifies the list.
- **Gaming-score vs trust-score separation** — trust drives re-capture; gaming drives human review. Two distinct score channels from different feature sets. Re-capturing a gaming attempt would reward it.
- **Text-address reverse-lookup storage** — when A7 + A10 parse unstructured text, store parsed output against captured GPS as enrichment stock. `what3words` and pincode cross-check deferred from day-1.
- **Layered containment logic** — three-layer test (partner polygon → city envelope → truly sparse) feeding BM1 confidence tier.
- **Temporal navigation anchor mining** — extracting the landmark phrase a successful partner actually used for the nearest recent install; ranking by recency × install-success.
- **Street View coverage scoping for Indian residential bookings** — sample ~1,000 Delhi bookings to measure `ZERO_RESULTS` rate before A9 commits to user-facing rollout.
- **Medium-confidence C7 routing** — ops throughput ceiling; when this tier exceeds ~15-20% of volume it becomes its own queue bottleneck.
