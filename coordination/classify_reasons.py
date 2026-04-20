"""
Classify Transcripts into Reason Buckets
==========================================
Input : investigative/transcripts.csv
        investigative/calls_manifest.csv
Output: investigative/transcripts_classified.csv
        investigative/reason_distribution.csv
        investigative/reason_vs_decision_crosstab.csv

TWO-LAYER CLASSIFIER:
  Layer 1 -- REGEX PRE-PASS
    Cheap deterministic flags on the English transcript for the two pre-
    specified categories (address_not_clear, address_too_far). Patterns
    ported/extended from ../location_accuracy/unified_decile_analysis.py.

  Layer 2 -- LLM OPEN-ENDED (Claude via Anthropic API)
    For each transcript, asks: "classify into one of {address_not_clear,
    address_too_far, customer_not_reachable, rescheduling, price_query,
    installation_concern, other}; also return a free-text one-line summary."
    Forces a JSON response for auditability.

The LLM tags override regex for the primary_reason column. The regex flags
are kept as separate binary columns so the two signals can be compared
(did LLM catch what regex missed and vice versa).

CROSS-VALIDATION vs location_accuracy:
  calls_manifest carries decision_event + decision_reason from task_logs.
  The final crosstab (primary_reason x decision_reason regex bucket) tells us
  whether the decline-reason dropdown agrees with what partners actually said
  on the call. Disagreement = dismissal-leak evidence (partner clicked
  'address not clear' but the call shows something else, or vice versa).

Run from: analyses/data/partner_customer_calls/
    python classify_reasons.py --llm-backend claude
    python classify_reasons.py --llm-backend none   # regex-only
"""

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd


HERE    = Path(__file__).resolve().parent
OUT_DIR = HERE / "investigative"

MANIFEST    = OUT_DIR / "calls_manifest.csv"
TRANSCRIPTS = OUT_DIR / "transcripts.csv"
CLASSIFIED  = OUT_DIR / "transcripts_classified.csv"
DIST_CSV    = OUT_DIR / "reason_distribution.csv"
XTAB_CSV    = OUT_DIR / "reason_vs_decision_crosstab.csv"


# ============================================================================
# LAYER 1 — REGEX PATTERNS (applied to translated English transcript)
# Regex is a weak pre-pass. Use it to FLAG co-occurrence, not to decide primary
# reason — that's the LLM's job. These columns are kept for audit: "did the
# LLM catch what regex saw and vice versa?"
# ============================================================================
ADDRESS_NOT_CLEAR_RX = re.compile(
    r"\b(address (is )?not clear|can(no|')t (find|locate|understand) (the |your )?address|"
    r"don'?t understand (the )?address|where (is|exactly|are you|do you live)|"
    r"which (lane|gali|street|block|sector|floor|building)|"
    r"send (me )?(your )?(correct )?location|share (your )?location|"
    r"location (is )?not clear|address unclear|"
    r"landmark|exact location|house number|flat number|pin(code)?|drop (me )?a (pin|location))",
    re.IGNORECASE,
)

ADDRESS_TOO_FAR_RX = re.compile(
    r"\b(too far|very far|far away|far from|out of (my )?(area|zone|coverage|range)|"
    r"outside (my )?(area|coverage|service)|not in (my )?area|not serviceable|"
    r"no (coverage|network|line|cable|fiber|fibre) (there|here|in that area)|"
    r"cable ?(reach|length) (not|won'?t)|wire (short|not enough|doesn'?t reach)|"
    r"\d+\s*(meter|metre|m |km|kilometer) (or more )?away|"
    r"can(no|')t (install|provide|give) .*(because|due to) .*(distance|far|coverage))",
    re.IGNORECASE,
)

ADDRESS_WRONG_RX = re.compile(
    r"\b(wrong address|shifted|moved|changed (the |my )?address|different address|"
    r"new address|old address|that'?s not (where|my) (I|place))",
    re.IGNORECASE,
)

BUILDING_ACCESS_RX = re.compile(
    r"\b(security (guard|not allowing|blocking)|society|gate pass|lift|"
    r"gated|compound|permission from|landlord|owner not (at home|allowing)|"
    r"rwa|housing society)",
    re.IGNORECASE,
)

CUSTOMER_POSTPONE_RX = re.compile(
    r"\b(come tomorrow|next (day|week)|after \d+ (days?|hours?)|later|"
    r"not (at home|available) (today|right now|now)|weekend|sunday|"
    r"after (diwali|holi|eid|festival|salary|my (husband|wife|father) returns)|"
    r"i'?m at (work|office|outside))",
    re.IGNORECASE,
)

