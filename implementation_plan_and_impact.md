# Implementation Plan & Expected Impact — Location Signal

**Drafted:** 2026-04-22
**Companion to:** `solution_frame_v6.md` (the frame) + `master_story.md` + `master_story.csv` (the evidence)
**Audience:** Engineering leads sequencing the build · functional leaders attributing impact · finance partners sizing the ask
**Scope:** v6 body (42 capabilities, Phases 1-3). Appendix C (cross-OS integrity) is sized separately in §10.

---

## §1 — What this document is for

Two questions functional leaders and engineering leads will ask the moment the frame lands:

1. **In what order do the 42 body capabilities get built, and what blocks what?**
2. **Which capability moves which metric, and by how much?**

This document answers both. It is deliberately narrow. It does not re-argue the frame (v6 does that) or the evidence (master story does that). It sequences the build and attributes the impact.

---

## §2 — Baselines: the numbers the build is moving

Every target in this document is measured against one of these baselines. Source: `master_story.md` / `master_story.csv`. Cohort: Delhi Dec-2025 non-BDO unless otherwise noted.

| # | Metric | Current | Source |
|---|---|---|---|
| **M1** | Structural drift >155m on installed cohort | **25.7%** | Part D.A |
| **M2** | ≥2 landmark confirmations before payment | 0% (capability doesn't exist) | — |
| **M3** | Inside-polygon install rate | **55.3%** | Part C.D |
| **M4** | Outside-polygon install rate | **38.6%** | Part C.D |
| **M5** | Inside-polygon install rate when partner stuck on gali | **62.5%** | Part C.D |
| **M6** | Outside-polygon install rate when partner stuck on gali | **25.4%** | Part C.D |
| **M7** | Chain-engagement lift (landmark → gali → floor touched on-call) inside polygon | **+11.2pp** | Part C.E |
| **M8** | Location-reason first call rate | **40.7%** (36.2% ANC + 4.5% PRCF) | Part C.B |
| **M9** | Calls per partner-customer pair | **1.92** | Part C.B |
| **M10** | ANC calls still ending in confusion | **77.5%** (46% one-sided + 31.5% mutual) | Part C.B |
| **M11** | Gali-stuck call rate | **7.4%** (call-transcript level) | Part C.C |
| **M12** | Install rate separation by distance decile | **43.81pp** | Part B |
| **M13** | Install rate separation by GNN probability decile | **56.77pp** | Part B |
| **M14** | Partner-side 30.8pp same-prob splitter-share gap | **30.8pp** | Appendix |
| **M15** | Promise-to-install conversion at held promise volume (the gameability control) | TBD Sprint 1 | — |

**M15 is the primary NUT-linked target.** Every other metric is directional. M15 is the one that cannot be gamed by tightening the gate.

---

## §3 — Implementation tracks

**All 42 body capabilities (Tracks 1-3) are built by the Genie team.** External sign-offs are called out explicitly in §4 phase gates where they are entry criteria (Legal privacy ratification for B4; Finance sizing for B8/B10/A14; SR-OS as a separate OS for A14). Track 4 (integrity) is the only genuinely cross-OS workstream; it runs on its own timeline.

```
  ┌─────────────────────────────┐
  │ Track 1 — Capture Substrate │  (Gate 1)       owner: Genie
  │ A1-A14, D1, D4-D7            │                 timeline: Q1 + Q3
  └──────────────┬───────────────┘
                 │
  ┌──────────────▼───────────────┐
  │ Track 2 — Gate Activation    │  (Gate 2)       owner: Genie
  │ B1-B10, D3, D8                │                 timeline: Q1 (governance) + Q3 (substrate) + Q4 (models)
  └──────────────┬───────────────┘
                 │
  ┌──────────────▼───────────────┐
  │ Track 3 — Partner Experience │  (Packet + feedback)  owner: Genie
  │ C1-C9, D2, D9                 │                 timeline: Q1 + Q2
  └──────────────────────────────┘

  ┌─────────────────────────────┐
  │ Track 4 — Integrity Channel │  (cross-OS)      owners: Q-OS + XS-OS + Enforcement OS + Genie
  │ E1-E8                        │                 timeline: Phase 4 (runs parallel to Phases 1-3)
  └─────────────────────────────┘
```

Tracks 1-3 have hard dependencies on each other (next section). Track 4 has no hard dependency on Tracks 1-3; Tracks 1-3 have no hard dependency on Track 4.

---

## §4 — Phases and phase gates

Five phases. Each phase has **entry criteria** (what must be true to start) and **exit criteria** (what must be true to move on). Don't cross a gate on calendar alone.

### Phase 1 — Ship polygon-only Gate 2 + capture substrate (Q1 + Q3 start)

**Scope:** B2 governance + polygon-only containment (Phase 1 of §2.6), A1-A7 capture substrate, A11 UAC v0 scorer (rule-based), A12 + D9 transparency, A14 SR-OS queue, B3 active promise stock with drain, B8-B10 verify-visit substrate, C1-C5 partner packet + consequence, D5 immutable history, D8 cause-code taxonomy.

**Entry criteria:**
- Cause-code taxonomy (D8) finalised by Genie; Q-OS owner acknowledges the shared contract.
- SR-OS queue live with an owner named; SLA signed off (10 min first touch, 24h resolution). SR-OS is a separate OS; Genie drives the conversation to get it operational.
- Polygon definition per partner frozen for Phase 1 (static snapshot OK; Phase 2 onwards these become live).
- Finance sizing done on B8 verify-visit bonus pool, B10 waiver budget, A14 SR-OS queue staffing.

**Exit criteria (ship gate):**
- M2 ≥90% (pre-payment ≥2 landmark confirmations operating).
- M1 declining — installed-cohort drift ≥10pp below 25.7% baseline on rolling 90-day window.
- A14 SR-OS queue volume <5% of MID cohort; breach shocks firing correctly.
- Zero production-time integrity errors in B3 drain accounting.

### Phase 2 — BM1 activation for tier enrichment (Q4)

**Scope:** B1 BM1 activation post-containment, B4 technician GPS ingestion, B5 landmark-grounded serviceability, D1 night-GPS divergence detector, D2 SLA-miss monitor wired to B3 drain, D3 install outcome → training loop, D4 landmark-confidence with triplet + decay, D6 customer-side difficulty monitor, D7 post-install validation.

**Entry criteria:**
- Phase 1 exit criteria met.
- BM1 production-wiring sign-off (Genie internal R&D → production handoff).
- Technician GPS privacy model ratified (Genie drafts; Legal ratifies).

**Exit criteria:**
- Tier classification agreement rate between BM1-enriched tiering and Phase 1 polygon-depth tiering >80% on HIGH; explicit delta report on MID tier reshuffles.
- M3 lifting — inside-polygon install rate ≥60% (baseline 55.3%, target >65%).
- No increase in M11 gali-stuck rate (regression guard).

### Phase 3 — BM2 activation for ranking (Q4+)

**Scope:** B6 BM2 activation, B7 exploration quota with partner rotation, A8-A10 jitter-recovery + Street View customer-side + NER, A13 repeat-customer friction reduction, C6-C9 partner-side advanced (Street View, verify-visit reward visibility, on-ground assist, team-trail visibility).

**Entry criteria:**
- Phase 2 exit criteria met.
- BM2 ranking sign-off; independent verification that BM2 scores load on P(accept) not P(install|accept) as the master story established.
- Partner-rotation logic reviewed against the v4 Donna failure mode (route-to-nearest reinforcement).

**Exit criteria:**
- M9 calls per pair ≤1.4.
- M11 gali-stuck ≤3%.
- Phase 1 shock volume on A14 stable or declining.

### Phase 4 — Integrity channel (cross-OS, parallel track)

See v6 Appendix C. Sized in §10 below; not blocking Phases 1-3.

### Steady state — Beyond Phase 3

Phases 1-3 shipped; the four feedback loops (1, 2, 4, 5) have 90-day data. Loop 3 (GNN weights) has ≥2 retrain cycles. Metrics convergence expected on a 6-month horizon after Phase 3 exit.

---

## §5 — Dependency graph

Hard dependencies (solid arrow = must-precede). Soft dependencies (dashed = recommended order) noted below the chart.

```
                 A11 (UAC scorer)
                      ▲
                      │ needs scoring inputs
     ┌────────────────┼────────────────┐
     A1    A2    A3   A4    A5    A8   │
     │     │     │    │     │     │    │
  booking ping pick struct photo jitter │
   GPS  cluster list  chat video profile│
                                         │
                                         ▼
                                    A6 corrective loop
                                         │
                                         ▼
                                    A14 SR-OS queue (if round 2 fails)

            D1 night-GPS divergence — NEEDS A1 + A2 + A8 all live

            B1 (BM1) — NEEDS D3 training loop ≥ 1 retrain cycle
            B6 (BM2) — NEEDS D3 training loop ≥ 2 retrain cycles (more edge-sparse)

            B3 drain — NEEDS D2 SLA monitor
            B8 verify-visit payout — NEEDS B9 outcome capture

            C1 structured notification — NEEDS A3 + A4 (source data)
            C9 team-trail visibility — NEEDS B4 technician GPS ingestion
            Loop 5 (tech-GPS enrichment) — NEEDS B4 + C9

            D4 landmark-confidence — NEEDS D7 (4 validation signals)
            D7 — NEEDS D5 immutable history (signal source)

            A13 repeat-customer friction reduction — NEEDS ≥90 days of A11 history
```

**Soft ordering** (quality improves with order, doesn't break without it):
- B5 landmark-grounded serviceability improves substantially after D4 has 30+ days of accumulation.
- C3 decline-zones are visible day 1 from polygon history; they get sharper after B4 feeds Loop 2.
- A9 (customer-side Street View) and C6 (partner-side Street View) share API integration work — sequence them together in Q2/Q4 regardless of which surface ships first.

---

## §5.5 — All 42 capabilities, ranked simplest → most complex

**Complexity rubric.** Each capability scored on three axes. Sum is the complexity score.

- **Dependency weight** — 0 = no prerequisites · 1 = 1-2 prior capabilities needed · 2 = 3+ prior capabilities (long-pole)
- **Tech-build weight** — 0 = copy/schema/rules only · 1 = standard FE/BE plumbing · 2 = new data pipeline or state machine · 3 = ML model wiring, mining pipeline, or large-scale telemetry ingest
- **Integration surface** — 0 = Genie-internal only · 1 = Genie + one app surface (mobile / partner app) · 2 = cross-OS or finance pathway

Range: 0 (trivial) → 5 (long-pole). Phase tag = where the capability ships: **[P1]** Phase 1 · **[P2]** Phase 2 · **[P3]** Phase 3.

```
 Complexity →   0 (trivial) ————————————————————————————————————————————————————————→ 5 (long-pole)

 TIER 0 — Score 0 — Copy / schema / rules only, no dependencies
 ┌─────────────────────────────────────────────────────────────────────────────────────┐
 │ [P1] A7  · Fallback text capture                                                    │
 │ [P1] D8  · Cause-code taxonomy (GPS_TRUST / ADDRESS_RES / SPATIAL / OPERATIONAL)    │
 └─────────────────────────────────────────────────────────────────────────────────────┘

 TIER 1 — Score 2 — Single-surface build, no cross-deps
 ┌─────────────────────────────────────────────────────────────────────────────────────┐
 │ [P1] A1  · Continuous GPS stream during booking                                     │
 │ [P1] A4  · Gali + floor structured chat                                             │
 │ [P1] A5  · Home-exterior photo / short video                                        │
 │ [P1] A6  · Two-round corrective loop (hands off to A14 on round 2 fail)             │
 │ [P2] A9  · Google Street View pull (customer-side)                                  │
 │ [P1] A12 · Customer transparency UI                                                 │
 │ [P1] B2  · Promise / ask-partner / verify-visit / reject governance                 │
 │ [P1] C2  · Partner's own serviceable-area map (live)                                │
 │ [P1] C4  · Decline consequence shown pre-confirm                                    │
 │ [P1] C6  · Street View at navigate-time (partner-side)                              │
 │ [P1] D5  · Immutable history log (H)                                                │
 │ [P2] D6  · Customer-side difficulty signal monitor                                  │
 │ [P1] D9  · Customer outcome transparency loop                                       │
 └─────────────────────────────────────────────────────────────────────────────────────┘

 TIER 2 — Score 3 — Standard plumbing; one dependency or one external integration
 ┌─────────────────────────────────────────────────────────────────────────────────────┐
 │ [P1] A2  · Nightly passive GPS pings                                                │
 │ [P1] A14 · SR-OS queue for MID remediation (cross-OS to SR-OS)                      │
 │ [P2] B1  · BM1 activation — polygon-only containment                                │
 │ [P1] B3  · Active promise exposure stock with drain on 48h-SLA-miss                 │
 │ [P3] B7  · Exploration quota with partner rotation                                  │
 │ [P1] B9  · Verify-visit outcome capture (reached-door tag + landmarks-used)         │
 │ [P1] B10 · Remediated-HIGH × MID path tagging + waived-cost accounting (Finance)    │
 │ [P1] C1  · Structured partner notification (landmark + gali + floor, packet format) │
 │ [P1] C3  · Decline-zones with decay + time weighting                                │
 │ [P1] C5  · Edge-polygon ask-partner flow                                            │
 │ [P1] C9  · Technician team-trail visibility to partner                              │
 │ [P2] D2  · Technician visit tracking → SLA nudge                                    │
 └─────────────────────────────────────────────────────────────────────────────────────┘

 TIER 3 — Score 4 — Multi-input pipeline, new state machine, or multi-surface integration
 ┌─────────────────────────────────────────────────────────────────────────────────────┐
 │ [P1] A3  · Landmark picker + probes (Google Address Descriptors + install-history)  │
 │ [P2] A8  · Per-mobile jitter-handling path with recovery                            │
 │ [P2] A10 · NER parsing for A7 fallback text                                         │
 │ [P1] A11 · UAC v0 scorer storing triplet state                                      │
 │ [P3] A13 · Repeat-customer friction reduction (needs 90d A11 history)               │
 │ [P2] B4  · Technician / team GPS ingestion (large-scale telemetry + Legal)          │
 │ [P1] B5  · Landmark-grounded serviceability (partner install-history × landmarks)   │
 │ [P1] B8  · Paid verify-visit flow (Finance-sized bonus pool + damping)              │
 │ [P1] C7  · Verify-visit reward + polygon-growth visibility                          │
 │ [P2] D1  · Night-GPS divergence detector                                            │
 │ [P2] D3  · Install outcome → cause-coded training loop                              │
 │ [P2] D4  · Landmark-confidence accumulation with triplet + decay                    │
 └─────────────────────────────────────────────────────────────────────────────────────┘

 TIER 4 — Score 5 — ML model wiring, multi-feed composition, or full three-way integration
 ┌─────────────────────────────────────────────────────────────────────────────────────┐
 │ [P3] B6  · BM2 activation (GNN wiring into production ranking)                      │
 │ [P1] C8  · On-ground navigation assist (A5 photos + live customer GPS + CRE call)   │
 │ [P2] D7  · Post-install landmark validation — 4-signal factorised estimate          │
 │            (call-transcript mining + second-call + field GPS + time-to-door)        │
 └─────────────────────────────────────────────────────────────────────────────────────┘
```

### Reading the ladder

**Quick-wins (Tier 0-1, 15 capabilities).** Almost all [P1]. If a sprint stalls, these are the items to pull forward — they unblock user-visible flow without waiting for dependent work. The two Tier-0 items (A7 text fallback, D8 cause-code taxonomy) are critical design decisions dressed as simple work — get them right early.

**Standard plumbing (Tier 2, 12 capabilities).** The middle of the build. Most of the partner-packet UI and the exposure-stock governance lives here. These are where most of Phase 1 weight lands.

**Long-pole pipelines (Tier 3, 12 capabilities).** The learning substrate. These are what makes the system *self-correct* rather than ship-and-stop. Don't under-invest here — Tier 3 is where the compounding lives.

**The three structural long-poles (Tier 4).** B6 (BM2 GNN activation), C8 (three-way on-ground assist), D7 (four-signal post-install validation). Each has a named dependency chain in §5 that must be walked end-to-end before they activate. Size them accordingly in the Phase 3 entry review.

### Phase distribution by tier

| Phase | Tier 0 | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Phase total |
|---|---:|---:|---:|---:|---:|---:|
| **P1** | 2 | 10 | 9 | 5 | 1 | **27** |
| **P2** | 0 | 3 | 2 | 5 | 1 | **11** |
| **P3** | 0 | 0 | 1 | 1 | 1 | **3** |
| **Sub-total** | **2** | **13** | **12** | **11** | **3** | **41** |

*(Note: B8 is tagged [P1] because its flow ships Phase 1 but its damping mechanics mature through Phase 2. One capability of the 42 — omitted from the grid above due to its split phasing — is counted once under P1. Total across all rows = 41 + 1 = 42.)*

**Phase 1 shoulders 27 of 42 capabilities** (64%) — and importantly carries the Tier 4 long-pole C8 (on-ground navigation assist). Phase 2 is ML + telemetry heavy (5 Tier-3 pipelines land here). Phase 3 is small (3 capabilities) but carries the hardest work (B6 GNN activation, A13 long-horizon friction reduction, B7 exploration quota).

---

## §6 — Impact attribution: which capability moves which metric

This is the table that answers *"if I remove capability X, which metric slips?"* and *"if I want to move metric Y, which capabilities are load-bearing?"*

Confidence codes: **H** = mechanism directly testable on master story baselines · **M** = mechanism plausible, magnitude uncertain · **L** = directional only, magnitude TBD Sprint 1.

| Metric (baseline → target) | Primary drivers (load-bearing) | Secondary (sharpens over time) | Mechanism | Conf. |
|---|---|---|---|---|
| **M1** 25.7% drift → **<5%** | A3 (landmarks) + A11 (UAC scorer) + A1 (GPS stream) + A8 (jitter recovery) | D1 (night-GPS divergence), D4 (landmark-confidence compound) | Gate 1 rejects LOW and routes MID to A14; bad coords never reach payment | H |
| **M2** 0% → **>90% ≥2 confirmations** | A3 + A11 | A13 (repeat-customer friction down) | Direct product metric — ≥2 picks is a UX gate | H |
| **M3** 55.3% inside-polygon → **>65%** | C1 (structured notification) + A3 + A4 (source structure) | B1 (BM1 tier sharpens), D4 (landmark confidence rises) | Chain-engagement lifts inside-polygon install by +11.2pp per master story; capturing upstream converts that lift from occasional-on-call to by-default | H |
| **M7-derived** — % of installs where landmark/gali/floor touched on-call | N/A today; **target 100% in packet** (touches happen pre-call) | C1 format compliance | Structure arrives in the packet; "touched on-call" is obsolete as a discovery path, becomes a confirmation path | H |
| **M8** 40.7% location-reason first call → **<25%** | C1 + A3 + A4 + A5 (photo/video) | C8 (on-ground assist when still stuck) | Partner receives structure; doesn't need first call to parse | H |
| **M9** 1.92 calls/pair → **<1.3** | C1 + A3 + A4 | C6 Street View partner-side at navigate-time | Today most pairs need ≥2 calls because the chain rebuilds on voice. Packet-resident chain drops most pairs to 0-1 call | H |
| **M10** 77.5% ANC within-call confusion → **<50%** | A3 + A5 (photo/video) + C1 | A9/C6 Street View | Confusion persists when the call is the only resolution surface. Packet-visible photo + confirmed landmark gives partner a non-voice channel | M |
| **M11** 7.4% gali-stuck → **<2%** | A4 (gali as structured field) + C1 (gali visible in packet) | — | Direct fix — unstructured gali → structured gali, visible in packet | H |
| **M12 / M13** separation holds, doesn't regress | B1 + B6 + training loop D3 | D7 post-install validation | Baselines already separate 43.81pp / 56.77pp on distance / GNN — target is **no regression** under new flow, not increase | H (no regression) |
| **M15 promise-to-install conversion at held volume** → **rises** | All of Phase 1 + B1 + B6 | D8 cause-code fidelity | The ONLY un-gameable metric. Tight gate drops volume; held-volume conversion proves calibration, not rejection | H |

### Capability impact breakdown — reverse view

Which metric does each capability move?

**Gate 1 capabilities (Group A)**
- A1-A2 → M1 (drift), M10 (ANC residual)
- A3 → M1, M2, M3, M8, M9, M10
- A4 → M3, M9, M11 (gali-stuck is A4's headline metric)
- A5 → M10 (photo channel), M8 (secondary)
- A6-A7 → M1 (catch-all for hard cases)
- A8 → M1 (jitter-recovery prevents good mobiles from being stained)
- A9 → M10 secondary
- A10 → M1 tail cases (NER on fallback text)
- A11 → M1, M2 (the scorer is the gate)
- A12 → M2 indirectly (transparency keeps MID users in the flow)
- A13 → M9, M10 (repeat-customer experience over 90+ days)
- A14 → M1 (catches MID that Gate 1 can't auto-resolve)

**Gate 2 capabilities (Group B)**
- B1 → M3 lift beyond baseline, M12/M13 no-regression
- B2 → M15 (governance is how held-volume conversion rises)
- B3 → M15 (no leaks in active-exposure stock)
- B4 → Loop 5, feeds M3 lift, M11 reduction in Phase 2+
- B5 → M3, M9 (landmark-partner cross-index tightens tier)
- B6 → M13 no-regression, M15 (Phase 3)
- B7 → **expansion-queue graduation rate** (Appendix metric)
- B8 → M3 MID lift, M15 (paid verify-visit is the MID conversion path)
- B9 → Loops 1 + 2 calibration — compounds every other metric slowly
- B10 → finance integrity on remediated-HIGH × MID cohort

**Partner-facing (Group C)**
- C1 → M3, M8, M9, M11 (the packet is the translation layer)
- C2-C3 → partner retention + M3 over time (partner sees own state)
- C4 → partner-side decision quality — reduces bad MID accepts
- C5 → M3 MID-tier conversion
- C6 → M9, M10 (Street View at navigate-time)
- C7 → partner motivation on verify-visit path → M3 MID conversion
- C8 → M9 tail (on-ground assist on stuck calls)
- C9 → partner buy-in for technician GPS program (B4 adoption)

**Feedback / control-pane (Group D)**
- D1 → M1 (detects post-payment drift → feeds back to A8 profile)
- D2 → M15 (prevents B3 stock from silently leaking)
- D3 → M3 lift, M12/M13 over time (compounds the belief models)
- D4 → M3 lift, M8 reduction over time
- D5 → precondition for D7, D3, everything backward-looking
- D6 → qualitative (customer friction flags ops)
- D7 → D4 quality (four-signal validation)
- D8 → **cross-cut enabler** — no metric moves correctly without cause-code fidelity
- D9 → repeat-customer trust (long-tail M2 compliance)

---

## §7 — Phase-level expected impact

What the dial reads at the end of each phase. Ranges reflect phase-end vs. steady-state.

### End of Phase 1 (Q1 + Q3 capture shipped; polygon-only Gate 2 live)

| Metric | Phase 1 target | Reasoning |
|---|---|---|
| M1 drift | 25.7% → **15-18%** | Gate 1 catches the worst drift; long tail needs loops 1 + 4 to compound |
| M2 ≥2 landmarks | 0 → **85-92%** | Direct UX metric |
| M11 gali-stuck | 7.4% → **3-4%** | Gali now structured; partner sees it |
| M9 calls/pair | 1.92 → **1.55-1.65** | Chain arrives in packet; tail of stuck cases still calls |
| M15 held-volume conversion | baseline → **+5-8pp** | B2 governance + no-leak B3; MID verify-visit conversion begins |
| M3 inside-polygon install | 55.3% → **58-61%** | C1 lift without BM1 tier sharpening |

### End of Phase 2 (BM1 enrichment live; technician GPS flowing)

| Metric | Phase 2 target | Delta vs Phase 1 |
|---|---|---|
| M1 drift | → **8-12%** | D1 + A8 recovery loops closing |
| M3 inside-polygon install | → **62-65%** | BM1 sharpens tier; B5 landmark-grounded serviceability online |
| M9 calls/pair | → **1.4-1.5** | Loop 5 visibility motivates technicians; C9 loop closes |

### End of Phase 3 (BM2 live; exploration quota operational)

| Metric | Phase 3 target | Delta vs Phase 2 |
|---|---|---|
| M1 drift | → **<5%** (target) | Full A1-A10 substrate + Loop 4 recovery compounding |
| M3 inside-polygon install | → **>65%** (target) | Full belief-model stack |
| M9 calls/pair | → **<1.3** (target) | Chain + Street View + BM2 ranking |
| M10 ANC confusion | → **<50%** | Photo/video + packet structure |
| M11 gali-stuck | → **<2%** (target) | Structured gali + BM2 downweights bad routing |

### Steady state (6 months post Phase 3)

All M1-M11 targets met; M15 held-volume conversion rising month-over-month.

---

## §8 — Risks and leading indicators

Each risk has a **leading indicator** (observable in hours/days) and a **lagging indicator** (weeks). Tripwires trigger mitigation.

| Risk | Leading (hours/days) | Lagging (weeks) | Mitigation |
|---|---|---|---|
| **R1: SR-OS queue overflows** — A14 volume >5% of MID cohort | A14 queue size per hour; CP shock fires | M2 compliance plateaus | Genie throttles A11 to route more to HIGH at the margin; escalates to SR-OS to size up capacity |
| **R2: MID verify-visit becomes a laundering channel** — bonus > HIGH install throughput value | Ratio of verify-visit bonus $ paid / install throughput $ | B7 exploration quota volume creep | B8 damping mechanics: cap bonus magnitude, throttle verify-visits per partner per week |
| **R3: Repeat-decline partner chains** — a partner in a MID hex repeatedly declines → polygon shrinks → next partner also declines → hex deserts | Hex-level decline count / week per (hex, partner_tier) | M3 plateau or regression | C4 pre-confirm consequence + B7 rotation route next ask to different-tier partner |
| **R4: Drift recovers slowly** — M1 plateaus above 10% | D1 divergence rate vs. baseline; A8 jitter-profile recovery curves | M1 lag | Tighten A11 HIGH threshold temporarily; route more to A14 |
| **R5: Structured capture adopts slowly** — A3/A4 pick rate low in some cities/segments | Per-city M2 rate weekly | Structural drift M1 stalls in lagging cities | Increase landmark set density from install-history (Round 2 of A6) |
| **R6: Partner signals degrade under gaming not covered by Track 4** | Unusual spikes in M10 one-sided confusion (customer clear, partner confused) by partner | Track 4 metrics lag | Fire early referral to Enforcement OS (E1 fast-path) |
| **R7: Finance leakage on B10 waived-cost path** | Weekly waiver volume / total verify-visit cost | P&L hit | Cap waiver volume with CP shock above threshold |

---

## §9 — Measurement cadence

Genie owns all production and reporting of these metrics. The column below names the **audience** — who reads each cadence — not a separate owner.

| Cadence | What gets reported | Audience |
|---|---|---|
| **Hourly** | A14 queue size, B3 active-exposure count, CP shock fires | Genie on-call |
| **Daily** | M2 (≥2 landmarks), A14 volume %, verify-visit outcomes (B9 tag distribution) | Genie product + Satyam |
| **Weekly** | M1 drift (installed cohort rolling 90d), M11 gali-stuck, MID ask-partner acceptance, verify-visit success rate | Genie team |
| **Monthly** | M3, M9, M10, M15 held-volume conversion, expansion-queue graduation rate | Satyam + functional leaders |
| **Per retrain** | D3 cause-code purity, BM1 / BM2 calibration drift, D4 landmark-confidence distribution shift | Genie (models sub-team) |
| **Quarterly** | Phase gate review (entry/exit criteria check), open-questions resolution | Genie + Satyam + functional leaders |

---

## §10 — Phase 4 (Integrity channel) — separate sizing note

Appendix C of v6 covers scope. Implementation plan for Phase 4 is owned jointly by Q-OS, XS-OS, Enforcement OS, and Genie, and sized on a separate timeline. This section is a pointer, not a plan.

**Capabilities:** E1-E8 (8 capabilities).
**Critical path:** E1 (fast-path contract) + E8 (bilateral contract terms) are Q1-feasible if the three OSes name contract owners this month. E2, E3, E5, E7 are Q3-Q4. E4 (booking-coord anomaly detector) lives in Enforcement OS, not Genie.
**Exit target:** M14 splitter-share gap **30.8pp → <10pp** within 6 months of E4 deployment.
**Independence:** Phase 4 does not block Phases 1-3. Phases 1-3 do not block Phase 4. Sequence either way.

---

## §11 — Open operational questions (carried from v6 §15)

Genie drives every item below. The "External sign-off" column names the non-Genie party whose approval is a hard blocker before the associated capability ships; blank means Genie-internal decision.

| # | Question | Blocks phase | Driver | External sign-off |
|---|---|---|---|---|
| 1 | Exploration quota rate + rotation mechanics (B7) | Phase 3 | Genie | Satyam |
| 2 | Verify-visit pricing + bonus magnitude (B8 damping) | Phase 1 (B8 ships in Q3) | Genie | Finance |
| 3 | Repeat-customer friction reduction cadence (A13) | Phase 3 | Genie | — |
| 4 | UAC v0 thresholds — exact rule for HIGH/MID/LOW (A11) | Phase 1 | Genie | — |
| 5 | Technician GPS ingestion cadence + privacy model (B4) | Phase 2 | Genie | Legal |
| 6 | Customer transparency copy (A12, D9) | Phase 1 | Genie | — |
| 7 | MID serviceability ops throughput ceiling | Phase 1-2 | Genie | Ops capacity sizing |
| 8 | Remediated-HIGH × MID verify-visit waiver cost absorption (B10) | Phase 1 (B10 ships in Q3) | Genie | Finance |

---

## §12 — The one-page summary

If you read nothing else:

- **42 body capabilities** across 4 groups (A/B/C/D). **8 more** in Appendix C (Track 4, cross-OS, parallel).
- **Three phases** for Tracks 1-3: Phase 1 ships the substrate in Q1+Q3; Phase 2 activates BM1 in Q4; Phase 3 activates BM2 + exploration quota. Phase 4 (integrity) is parallel and separately timed.
- **The load-bearing capabilities** for each headline metric are named in §6. If you cut one, the named metric slips.
- **Phase gates** are in §4 — do not cross them on calendar alone; cross them when the named exit criteria are met.
- **The primary NUT-linked target** is M15 (held-volume conversion). All other metrics are directional. M15 is the one that cannot be gamed by tightening the gate.
- **Headline numbers at Phase 3 end:** M1 drift 25.7% → <5%, M3 inside-polygon install 55.3% → >65%, M9 calls/pair 1.92 → <1.3, M11 gali-stuck 7.4% → <2%.
- **Risk to watch earliest:** R2 (MID verify-visit becoming a laundering channel). B8 damping mechanics are the load-bearing control.
- **Build ownership:** All 42 body capabilities are built by the Genie team. External sign-offs required: Finance (B8 bonus pool, B10 waiver absorption, A14 staffing), Legal (B4 privacy model), SR-OS (A14 queue capacity). All other decisions are Genie-internal.
