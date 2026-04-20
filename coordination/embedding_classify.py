"""
Semantic classification via OpenAI embeddings
==============================================
Parallel signal to the Haiku classifier. Given the 20 first-principles reasons,
we write a "prototype description" per reason (what that reason SOUNDS like on
a call), embed all transcripts and all prototypes, and score cosine similarity.

Outputs:
    investigative/embedding_reason_scores.csv
        One row per transcript, one column per reason = cosine similarity.
        Plus columns: emb_top1_reason, emb_top1_score,
                     emb_top2_reason, emb_top2_score,
                     emb_top3_reason, emb_top3_score.

    investigative/embedding_vs_haiku.csv
        Disagreement audit: transcripts where emb_top1 != haiku_primary
        AND emb_top1_score > threshold. Columns:
          call_id, haiku_primary, emb_top1, emb_top1_score, transcript, summary.

Why both signals:
  - Haiku is a single-label discrete classifier (forced to pick one). On short
    or ambiguous calls it over-uses 'other' / 'noise_or_empty'.
  - Embeddings give a CONTINUOUS similarity to every reason. Catches calls
    where two reasons co-occur, and calls where Haiku was too conservative.
  - Disagreement between them is the interesting cohort — flags transcripts
    for manual inspection or prompt iteration.

Run from: analyses/data/partner_customer_calls/
    python embedding_classify.py
"""

import os
import time
from pathlib import Path
import numpy as np
import pandas as pd


HERE        = Path(__file__).resolve().parent
OUT_DIR     = HERE / "investigative"
TRANSCRIPTS = OUT_DIR / "transcripts.csv"
CLASSIFIED  = OUT_DIR / "transcripts_classified.csv"

EMB_SCORES  = OUT_DIR / "embedding_reason_scores.csv"
EMB_VS_HAIKU = OUT_DIR / "embedding_vs_haiku.csv"

EMBED_MODEL = "text-embedding-3-small"   # 1536 dims, $0.02/1M tok
BATCH       = 64


