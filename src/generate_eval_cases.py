"""Generate Dutch support-question test cases using INDEPENDENT local models.

Bias-reduction: the test phrasings are written by qwen3 / gemma3 / llama3.1 via
Ollama, NOT by the author. The generation prompt names only Expertum's business
categories in plain language -- it never reveals the router's vocabulary or the
specific gaps the fix targeted -- so the cases are independent of the
implementation under test. ALL generated cases are kept (no cherry-picking).

Output: docs/eval_generated_cases.json -> list of
    {id, question, gen_model, intended_bucket}

The 'intended_bucket' is the generator's target (mapped to the app's five
buckets). A separate labelling pass (label_eval_cases.py) assigns an independent
blind label so ground truth comes from cross-model agreement, not assertion.

Routing note: delivery/levering questions are requested under the Product
inquiry bucket because the application routes delivery questions there (see the
delivery_en_missing_package publisher case + _detect_ticket_type).
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "eval_generated_cases.json"
BASE = "http://localhost:11434"

GENERATORS = ["qwen3:8b", "gemma3:1b", "llama3.1:8b"]

# Plain business meaning ONLY. No router vocabulary, no "avoid keyword X" hints.
CATEGORIES = {
    "Technical issue": "het gekochte product werkt niet goed, is defect of doet iets onverwachts",
    "Refund request": "de klant wil het betaalde aankoopbedrag terugkrijgen",
    "Billing inquiry": "een vraag of probleem over de betaling, het bedrag of de afrekening van een aankoop",
    "Cancellation request": "de klant wil een geplaatste bestelling stopzetten",
    "Product inquiry": "een vraag over de levering van een bestelling of over een product zelf",
}

SYSTEM = (
    "Je bent een klant van Expertum, een Belgische webshop voor elektronica "
    "(laptops, televisies, camera's, smartphones, spelconsoles). "
    "Je schrijft realistische klantvragen in het Nederlands, zoals echte Belgische "
    "klanten ze zouden typen. Varieer de stijl: soms kort, soms uitgebreider, "
    "soms formeel, soms informeel. Schrijf telkens over een concreet product."
)


def _chat(model: str, system: str, user: str, timeout: int = 120) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.9},
    }
    if "qwen3" in model:  # qwen3 is a reasoning model; disable thinking for speed + clean JSON
        payload["think"] = False
    req = urllib.request.Request(
        BASE + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.loads(r.read())
    return body.get("message", {}).get("content", "")


def _parse_questions(raw: str) -> list[str]:
    """Tolerantly pull a list of question strings out of a model response."""
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    # try whole-string JSON first
    for candidate in (raw, raw[raw.find("{"):raw.rfind("}") + 1], raw[raw.find("["):raw.rfind("]") + 1]):
        try:
            obj = json.loads(candidate)
        except Exception:
            continue
        if isinstance(obj, dict):
            for v in obj.values():
                if isinstance(v, list):
                    obj = v
                    break
        if isinstance(obj, list):
            out = [str(x).strip() for x in obj if isinstance(x, (str,)) and str(x).strip()]
            if out:
                return out
    return []


def run(per_category: int) -> None:
    cases: list[dict] = []
    seen: set[str] = set()
    cid = 0
    for model in GENERATORS:
        for bucket, meaning in CATEGORIES.items():
            user = (
                f"Geef precies {per_category} verschillende klantvragen voor deze situatie: "
                f"{meaning}. Antwoord ALLEEN met JSON in de vorm "
                f'{{"vragen": ["vraag 1", "vraag 2", ...]}}. Geen uitleg.'
            )
            try:
                raw = _chat(model, SYSTEM, user)
                qs = _parse_questions(raw)
            except Exception as e:  # noqa: BLE001
                print(f"  !! {model} / {bucket}: {e}", flush=True)
                qs = []
            kept = 0
            for q in qs:
                key = q.lower().strip()
                if len(q) < 12 or key in seen:
                    continue
                seen.add(key)
                cases.append({
                    "id": f"gen_{cid:03d}",
                    "question": q,
                    "gen_model": model,
                    "intended_bucket": bucket,
                })
                cid += 1
                kept += 1
            print(f"  {model:14s} {bucket:22s} -> {kept} kept", flush=True)
            time.sleep(0.3)

    OUT.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {len(cases)} generated cases to {OUT}")
    # quick per-bucket / per-model tally
    from collections import Counter
    print("by intended bucket:", dict(Counter(c["intended_bucket"] for c in cases)))
    print("by generator:", dict(Counter(c["gen_model"] for c in cases)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-category", type=int, default=6)
    run(ap.parse_args().per_category)
