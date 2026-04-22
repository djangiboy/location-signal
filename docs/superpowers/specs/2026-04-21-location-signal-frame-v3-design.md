# Design Spec — Location Signal Frame v3 + Gate 0 Thinking Contracts v2

**Date:** 2026-04-21
**Author:** Maanas (via brainstorming session)
**Scope:** Three deliverables — one solution frame for Wiom functional leaders (incl. design + product heads), two Gate 0 thinking contracts for Satyam.
**Predecessors (untouched):** `solution_frame.md` (v1), `solution_frame_v2.md` (v2), `problem_statements/problem_1_location_estimation.md` (P1 v1), `problem_statements/problem_2_address_translation.md` (P2 v1).

---

## 1. Context

Two customer pain points drove the audit:
- *"Mujhe Wifi chahiye but Wiom mana kar raha hai."* (I want WiFi but Wiom is refusing me.)
- *"Mera connection aaj lagna tha, but koi lagane nahi aaya."* (My connection was supposed to be installed today, but nobody came.)

Satyam decomposed these into **two bounded problem statements** each requiring a Gate 0 thinking contract:
- **Problem 1 — Location estimation** (Point A, Wiom's promise decision)
- **Problem 2 — Address translation for CSP** (Point B, partner's decision)

After post-analysis (captured in `master_story.md`, `master_story.csv`), the existing Gate 0 docs need resubmission with sharpened framing. Maanas also wants a standalone solution frame for functional leaders (design head + product head + business ops). The word "solution" is forbidden in Satyam's Gate 0 docs — those are thinking contracts, not solution specs.

## 2. Locked decisions from brainstorming

### 2.1 P1 root cause (locked)

**Wiom commits on the customer's self-report ("yes, I am at home") without any independent channel confirming the self-report is true.** The system asks, the customer answers, Wiom takes the answer at face value. One lat/long + text address is the entire evidence basis at commit. There is no structured representation of the customer's mental model (landmark, gali, floor) at the gate — so verification has nothing to be verified against.

Single-shot capture is a **mechanism** by which trust-without-verification manifests, not the root itself.

### 2.2 Text-visibility correction (load-bearing)

Earlier framing ("partner does not see text address until click-through") is incorrect. The partner sees the text. What he doesn't see is **structure**. The address is a hurriedly-typed single-string blob; he can read it but cannot parse landmark → gali → floor without a voice call. The diagnostic shift: partner is not working without information — he is working with information he cannot use.

### 2.3 The two objectives (verbatim, canonical in solution_frame_v3 §3)

**O1:** Inputs should be verified before making a promise — the customer's self-report that he is at home is not enough evidence to commit on.

**O2:** The address the partner sees should carry the same structure the customer holds in her head — landmark, gali, floor as separate confirmed fields, not a single typed blob.

### 2.4 The landmark → gali → floor chain is behavioural, not invented

Coordination transcript analysis shows this chain is the sequence partners *already use* on voice calls to resolve addresses. Chain-engagement has a measured protective effect (+11pp install inside polygon, `master_story.md` Part C.E). Upstream capture in the same chain removes the call.

### 2.5 The shared substrate

Structured landmark/gali/floor capture at flow steps 4-6 (pre-promise) is the shared upstream element both problems rest on. **Parallel workstreams** — no "blocks" or "depends on" language between P1 and P2. Captured once, consumed by both.

### 2.6 Belief model posture

Supporting, not primary. In solution_frame_v3, appendix only. In each Gate 0, a single line under E.13 Driver Mapping noting that fixing this problem activates the existing R&D belief model.

### 2.7 System-oriented framing

Stated explicitly in solution_frame_v3 §4: this is a system build with feedback loops leading to self-correction, not a point fix. Install outcomes teach the landmark picker, partner declines teach the polygon, post-install transcripts teach the next booking's notification.

### 2.8 Nine principles (tagged by problem served)

| # | Rule | Tag |
|---|---|---|
| P1 | Verify before committing (reworded from "elicit") | P1 |
| P2 | Capture is not verification (25m gate + self-report both fail this) | P1 |
| P3 | Customer is ground truth, asked in a form that returns structure | P1 |
| P4 | Re-capture uses a different surface than initial capture | P1 |
| P5 | Partner address is structured and that structure is preserved end-to-end (absorbs earlier P10) | P2 |
| P6 | Every signal consumed has a feedback channel back to source | both |
| P7 | Cause-code fidelity (GPS_TRUST_FAILURE vs ADDRESS_RESOLUTION_FAILURE vs SPATIAL_FAILURE — never lumped) | both |
| P8 | Scoring artifacts stay internal; only facts cross membranes | both |
| P9 | Confidence is field-level, not booking-level | P2 |

### 2.9 Prioritisation matrix — impact × when

**Axes:** Impact (Quick / Medium-term) × When (Do it now / Do it in next 1 month)

**Sequencing principle:** Q3 ships alongside Q1; Q2 and Q4 follow as Q1/Q3 stabilise.

**Q1 — Do now, Quick impact (partner-side UI, visible this month):** C1, C2, C4, C7, B2.
**Q2 — In 1 month, Quick impact (UI that depends on Q1/Q3):** C3, C5, C6, D7.
**Q3 — Do now, Medium-term impact (capture substrate, value compounds):** A3, A4, A5, A6, A7, A2, B3, B5, D5.
**Q4 — In 1 month, Medium-term impact (model training, feedback loops, telemetry):** A1, A8, A9, A10, B1, B4, B6, D1, D2, D3, D4, D6, D8.

Total: 31 capabilities across four quadrants.

### 2.10 File structure (option (a) — iterate in place)

- `solution_frame_v3.md` — new
- `problem_statements/problem_1_location_estimation_v2.md` — new
- `problem_statements/problem_2_address_translation_v2.md` — new
- All predecessors preserved.

### 2.11 Cross-doc canonical sources (single source of truth)

| Element | Canonical home | Consumers |
|---|---|---|
| Two Hindi pain quotes | `CLAUDE.md` / `master_story.md` | solution_frame_v3 §1, both Gate 0 Framings |
| O1 + O2 verbatim | solution_frame_v3 §3 | Both Gate 0 B.2 |
| All numbers | `master_story.md` + `.csv` by section pointer | Never duplicated — only cited |
| Text-visibility correction sentence | Gate 0 P2 A.2.1 | solution_frame_v3 §6 quotes verbatim |
| 9 principles | solution_frame_v3 §7 | Gate 0s do not restate |

### 2.12 Gate 0 format rules

- Word "solution" forbidden in either Gate 0.
- No cross-reference to solution_frame_v3 filename from Gate 0s.
- B.2 Objective leads with **quantified shift** (template compliance), then verbal framing below.
- NUT Chain rendered inline with arrow: *"Project → Driver → NUT"* (per template example).
- Signal Validity: each sub-item (Observability / Causality / Sensitivity) opens with a one-line proof, then expands.
- "Framing" block preserved at top of each Gate 0 (additive to template, load-bearing for external readers).

## 3. solution_frame_v3 skeleton (16 sections + appendix)

| # | Section | Lines |
|---|---|---|
| §1 | The two customer voices | ~10 |
| §2 | The two decision points (Satyam frame) | ~12 |
| §3 | The two objectives (O1, O2 locked) | ~15 |
| §4 | This is a system build, not a point fix | ~10 |
| §5 | Problem 1 — what the data says | ~18 |
| §6 | Problem 2 — what the data says (with text-visibility correction loud inline) | ~22 |
| §7 | Principles of build (9) | ~25 |
| §8 | The shared substrate | ~18 |
| §9 | System flow (6 stages + control pane, ASCII) | ~50 |
| §10 | What changes (lived) — customer: Priya | ~28 |
| §11 | What changes (lived) — partner: Ramesh | ~30 |
| §12 | Capability changes (A, B, C, D tables with Impact + Quadrant columns) | ~80 |
| §13 | Prioritisation matrix (2×2 + four quadrant summaries) | ~30 |
| §14 | Why fixing only one leaves installs broken | ~12 |
| §15 | How we'll know it worked | ~14 |
| §16 | Companion files + open questions | ~15 |
| Appendix A1 | Post-install validation (4 signals, factorised) | ~12 |
| Appendix A2 | Belief-model note (3 lines) | ~5 |
| Appendix A3 | Out-of-scope handoffs to system spec | ~15 |

**Voice red flags (kill on sight):** "leverage," "enable," "unlock," "drive," "strategic," "ecosystem," "stakeholders," "journey orchestration." Any sentence over ~20 words. Any paragraph without a number, Hindi word, or concrete verb.

## 4. problem_1_location_estimation_v2 deltas from v1

- **Framing:** keep; add post-analysis sharpening note.
- **A.1:** numbers unchanged; mechanism attribution named ("customer captured GPS from not-home"); sub-population rows added.
- **A.2:** three-engine cross-check; add decline-channel-artifact confirmation.
- **B.2:** quant first (25.7% → <5%); verbal O1 framing second.
- **B.3 / B.5:** keep Capability Build / LP4.
- **B.4:** major rewrite — new root (trust-without-verification).
- **B.4.1 NEW:** "Why trust-without-verification is the root, not single-shot-capture."
- **C.6 / C.7:** L3 gains a leading execution signal row.
- **D.8:** rewrite — new leading signal is verification-completion rate.
- **D.9:** rewrite for verification-completion causality.
- **E.13:** add one-line belief-model reference.
- **E.14 NUT Chain:** convert to arrow format (template compliance).
- **F.17:** Step 2 rewrites to "build independent-verification channel."
- **G.18 Hypothesis:** rewrite around independent corroboration of self-report.
- **G.19:** add gaming risk + mitigation.
- **G.20:** verification completion rate axes.
- **Cross-link:** shared upstream element framing; no dependency language.

## 5. problem_2_address_translation_v2 deltas from v1

- **Framing:** three-party table row for Partner rewritten (text is visible, structure is the gap).
- **A.1:** numbers unchanged; call out 41% never-reach-gali finding.
- **A.2:** drop any residual "unseen by partner" framing.
- **A.2.1 NEW:** the text-visibility correction subsection (canonical source of the correction sentence).
- **B.2:** quant first (1.92 → <1.3; 7.4% gali-stuck → <2%; ~10% cant-find → <5%); verbal O2 framing second.
- **B.3 / B.5:** keep Capability Build / LP4.
- **B.4:** contributing factor #2 rewritten (unstructured blob, not hidden).
- **B.4.1 NEW:** "The landmark → gali → floor chain is behaviourally established" — cites coordination transcripts.
- **C.6 / C.7:** intact; C.7 adds baseline source for "pairs installing with ≤1 call."
- **D.8:** tighten leading signal definition (first-call-resolved rate).
- **D.9:** rewrite causality for structured-address propagation.
- **E.13:** add one-line belief-model-2 reference.
- **E.14 NUT Chain:** convert to arrow format.
- **F.17:** Step 1 feeds both customer-side picker AND partner-side framing.
- **F.Decision-point (Option A vs B):** **major rewrite** — Option B is default (not a choice); A is degraded fallback only.
- **G.18 Hypothesis:** rewrite around structured-vs-unstructured framing, not visible-vs-hidden.
- **G.19:** update partner-adoption risk mitigation with D8 post-install validation.
- **Cross-link:** shared upstream element framing.

## 6. Success criteria

- Functional leader can read solution_frame_v3 alongside master_story.md and explain both problems back in their own words.
- Design head / product head reading solution_frame_v3 can see what they will build (capability tables + Impact/Quadrant tags) and what order (matrix).
- Satyam reading either Gate 0 can find: clear problem, measurable signal, testable hypothesis (template FINAL RULE) — without ever seeing the word "solution."
- No number appears in any of the three docs that isn't sourced to master_story.md by section pointer.
- Text-visibility correction lands identically in solution_frame_v3 §6 and Gate 0 P2 A.2.1 (verbatim quote, one canonical sentence).

## 7. Out of scope for this spec

- System architect document (future work; Appendix A1-A3 seed it).
- Engineering mechanics (thresholds, decay formulas, retry logic, write-contracts, API shapes).
- Option B UX design specifics (user-flow completion thresholds, structured capture form design).
- Gaming-detection feature engineering.
- Cross-engine integration spec (how Promise Maker talks to D&A OS, CL OS).

## 8. Self-review (post-write)

- [x] No TBDs or placeholders in the three deliverables.
- [x] O1, O2 appear verbatim in solution_frame_v3 §3 and as framing lines in Gate 0 B.2.
- [x] Text-visibility correction sentence is identical across solution_frame_v3 §6 and Gate 0 P2 A.2.1.
- [x] Word "solution" appears zero times in either Gate 0 (grep-checked).
- [x] Both Gate 0 B.2 sections lead with quantified shift per template.
- [x] NUT chains rendered inline with arrows in both Gate 0s.
- [x] All numbers cite master_story.md by section pointer.
- [x] 31 capabilities tagged across 4 quadrants; tally reconciles.
- [x] Nine principles appear once in solution_frame_v3 §7; zero restatement elsewhere.