# ============================================================================
# REASON PROTOTYPES — one paragraph per label describing what that reason
# SOUNDS LIKE on a partner-customer call. Embeddings of these define the
# "reason centroids" against which transcripts are scored.
# ============================================================================
REASON_PROTOTYPES = {
    "address_not_clear": (
        "The partner cannot understand, find, or locate the customer's address. "
        "The partner asks repeatedly for a landmark, gali, lane, street, block, "
        "sector, floor, building, pincode, or for the customer to share their "
        "WhatsApp location or drop a pin. The partner is confused about where "
        "to go. 'Where exactly is that? Near which landmark? Send me the "
        "location. Which lane? Which floor? Send pin drop.'"
    ),
    "address_too_far": (
        "The partner says the customer's address is too far, outside coverage, "
        "not serviceable, no cable reach, no fiber, out of the service area. "
        "This is a hard distance / serviceability block, not navigation "
        "confusion. 'That area is out of my coverage. Cable doesn't reach "
        "there. It's too far from my setup. Not serviceable from here.'"
    ),
    "address_wrong": (
        "The customer is at a different address than what was booked. They "
        "have shifted, moved, changed address, or gave the wrong address "
        "originally. 'I've shifted to a new place. The address you have is "
        "old. I'm not at that address anymore.'"
    ),
    "building_access_issue": (
        "Society, security guard, gate, lift, landlord, or RWA blocking "
        "entry. Gated compound requires permission, owner not available to "
        "authorize, tenant needs landlord consent. 'Security isn't letting "
        "me in. Society gate pass needed. Landlord should approve first.'"
    ),
    "customer_postpone": (
        "The customer wants to shift the installation to a later time or "
        "date for a scheduling reason. Common drivers: being at work or "
        "office today, having guests, weekend-only availability, waiting "
        "for a family member to be home (husband, wife, parent), after "
        "salary day, after festival. 'Come tomorrow, come next week, I'm "
        "at office today, come on Sunday, when my husband is back.' This "
        "is about WHEN, not whether to buy — the purchase intent is intact."
    ),
    "partner_postpone": (
        "The partner is shifting the slot, not the customer. Partner says "
        "they will come tomorrow or later, cannot come today, busy with "
        "another install, weather blocking them, their team is not available. "
        "'I'll come tomorrow, can't make it today, I'm busy right now.'"
    ),
    "slot_confirmation": (
        "A routine slot coordination call with no real friction. Partner "
        "says they'll come at a specific time, customer acknowledges. Brief "
        "exchange of timing, 'ok see you then'. No address confusion, no "
        "postponement, no commercial issue. Just confirming when the visit "
        "happens."
    ),
    "partner_reached_cant_find": (
        "The partner has already reached the location or is near it, but "
        "can't find the customer or the exact house. Call is navigational — "
        "partner is on-site looking around. 'I'm here outside, come down. "
        "I'm near the gate, where are you? Come outside, I'm standing at "
        "the corner. I can't see your house, which direction?'"
    ),
    "partner_no_show": (
        "The customer says the partner was supposed to come but didn't "
        "show up. Customer is complaining about the missed appointment "
        "and asking when the partner will come or demanding a reschedule. "
        "'You didn't come yesterday. Nobody came for installation. It's "
        "been three days, where are you?'"
    ),
    "customer_cancelling": (
        "The customer wants to cancel the booking / installation entirely. "
        "They are asking for a refund, saying they no longer want the "
        "service, have changed their mind. 'Please cancel. Refund my money. "
        "I don't need it anymore. Not interested anymore.'"
    ),
    "competitor_or_consent": (
        "The customer wants more time before committing to the purchase, "
        "either to compare with another ISP (Airtel, Jio, BSNL, Excitel, "
        "Reliance) or because they need a DECISION-AUTHORITY to approve "
        "first — 'let me think about it,' 'I need to decide,' 'I'll call "
        "you back after comparing.' This is about hesitation on the "
        "PURCHASE DECISION, not scheduling. Mere mentions of family members "
        "in a timing context ('my husband is at work, come tomorrow') "
        "are NOT this category — those are postponement."
    ),
    "price_or_plan_query": (
        "The call is primarily about plan, price, speed, monthly cost, "
        "validity, recharge, or requesting a different plan. Commercial "
        "topics dominate, not the install logistics. 'How much per month? "
        "What's the speed? Can I get a cheaper plan? When does it expire?'"
    ),
    "payment_issue": (
        "The customer cannot pay right now, is asking to defer payment, "
        "has a payment method problem, or is confused about the security "
        "deposit or refund. 'I can't pay today, I'll pay later, online "
        "payment failed, about the deposit refund.'"
    ),
    "install_site_technical": (
        "Technical concern about the install site inside the home — "
        "power socket location, wiring route, where to mount the router, "
        "speed not matching promise. NOT about the address. 'Where will "
        "you put the router? There's no socket there. The wiring needs "
        "to go through this wall.'"
    ),
    "router_or_stock_issue": (
        "The partner does not have a router to install — inventory or "
        "stock problem on the partner side. 'No router available right "
        "now. Out of stock. Device will come next week.'"
    ),
    "duplicate_or_existing_connection": (
        "The customer already has a connection installed, either from Wiom "
        "or another provider. Duplicate booking, already a customer, already "
        "has wifi. 'I already have Wiom. We already have a connection. "
        "Someone else installed it yesterday.'"
    ),
    "wrong_customer": (
        "The dialed number does not belong to the customer who booked, or "
        "the person answering denies booking. Wrong number. 'I didn't book "
        "anything. Who are you? Which company? I don't know what you're "
        "talking about.'"
    ),
    "customer_unreachable": (
        "No real conversation content. Customer's ONLY message is to defer "
        "the call: 'I'll call you back later, busy right now, call me after "
        "some time.' The call ends quickly with no substantive information "
        "exchanged. Nothing said about address, slot, payment, or product."
    ),
    "noise_or_empty": (
        "The recording contains literally no intelligible content — only "
        "'Hello? Hello? Hello?' repetitions, the Exotel recording notice "
        "'This call is now being recorded' by itself, silence, background "
        "noise, or garbled speech. No names, places, times, or information "
        "of any kind are exchanged."
    ),
    "other": (
        "The call content does not fit any specific operational reason "
        "and is neither a pure slot confirmation nor a navigational call."
    ),
}


def embed_batch(client, texts):
    """Embed a list of strings, return (N, D) float32 matrix."""
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return np.array([d.embedding for d in resp.data], dtype=np.float32)


def cosine_matrix(A, B):
    """(N, D) x (M, D) -> (N, M) cosine similarity."""
    An = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-12)
    Bn = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-12)
    return An @ Bn.T


