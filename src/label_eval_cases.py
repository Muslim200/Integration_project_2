"""Assign an INDEPENDENT blind bucket label to each generated case.

Ground truth for routing accuracy must not be my assertion. So each generated
question is classified by a model DIFFERENT from the one that wrote it, shown
only the neutral five-bucket taxonomy and not the generator's intended bucket.
A case's ground truth is accepted only when the generator's intent and the blind
label AGREE -- cross-model agreement, reported alongside the disagreement rate.

    qwen3-written   -> labelled by llama3.1
    gemma3-written  -> labelled by qwen3
    llama3.1-written-> labelled by qwen3   (gemma3 never labels: too weak)

Input:  docs/eval_generated_cases.json
Output: docs/eval_generated_labeled.json  (+ blind_label, label_model, agree)
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "docs" / "eval_generated_cases.json"
OUT = ROOT / "docs" / "eval_generated_labeled.json"
BASE = "http://localhost:11434"

BUCKETS = {
    "Technical issue": "het product werkt niet, is defect of doet iets onverwachts",
    "Refund request": "de klant wil betaald geld terugkrijgen",
    "Billing inquiry": "een vraag of probleem over betaling, bedrag of afrekening",
    "Cancellation request": "de klant wil een bestelling stopzetten of annuleren",
    "Product inquiry": "een vraag over de levering van een bestelling of over een product zelf",
}
VALID = set(BUCKETS)

LABELER_FOR = {"qwen3:8b": "llama3.1:8b", "gemma3:1b": "qwen3:8b", "llama3.1:8b": "qwen3:8b"}

TAXONOMY = "\n".join(f'- "{b}": {d}' for b, d in BUCKETS.items())
SYSTEM = (
    "Je bent een classificatiemodel voor klantenservice. Je deelt elke klantvraag "
    "in bij precies een van deze categorieen:\n" + TAXONOMY +
    "\nAntwoord uitsluitend met de exacte categorienaam."
)


def _chat(model: str, system: str, user: str, timeout: int = 150) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False, "format": "json", "options": {"temperature": 0.0},
    }
    if "qwen3" in model:
        payload["think"] = False
    req = urllib.request.Request(BASE + "/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read()).get("message", {}).get("content", "")


def _norm(bucket: str) -> str | None:
    b = (bucket or "").strip().lower()
    for v in VALID:
        if v.lower() == b or v.lower() in b:
            return v
    return None


def _label_chunk(model: str, items: list[dict]) -> dict[str, str]:
    listing = "\n".join(f'{i+1}. {it["question"]}' for i, it in enumerate(items))
    user = (
        "Classificeer elke vraag. Antwoord ALLEEN met JSON: "
        '{"labels":[{"n":1,"categorie":"..."}, ...]}.\n\n' + listing
    )
    raw = re.sub(r"<think>.*?</think>", "", _chat(model, SYSTEM, user), flags=re.DOTALL)
    out: dict[str, str] = {}
    try:
        obj = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        for row in obj.get("labels", []):
            n = int(row.get("n", 0)) - 1
            b = _norm(row.get("categorie") or row.get("bucket") or "")
            if 0 <= n < len(items) and b:
                out[items[n]["id"]] = b
    except Exception:
        pass
    return out


def run(chunk: int = 8) -> None:
    cases = json.loads(IN.read_text(encoding="utf-8"))
    by_labeler: dict[str, list[dict]] = {}
    for c in cases:
        by_labeler.setdefault(LABELER_FOR[c["gen_model"]], []).append(c)

    labels: dict[str, str] = {}
    for model, items in by_labeler.items():
        got = 0
        for i in range(0, len(items), chunk):
            part = items[i:i + chunk]
            res = _label_chunk(model, part)
            # retry any item the batch missed, one at a time
            for it in part:
                if it["id"] not in res:
                    res.update(_label_chunk(model, [it]))
            labels.update(res)
            got += sum(1 for it in part if it["id"] in res)
            print(f"  {model:14s} labelled {got}/{len(items)}", flush=True)

    n_agree = 0
    for c in cases:
        c["label_model"] = LABELER_FOR[c["gen_model"]]
        c["blind_label"] = labels.get(c["id"])
        c["agree"] = bool(c["blind_label"] == c["intended_bucket"])
        n_agree += c["agree"]

    OUT.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    labelled = sum(1 for c in cases if c["blind_label"])
    print(f"\nWrote {OUT}")
    print(f"labelled: {labelled}/{len(cases)} | cross-model agreement: {n_agree}/{labelled} "
          f"({100*n_agree/max(labelled,1):.0f}%)")


if __name__ == "__main__":
    run()
