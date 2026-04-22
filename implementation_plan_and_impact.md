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
| **Phase 1 — Quick fixes** | +15 | ~41-42% | +1-2pp | Substrate + UI; enablement, not compounding |
| **Phase 2 — Governance + packet** | +12 | **~46%** | +4-5pp | Structured packet flowing; P2 contribution lands |
| **Phase 3 — Learning pipelines** | +12 | **~49%** | +3pp | P1 contribution closes; L5 joint target met |
| **Phase 4 — Long-poles** | +3 | ~51-52% | +2-3pp | Model-activation lift begins |

Model activation (BM1/BM2) and partner expansion stack beyond Phase 4, pushing L5 toward 55-58%. Those are **separate contracts** — see `l5_target_derivation.md` §5.

---

## §2 — Leading metric readiness

When each measurable metric becomes trackable.

| Metric | Category | Trackable after |
|---|---|---|
| L1 — Service uptime, event emissions clean | Plumbing | End of Phase 1 |
| **Verification-completion rate** (P1 Leading) | Leading | End of Phase 2 |
| **Structured-address coverage** (P2 Leading) | Leading | End of Phase 2 |
| First-call-location-reason rate (P2 L3 primary) | L3 | Trackable today; shifts post-Phase 2 |
| **Capture drift rate** (P1 L3 primary) | L3 | End of Phase 3 (needs landmark picker + UAC scorer live) |
| Verify-visit success rate (both, Learning) | Learning | End of Phase 2 |
| Technician landmark-arrival correctness (P2 Learning) | Learning | End of Phase 3 (needs A3 + technician GPS) |
| Install rate at held promise volume (L5) | L5 | Trackable today; aggregate monthly |

---

## §3 — Phase breakdown

Phasing = **complexity order**, simplest first. Tier ordering from `solution_frame_v6.md` complexity rubric. Timelines deliberately omitted.

### Phase 1 — Quick fixes (15 capabilities, Tiers 0-1)

Copy / schema / rules + single-surface UI. No cross-deps. Shippable independently.

| # | Capability |
|---|---|
| D8 | Cause-code taxonomy (GPS_TRUST / ADDRESS_RES / SPATIAL / OPERATIONAL) |
| A7 | Fallback text capture |
| A1 | Continuous GPS stream during booking |
| A4 | Gali + floor structured chat |
| A5 | Home-exterior photo / short video |
| A6 | Two-round corrective loop |
| A9 | Google Street View pull (customer-side) |
| A12 | Customer transparency UI |
| B2 | Promise / ask-partner / verify-visit / reject governance |
| C2 | Partner's own serviceable-area map (live) |
| C4 | Decline consequence shown pre-confirm |
| C6 | Street View at navigate-time (partner-side) |
| D5 | Immutable history log |
| D6 | Customer-side difficulty signal monitor |
| D9 | Customer outcome transparency loop |

**Outcome.** Substrate ready. Cause-code fidelity locked. Partner-facing UI changes visible. Ready for Leading-indicator wiring.

### Phase 2 — Governance + structured packet (12 capabilities, Tier 2)

Standard plumbing. One dep or one external integration per item.

| # | Capability |
|---|---|
| A2 | Nightly passive GPS pings |
| A14 | SR-OS queue for MID remediation |
| B1 | BM1 activation — polygon-only containment |
| B3 | Active promise exposure stock with drain on 48h-SLA-miss |
| B7 | Exploration quota with partner rotation |
| B9 | Verify-visit outcome capture |
| B10 | Remediated-HIGH × MID path tagging + waived-cost accounting |
| C1 | Structured partner notification (landmark + gali + floor) |
| C3 | Decline-zones with decay + time weighting |
| C5 | Edge-polygon ask-partner flow |
| C9 | Technician team-trail visibility to partner |
| D2 | Technician visit tracking → SLA nudge |

**Outcome.** Both Leading indicators trackable. MID-tier conversion live. P2 structured packet flowing end-to-end. L3 primary metrics begin moving.

### Phase 3 — Learning pipelines (12 capabilities, Tier 3)

Multi-input pipelines, state machines, cross-surface integrations.

| # | Capability |
|---|---|
| A3 | Landmark picker + probes |
| A8 | Per-mobile jitter-handling path with recovery |
| A10 | NER parsing for fallback text |
| A11 | UAC v0 scorer storing triplet state |
| A13 | Repeat-customer friction reduction |
| B4 | Technician / team GPS ingestion |
| B5 | Landmark-grounded serviceability |
| B8 | Paid verify-visit flow with bonus < HIGH steady-state |
| C7 | Verify-visit reward + polygon-growth visibility |
| D1 | Night-GPS divergence detector |
| D3 | Install outcome → cause-coded training loop |
| D4 | Landmark-confidence accumulation with triplet + decay |

**Outcome.** Full P1+P2 contribution lands. L5 joint target (≥49%) achievable. Feedback loops (1, 2, 4, 5) closing. Learning signals trackable.

### Phase 4 — Long-poles (3 capabilities, Tier 4)

ML model wiring, multi-feed composition, full three-way integration.

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
| SR-OS queue overflow (>5% of MID cohort) | Phase 2 | Throttle scorer HIGH threshold; escalate to SR-OS capacity |
| Verify-visit becomes a laundering channel | Phase 3 | Bonus magnitude < HIGH steady-state install throughput (damping) |
| Partner decline chains in MID hexes | Phase 2-3 | Pre-confirm consequence + rotation to different-tier partner |
| Capture drift plateaus | Phase 3 | Tighten UAC scorer HIGH threshold; route more to SR-OS |
| Finance leakage on waived-cost path | Phase 2 | Cap waiver volume; CP shock above threshold |

---

## §5 — External sign-offs required

All 42 body capabilities are built by Genie. External blockers:

- **Finance** — verify-visit bonus pool (Phase 3, B8), waiver absorption (Phase 2, B10), SR-OS queue staffing (Phase 2, A14).
- **Legal** — technician GPS privacy model (Phase 3, B4).
- **SR-OS owner** — queue operational with SLA signed off (Phase 2, A14).

---

## §6 — One-line summary

**4 phases, complexity-ordered, timelines TBD. Phase 3 end = L5 joint target (≥49%) met. Phase 4 end = model-activation contribution layered on top. Everything beyond that sits in other contracts (BM1/BM2 activation, partner expansion).**