PARTNER_POSTPONE_RX = re.compile(
    r"\b(i'?ll come (tomorrow|later|in \d+)|can'?t come today|will come (next|day)|"
    r"busy today|raining|no time today)",
    re.IGNORECASE,
)

CUSTOMER_CANCEL_RX = re.compile(
    r"\b(cancel|don'?t want|not interested|refund|changed my mind|no need)",
    re.IGNORECASE,
)

COMPETITOR_CONSENT_RX = re.compile(
    r"\b(airtel|jio|bsnl|tata play|excitel|my (husband|wife|father|mother|son|daughter|landlord)|"
    r"ask my|decide later|think about it|compare)",
    re.IGNORECASE,
)

PRICE_PLAN_RX = re.compile(
    r"\b(price|cost|charge|plan|monthly|rupees|\brs\.?\b|₹|how much|mbps|speed|validity|recharge)",
    re.IGNORECASE,
)

PAYMENT_ISSUE_RX = re.compile(
    r"\b(can'?t pay|unable to pay|pay later|deposit|refund|security (money|deposit)|"
    r"payment (issue|problem|not working|failed))",
    re.IGNORECASE,
)

DUPLICATE_CONN_RX = re.compile(
    r"\b(already (have|installed|connected)|existing connection|"
    r"another (connection|wifi)|already a (customer|wiom user))",
    re.IGNORECASE,
)

ROUTER_STOCK_RX = re.compile(
    r"\b(no router|router (not |un)available|stock|inventory|out of stock|"
    r"device not (available|ready))",
    re.IGNORECASE,
)

WRONG_CUSTOMER_RX = re.compile(
    r"\b(wrong number|didn'?t book|never booked|i don'?t know|"
    r"who are you|which company)",
    re.IGNORECASE,
)

CUSTOMER_UNREACHABLE_RX = re.compile(
    r"\b(not (answering|picking up|responding)|no response|"
    r"number (is )?(off|switched off|busy|unreachable)|call (me )?back|will call later)",
    re.IGNORECASE,
)

# Map the regex to label keys — keep order matching LABELS for deterministic fallback.
REGEX_BY_LABEL = {
    "address_not_clear":                ADDRESS_NOT_CLEAR_RX,
    "address_too_far":                  ADDRESS_TOO_FAR_RX,
    "address_wrong":                    ADDRESS_WRONG_RX,
    "building_access_issue":            BUILDING_ACCESS_RX,
    "customer_postpone":                CUSTOMER_POSTPONE_RX,
    "partner_postpone":                 PARTNER_POSTPONE_RX,
    "customer_cancelling":              CUSTOMER_CANCEL_RX,
    "competitor_or_consent":            COMPETITOR_CONSENT_RX,
    "price_or_plan_query":              PRICE_PLAN_RX,
    "payment_issue":                    PAYMENT_ISSUE_RX,
    "duplicate_or_existing_connection": DUPLICATE_CONN_RX,
    "router_or_stock_issue":            ROUTER_STOCK_RX,
    "wrong_customer":                   WRONG_CUSTOMER_RX,
    "customer_unreachable":             CUSTOMER_UNREACHABLE_RX,
}


LABELS = [
    # A. Location resolution
    "address_not_clear",
    "address_too_far",
    "address_wrong",
    "building_access_issue",
    # B. Scheduling
    "customer_postpone",
    "partner_postpone",
    "slot_confirmation",
    # C. Post-visit recovery
    "partner_reached_cant_find",
    "partner_no_show",
    # D. Customer decision
    "customer_cancelling",
    "competitor_or_consent",
    # E. Commercial
    "price_or_plan_query",
    "payment_issue",
    # F. Technical / site
    "install_site_technical",
    "router_or_stock_issue",
    "duplicate_or_existing_connection",
    # G. Communication / noise / fallback
    "wrong_customer",
    "customer_unreachable",
    "noise_or_empty",
    "other",
]


