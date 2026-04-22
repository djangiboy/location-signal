# Implementation Plan & Expected Impact — Location Signal

**Drafted:** 2026-04-22
**Companion to:** `solution_frame_v6.md`, `problem_statements/*_v3.md`, `l5_target_derivation.md`, `master_story.md`
**Build team:** Genie (all 42 body capabilities). **Timelines TBD** — dependent on product/design/tech inputs. Phase gates are evidence-based, not calendar-based.

---

## §1 — Expected cumulative impact

L5 = booking → install rate at held promise volume. Baseline **40%**. Derivation: `l5_target_derivation.md`.

| After phase | Capabilities shipped | Cumulative L5 | Delta | What lands |
|---|---:|---:|---:|---|
| Baseline | 0 | **40%** | — | — |
| **Phase 1 — Substrate + capture UI** | +15 | ~41% | +1pp | Both Leading metrics trackable; MID-remediated bookings get a second chance pre-payment |
| **Phase 2 — Partner-facing + governance** | +11 | **~45%** | +4pp | Structured packet flowing; P2 contribution lands |
| **Phase 3 — Learning pipelines** | +13 | **~49%** | +4pp | P1 contribution closes; L5 joint target met |
| **Phase 4 — Long-poles** | +3 | ~51-52% | +2-3pp | Model-activation lift begins |

Model activation (BM1/BM2) and partner expansion stack beyond Phase 4, pushing L5 toward 55-58%. Those are **separate contracts** — see `l5_target_derivation.md` §5.

---

## §2 — Leading metric readiness

When each measurable metric becomes trackable.

| Metric | Category | Trackable after |
|---|---|---|
| L1 — Service uptime, event emissions clean | Plumbing | End of Phase 1 |
| **Verification-completion rate** (P1 Leading) | Leading | **End of Phase 1** |
| **Structured-address coverage** (P2 Leading) | Leading | **End of Phase 1** |
| Capture drift rate (P1 L3 primary) | L3 | End of Phase 1 + first install cohort (~1 week) |
| First-call-location-reason rate (P2 L3 primary) | L3 | Trackable today; shifts post-Phase 2 |
| Verify-visit success rate (both, Learning) | Learning | End of Phase 3 (needs B8 + B9 both live) |
| Technician landmark-arrival correctness (P2 Learning) | Learning | End of Phase 3 (needs A3 + B4 both live) |
| Install rate at held promise volume (L5) | L5 | Trackable today; aggregate monthly |

**Key point:** Phase 1 unlocks both Leading indicators and P1's L3. Functional leaders see weekly movement from Phase 1 onwards, not Phase 2.

---

## §3 — Phase breakdown

Phasing = **what unlocks visibility and customer-facing effect soonest**, with complexity rising across phases. Timelines deliberately omitted.

### Phase 1 — Substrate + capture UI (15 capabilities)

Customer-side capture flow + scoring + transparency + escape hatches. Unlocks both Leading indicators. D8 taxonomy ships first — every event emitted in Phase 1 relies on the cause-code schema being locked before writing.

| # | Capability |
|---|---|
| D8 | Cause-code taxonomy (GPS_TRUST / ADDRESS_RES / SPATIAL / OPERATIONAL) — ships **first**; schema that every closure event writes to |
| D5 | Immutable history log |
| A1 | Continuous GPS stream during booking |
| A3 | Landmark picker + probes |
| A4 | Gali + floor structured chat |
| A5 | Home-exterior photo / short video |
| A6 | Two-round corrective loop |
| A7 | Fallback text capture |
| A9 | Google Street View pull (customer-side) |
| A11 | UAC v0 scorer storing triplet state |
| A12 | Customer transparency UI |
| A14 | SR-OS queue for MID remediation |
| B2 | Promise / ask-partner / verify-visit / reject governance |
| D6 | Customer-side difficulty signal monitor |
| D9 | Customer outcome transparency loop |

