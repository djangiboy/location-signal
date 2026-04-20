"""
End-to-end smoke test on a single recording.

Picks one call from calls_manifest.csv (prefers a ~60s call so we see a
reasonable transcript), runs the full pipeline:
    download -> OpenAI Whisper translate -> Haiku classify.

Prints the transcript, classification, raw Haiku output. No CSVs written.
"""
import os, json, re, time
from pathlib import Path
import requests
import pandas as pd


HERE = Path(__file__).resolve().parent
AUDIO_DIR = HERE / "audio_cache"
AUDIO_DIR.mkdir(exist_ok=True)

MANIFEST = HERE / "investigative" / "calls_manifest.csv"

# pick a mid-length call for a meaningful transcript
df = pd.read_csv(MANIFEST).drop_duplicates("call_id")
df = df[(df["call_duration"] >= 45) & (df["call_duration"] <= 120)]
row = df.sample(1, random_state=7).iloc[0]
cid = str(row["call_id"])
url = row["recording_url"]
dur = int(row["call_duration"])
print(f"call_id    : {cid}")
print(f"duration   : {dur}s")
print(f"installed  : {row['installed']}")
print(f"decision   : {row['decision_event']} ({row['decision_reason']})")
print(f"url        : {url}")
print()

# ------ Download ------
ext = ".mp3"
for cand in (".wav", ".mp3", ".m4a", ".ogg"):
    if url.lower().split("?")[0].endswith(cand):
        ext = cand; break
local = AUDIO_DIR / f"{cid}{ext}"
EXOTEL_AUTH = (os.environ["EXOTEL_SID"], os.environ["EXOTEL_TOKEN"])
if not local.exists() or local.stat().st_size == 0:
    t0 = time.time()
    r = requests.get(url, timeout=60, stream=True, auth=EXOTEL_AUTH)
    r.raise_for_status()
    with open(local, "wb") as f:
        for chunk in r.iter_content(1 << 15):
            f.write(chunk)
    print(f"downloaded {local.stat().st_size/1024:.1f} KB in {time.time()-t0:.1f}s")
else:
    print(f"cached   {local}")
print()

# ------ Whisper translate ------
from openai import OpenAI
client = OpenAI()
t0 = time.time()
with open(local, "rb") as f:
    resp = client.audio.translations.create(
        model="whisper-1", file=f, response_format="text"
    )
text = resp if isinstance(resp, str) else getattr(resp, "text", str(resp))
text = text.strip()
print(f"WHISPER TRANSLATE ({time.time()-t0:.1f}s)")
print(f"text[:500]: {text[:500]}")
print(f"chars: {len(text)}")
print()

# ------ Haiku classify ------
from anthropic import Anthropic
ac = Anthropic()
SYSTEM = open(HERE / "classify_reasons.py").read()
sys_prompt = re.search(r'SYSTEM_PROMPT = """(.*?)"""', SYSTEM, re.S).group(1)

t0 = time.time()
msg = ac.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=250,
    system=sys_prompt,
    messages=[{"role": "user", "content": text[:4000]}],
)
raw = msg.content[0].text.strip()
print(f"HAIKU CLASSIFY ({time.time()-t0:.1f}s)")
print(f"raw:\n{raw}")
print()

# Try to parse
raw_clean = re.sub(r"^```(json)?|```$", "", raw, flags=re.M).strip()
try:
    data = json.loads(raw_clean)
    print(f"PARSED: {data}")
except Exception as e:
    print(f"PARSE FAIL: {e}")

print("\nSMOKE TEST COMPLETE")