# ============================================================================
# LAYER 2 — LLM CLASSIFICATION (Claude)
# ============================================================================
SYSTEM_PROMPT = """You are a Wiom call-reason classifier.

INPUT
  An English transcript of a phone call between a Wiom INSTALLATION PARTNER
  (field agent) and a CUSTOMER who booked residential broadband. Transcripts
  may be partial, noisy, or code-mixed residue from Hindi->English translation.
  The call happens BETWEEN booking and install (post-ASSIGNED, pre-OTP_VERIFIED).

PRODUCT VOCABULARY (do NOT mis-classify as address/location content)
  The product being installed is the "Wiom Net box" — a WiFi router. In Hindi
  partner dialects this often sounds like "BOM box", "bomb box", "vyom box",
  "wiom box", "WI OM box", "boom box", "room box", "router", "ruter", "rooter"
  (Whisper transliteration artifacts). When the transcript mentions any of
  these, the speaker is naming the ROUTER/PRODUCT, not a place, person, or
  landmark. Do not let product mentions influence the reason label.

TASK
  Return the single PRIMARY reason the call occurred / ended in its current
  state, plus a one-line summary.

LABELS (pick exactly one)

  Location resolution:
  - address_not_clear             partner cannot parse/find address; asks for
                                  landmark, gali, block, sector, exact directions,
                                  OR asks customer to share WhatsApp/GPS location
  - address_too_far               partner says address is out of coverage, too
                                  far, no cable/fiber reach, serviceability fail
  - address_wrong                 customer is at a different address than booked
                                  (shifted, moved, gave wrong address initially)
  - building_access_issue         society/security blocking entry, lift access,
                                  gated compound, floor permission

  Scheduling:
  - customer_postpone             customer wants to shift slot to later (work,
                                  guest, festival, weekend-only, salary-day)
  - partner_postpone              partner defers (weather, workload, other job,
                                  will-come-tomorrow without a customer reason)
  - slot_confirmation             routine slot coordination with no friction:
                                  "I'll come at 3pm", "ok see you then"

  Post-visit recovery:
  - partner_reached_cant_find     partner is at/near the location and can't
                                  find the customer, call is navigational
  - partner_no_show               customer says partner didn't come when promised,
                                  asking to reschedule or complaining

  Customer decision:
  - customer_cancelling           customer wants to cancel the booking / install,
                                  refund request, no-longer-interested
  - competitor_or_consent         customer asks for time to compare with
                                  Airtel/Jio/etc., OR needs spouse/family/landlord
                                  consent before proceeding

  Commercial:
  - price_or_plan_query           question about plan, speed, monthly cost,
                                  recharge, discount, plan change
  - payment_issue                 cannot pay now / asking deferral / payment
                                  method issue / security deposit refund confusion

  Technical / site:
  - install_site_technical        power point, wiring route inside home, router
                                  mount position, speed-test disputes
  - router_or_stock_issue         partner has no router to install, inventory
                                  issue on partner side
  - duplicate_or_existing_connection
                                  customer already has a connection installed
                                  (Wiom or other), duplicate booking

  Communication / noise / fallback:
  - wrong_customer                dialed number doesn't belong to the booking
                                  customer, or customer denies booking
  - customer_unreachable          no answer, number off, voicemail, call rang
                                  but no conversation happened
  - noise_or_empty                recording is unintelligible, empty, or just
                                  noise / crosstalk / silence
  - other                         genuinely doesn't fit any above

DISAMBIGUATION RULES (applied in order)

  1. noise_or_empty ONLY applies when the transcript is literally:
       - just greetings ("Hello? Hello? Yes?") with no other words, OR
       - just the Exotel recording notice ("This call is now being recorded")
         with no other content, OR
       - unintelligible garble.
     If there is ANY intelligible content — a name, a location, a time, a
     plan, "call back", "busy", "wrong number" — DO NOT use noise_or_empty.
     Classify by the content instead.

  2. customer_unreachable covers short calls where the customer's ONLY
     message is "I'll call you back / call me later / busy right now" with
     no other content. If there is ANY substantive exchange (address,
     slot, price, anything) beyond "call back," classify by that content.

  3. customer_postpone vs competitor_or_consent:
       - "Let me ask my husband/wife/father" + "I'll think about it / decide
         later / call back" in the context of COMMITTING TO THE PURCHASE
         -> competitor_or_consent
       - "My husband/wife is at work, come when he returns" or "after Sunday,
         after festival, after salary" -> customer_postpone
     Family-member mentions alone are not enough for competitor_or_consent.
     competitor_or_consent needs an explicit decision-pending signal or
     explicit ISP comparison (Airtel/Jio/BSNL).

  4. address_not_clear vs partner_reached_cant_find:
       - Partner still trying to leave / plan route, asking for address,
         landmark, pin, location share -> address_not_clear
       - Partner IS at/near the site ("I'm standing in the lane", "I'm here
         outside", "which house is this", "come outside I'm here") ->
         partner_reached_cant_find. This is navigational, partner is on-site.

  5. partner asks for landmark/pin drop -> address_not_clear, not slot_confirmation

  6. partner says "I'll come tomorrow" with no customer-side reason ->
     partner_postpone. "Customer says I'm at work, come tomorrow" ->
     customer_postpone.

  7. address_too_far is a HARD serviceability statement ("out of my area",
     "cable doesn't reach", "outside coverage"), not a soft distance mention.

  8. slot_confirmation = brief coordination, timing-only, with no friction
     and no repeated address clarification. "Ok I'll come at 3" + "ok" = slot.

FEW-SHOT EXAMPLES

  Ex1 transcript: "This call is now being recorded. This call is now being recorded."
  {"primary_reason":"noise_or_empty","secondary_reason":"","summary":"Only the Exotel recording notice."}

  Ex2 transcript: "Hello? Hello? I'll call you back in a while. Okay."
  {"primary_reason":"customer_unreachable","secondary_reason":"","summary":"Customer defers the call, no content exchanged."}

  Ex3 transcript: "Hello. Where? At Kamsul Ghat. Where is Kamsul Ghat? Near the transformer. Twin Tower. Ok I'll come there."
  {"primary_reason":"address_not_clear","secondary_reason":"slot_confirmation","summary":"Partner repeatedly asks for the location; customer gives landmarks."}

  Ex4 transcript: "Hello. I'm standing in the lane, which house is this? Come outside and tell me."
  {"primary_reason":"partner_reached_cant_find","secondary_reason":"","summary":"Partner is on-site and cannot identify the correct house."}

  Ex5 transcript: "Hello, I'm at work today, please come tomorrow when I'm home."
  {"primary_reason":"customer_postpone","secondary_reason":"","summary":"Customer is at work, asks to shift to next day."}

  Ex6 transcript: "Let me compare with Airtel first, I'll decide and call you back tomorrow."
  {"primary_reason":"competitor_or_consent","secondary_reason":"","summary":"Customer wants to compare with competitor before committing."}

  Ex7 transcript: "Yes, tell me the number you booked from. 7017... OTP must have come, see."
  {"primary_reason":"wrong_customer","secondary_reason":"","summary":"Partner is verifying booking identity; the person denies or cannot confirm."}

OUTPUT
  Return ONLY a JSON object. No markdown fencing. No preamble.

  {"primary_reason": "<label>",
   "secondary_reason": "<label or empty string>",
   "summary": "<one line, <=25 words>"}
"""