**Outcome.** Capture substrate live. Verification-completion rate and structured-address coverage both trackable. Customer gets a second chance at Gate 1 MID before money is taken. Payment flow aware of HIGH/MID/LOW states.

### Phase 2 — Partner-facing + governance (11 capabilities)

Structured packet reaches partners; polygon consequences shown; governance flows operational.

| # | Capability |
|---|---|
| C1 | Structured partner notification (landmark + gali + floor) |
| C2 | Partner's own serviceable-area map (live) |
| C3 | Decline-zones with decay + time weighting |
| C4 | Decline consequence shown pre-confirm |
| C5 | Edge-polygon ask-partner flow |
| C6 | Street View at navigate-time (partner-side) |
| B3 | Active promise exposure stock with drain on 48h-SLA-miss |
| B7 | Exploration quota with partner rotation |
| B9 | Verify-visit outcome capture |
| B10 | Remediated-HIGH × MID path tagging + waived-cost accounting |
| D2 | Technician visit tracking → SLA nudge |

**Outcome.** Partner sees structured packet with polygon consequences pre-confirm. MID-tier conversion live (ask-partner + decline-with-consequences). P2 L3 (first-call-location-reason rate) begins moving. Most of P2 contribution lands here.

### Phase 3 — Learning pipelines (13 capabilities)

Multi-input feedback loops close. Full P1 contribution lands. Belief stocks compound.

| # | Capability |
|---|---|
| A2 | Nightly passive GPS pings |
| A8 | Per-mobile jitter-handling path with recovery |
| A10 | NER parsing for fallback text |
| A13 | Repeat-customer friction reduction |
| B1 | BM1 activation — polygon-only containment + tier enrichment |
| B4 | Technician / team GPS ingestion |
| B5 | Landmark-grounded serviceability |
| B8 | Paid verify-visit flow with bonus < HIGH steady-state |
| C7 | Verify-visit reward + polygon-growth visibility |
| C9 | Technician team-trail visibility to partner |
| D1 | Night-GPS divergence detector |
| D3 | Install outcome → cause-coded training loop |
| D4 | Landmark-confidence accumulation with triplet + decay |

**Outcome.** Full P1 + P2 contribution lands. Feedback loops (1, 2, 4, 5) closing. Verify-visit and landmark-arrival Learning signals trackable. L5 joint target (≥49%) achievable.

### Phase 4 — Long-poles (3 capabilities)

ML model wiring and multi-feed composition.

| # | Capability |
|---|---|
| B6 | BM2 activation (GNN ranking into production) |
| C8 | On-ground navigation assist (photos + live customer GPS + CRE call) |
| D7 | Post-install landmark validation (4-signal factorised estimate) |

**Outcome.** Model-driven lift layered on P1+P2 base. L5 progresses toward 52%+.

---

## §4 — Risks

| Risk | Surfaces at | Mitigation |
|---|---|---|
| SR-OS queue overflow (>5% of MID cohort) | Phase 1 | Throttle scorer HIGH threshold; escalate to SR-OS capacity |
| Verify-visit becomes a laundering channel | Phase 3 | Bonus magnitude < HIGH steady-state install throughput (damping) |
| Partner decline chains in MID hexes | Phase 2 | Pre-confirm consequence + rotation to different-tier partner |
| Capture drift plateaus | Phase 3 | Tighten UAC scorer HIGH threshold; route more to SR-OS |
| Finance leakage on waived-cost path | Phase 2 | Cap waiver volume; CP shock above threshold |

---

## §5 — One-line summary

**4 phases, visibility-ordered, timelines TBD. Phase 1 end = both Leading indicators live. Phase 2 end = structured packet flowing + P2 lands. Phase 3 end = L5 joint target (≥49%) met. Phase 4 end = model-activation layered on top. Beyond: BM1/BM2 activation + partner expansion (separate contracts).**