def main():
    assert TRANSCRIPTS.exists(), "Run transcribe_calls.py first"
    from openai import OpenAI
    client = OpenAI()

    # Load transcripts — dedupe by call_id (one embedding per unique recording)
    tx = pd.read_csv(TRANSCRIPTS).drop_duplicates("call_id").reset_index(drop=True)
    tx["transcript"] = tx["transcript"].fillna("").astype(str)
    # Embed empty/very short transcripts would fail — replace with a placeholder
    tx["_emb_text"] = tx["transcript"].apply(lambda s: s if len(s.strip()) >= 3 else "empty silence")
    print(f"TRANSCRIPTS to embed: {len(tx):,}")

    # ------ Embed reason prototypes ------
    labels = list(REASON_PROTOTYPES.keys())
    proto_texts = [REASON_PROTOTYPES[l] for l in labels]
    print(f"EMBEDDING {len(proto_texts)} reason prototypes ...")
    proto_mat = embed_batch(client, proto_texts)
    print(f"  proto_mat shape: {proto_mat.shape}")

    # ------ Embed transcripts in batches ------
    t0 = time.time()
    all_vecs = []
    texts = tx["_emb_text"].tolist()
    for i in range(0, len(texts), BATCH):
        batch = texts[i:i + BATCH]
        vec = embed_batch(client, batch)
        all_vecs.append(vec)
        if (i // BATCH) % 5 == 0:
            print(f"  embedded {i + len(batch)}/{len(texts)} ({time.time() - t0:.1f}s)")
    tx_mat = np.vstack(all_vecs)
    print(f"EMBEDDED {len(tx_mat):,} transcripts in {time.time() - t0:.1f}s")
    print(f"  tx_mat shape: {tx_mat.shape}")

    # ------ Score ------
    sims = cosine_matrix(tx_mat, proto_mat)
    out = pd.DataFrame(sims, columns=[f"sim_{l}" for l in labels])
    out.insert(0, "call_id", tx["call_id"].astype(str).values)

    # top 3
    order = np.argsort(-sims, axis=1)
    top1 = order[:, 0]; top2 = order[:, 1]; top3 = order[:, 2]
    out["emb_top1_reason"] = [labels[i] for i in top1]
    out["emb_top1_score"]  = sims[np.arange(len(tx)), top1]
    out["emb_top2_reason"] = [labels[i] for i in top2]
    out["emb_top2_score"]  = sims[np.arange(len(tx)), top2]
    out["emb_top3_reason"] = [labels[i] for i in top3]
    out["emb_top3_score"]  = sims[np.arange(len(tx)), top3]

    out.to_csv(EMB_SCORES, index=False)
    print(f"\nWROTE {EMB_SCORES}  ({len(out):,} rows)")

    print("\nEMB top1 distribution:")
    print(out["emb_top1_reason"].value_counts().to_string())

    # ------ Cross-check with Haiku ------
    if CLASSIFIED.exists():
        cl = pd.read_csv(CLASSIFIED).drop_duplicates("call_id")
        cl["call_id"] = cl["call_id"].astype(str)
        out["call_id"] = out["call_id"].astype(str)
        m = out.merge(
            cl[["call_id", "transcript", "primary_reason", "llm_summary"]],
            on="call_id", how="inner")
        m = m.rename(columns={"primary_reason": "haiku_primary"})

        # Agreement rate
        agree = (m["emb_top1_reason"] == m["haiku_primary"]).mean()
        print(f"\nHAIKU ↔ EMB_TOP1 AGREEMENT: {agree * 100:.1f}%")

        # Disagreement matrix
        xt = pd.crosstab(m["haiku_primary"], m["emb_top1_reason"])
        xt.to_csv(OUT_DIR / "embedding_vs_haiku_crosstab.csv")
        print("\nAgreement crosstab (rows=Haiku, cols=Embedding top1):")
        print(xt.to_string())

        # Flag disagreements with high embedding confidence
        dis = m[(m["emb_top1_reason"] != m["haiku_primary"]) &
                (m["emb_top1_score"] >= 0.35)].copy()
        dis = dis.sort_values("emb_top1_score", ascending=False)
        dis[["call_id", "haiku_primary", "emb_top1_reason", "emb_top1_score",
             "emb_top2_reason", "emb_top2_score",
             "llm_summary", "transcript"]].to_csv(EMB_VS_HAIKU, index=False)
        print(f"\nDISAGREEMENTS (emb_top1 != haiku, score >= 0.35): {len(dis):,}")
        print(f"WROTE {EMB_VS_HAIKU}")


if __name__ == "__main__":
    main()