def _classify_one(client, text):
    """Single classification call. Returns (primary, secondary, summary)."""
    if not isinstance(text, str) or len(text.strip()) < 5:
        return ("noise_or_empty", "", "")
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=250,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": text[:4000]}],
        )
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        primary = data.get("primary_reason", "other")
        secondary = data.get("secondary_reason", "") or ""
        if primary not in LABELS:
            primary = "other"
        if secondary and secondary not in LABELS:
            secondary = ""
        return (primary, secondary, data.get("summary", "")[:200])
    except Exception as e:
        return ("other", "", f"ERR:{str(e)[:100]}")


def classify_with_claude(transcripts, workers=5):
    """Classify each transcript via Haiku. Thread-pool for concurrent API
    calls (5 workers keeps well below Anthropic rate limits)."""
    from anthropic import Anthropic
    client = Anthropic()

    results = [None] * len(transcripts)
    done = 0
    t0 = time.time()

    def work(i, t):
        return i, _classify_one(client, t)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, i, t) for i, t in enumerate(transcripts)]
        for fut in futures:
            i, tup = fut.result()
            results[i] = tup
            done += 1
            if done % 50 == 0 or done == len(transcripts):
                rate = done / (time.time() - t0)
                eta  = (len(transcripts) - done) / rate if rate > 0 else 0
                print(f"  classified {done}/{len(transcripts)} — {rate:.1f}/s — ETA {eta/60:.1f} min")
    return results


# ============================================================================
# DECISION_REASON BUCKETING (for crosstab vs transcript classification)
# ============================================================================
# Imported from ../location_accuracy so buckets match the existing analysis.
AREA_DECLINE_PATTERN = (
    r"feasible|area|ariya|coverage|zone|outside|serviceab|network|signal|"
    r"line|cable|fiber|fibre|range|reach|far|meters or more away"
)
ADDRESS_DROPDOWN_RX = re.compile(r"understand the address|पता समझ", re.IGNORECASE)
AREA_DROPDOWN_RX   = re.compile(AREA_DECLINE_PATTERN, re.IGNORECASE)


def bucket_decision_reason(reason):
    if not isinstance(reason, str) or not reason.strip():
        return "no_reason"
    if ADDRESS_DROPDOWN_RX.search(reason):
        return "dropdown_address_not_clear"
    if AREA_DROPDOWN_RX.search(reason):
        return "dropdown_area_decline"
    return "other_reason"


# ============================================================================
# MAIN
# ============================================================================
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--llm-backend", default="claude",
                   choices=["claude", "none"])
    p.add_argument("--workers", type=int, default=5,
                   help="parallel API workers (Haiku)")
    args = p.parse_args()

    assert TRANSCRIPTS.exists(), f"Missing {TRANSCRIPTS} — run transcribe_calls.py"
    assert MANIFEST.exists(),   f"Missing {MANIFEST} — run pull_calls.py"

    tx = pd.read_csv(TRANSCRIPTS)
    mn = pd.read_csv(MANIFEST)
    print(f"TRANSCRIPTS: {len(tx):,}  MANIFEST: {len(mn):,}")

    df = tx.merge(
        mn[["call_id", "mobile", "partner_id", "decision_event",
            "decision_reason", "installed", "call_duration"]],
        on="call_id",
        how="left",
    )
    df["call_id"] = df["call_id"].astype(str)

    # --- Layer 1: regex flags (one column per label that has a regex) ---
    txts = df["transcript"].fillna("").astype(str)
    for label, rx in REGEX_BY_LABEL.items():
        df[f"rx_{label}"] = txts.str.contains(rx).astype(int)

    # --- Layer 2: LLM ---
    if args.llm_backend == "claude":
        print(f"CLASSIFYING via Claude Haiku — {args.workers} workers ...")
        t0 = time.time()
        results = classify_with_claude(df["transcript"].tolist(),
                                       workers=args.workers)
        df["primary_reason"]   = [r[0] for r in results]
        df["secondary_reason"] = [r[1] for r in results]
        df["llm_summary"]      = [r[2] for r in results]
        print(f"  LLM done in {time.time() - t0:.1f}s")
    else:
        def pick(row):
            for lbl in REGEX_BY_LABEL:
                if row.get(f"rx_{lbl}"):
                    return lbl
            if not row["transcript"] or len(str(row["transcript"])) < 10:
                return "noise_or_empty"
            return "other"
        df["primary_reason"]   = df.apply(pick, axis=1)
        df["secondary_reason"] = ""
        df["llm_summary"]      = ""

    df["decision_reason_bucket"] = df["decision_reason"].apply(bucket_decision_reason)

    df.to_csv(CLASSIFIED, index=False)
    print(f"\nWROTE {CLASSIFIED} ({len(df):,} rows)")

    # --- Distribution ---
    dist = df["primary_reason"].value_counts().rename("count").to_frame()
    dist["pct"] = (dist["count"] / len(df) * 100).round(2)
    dist.to_csv(DIST_CSV)
    print(f"\nPRIMARY_REASON DISTRIBUTION:")
    print(dist.to_string())

    # --- Crosstab: transcript-classified reason vs task_logs decision_reason ---
    xtab = pd.crosstab(df["primary_reason"], df["decision_reason_bucket"],
                       margins=True, margins_name="total")
    xtab.to_csv(XTAB_CSV)
    print(f"\nCROSSTAB primary_reason x decision_reason_bucket:")
    print(xtab.to_string())
    print(f"\nWROTE {XTAB_CSV}")

    # --- Headline: among NOT-installed calls, what fraction have transcript-
    #     evidence of address_not_clear? Compare to dropdown rate.
    not_installed = df[df["installed"] == 0]
    if len(not_installed) > 0:
        pct_transcript_addr = (not_installed["primary_reason"] == "address_not_clear").mean() * 100
        pct_dropdown_addr   = (not_installed["decision_reason_bucket"] == "dropdown_address_not_clear").mean() * 100
        pct_transcript_far  = (not_installed["primary_reason"] == "address_too_far").mean() * 100
        pct_dropdown_far    = (not_installed["decision_reason_bucket"] == "dropdown_area_decline").mean() * 100
        print(f"\nNOT-INSTALLED CALLS (n={len(not_installed):,})")
        print(f"  address_not_clear : transcript {pct_transcript_addr:.1f}% vs dropdown {pct_dropdown_addr:.1f}%")
        print(f"  address_too_far   : transcript {pct_transcript_far:.1f}% vs dropdown {pct_dropdown_far:.1f}%")


if __name__ == "__main__":
    main()
