"""Objective before/after routing accuracy on INDEPENDENTLY-generated cases.

The point of this script is to remove the author from the measurement loop.

Ground truth is NOT my assertion. Each test question was:
  1. written by an independent local model (qwen3 / gemma3 / llama3.1) shown only
     Expertum's plain business categories -- never the router's vocabulary
     (generate_eval_cases.py), and
  2. classified by a DIFFERENT independent model shown only the neutral
     five-bucket taxonomy (label_eval_cases.py).

The blind label is the ground truth; a case is "agreed" when the generator's
intent and the blind label coincide -- two independent models concurring.

Three versions of the routing function `_detect_ticket_type` are compared,
loaded with the LangChain/Chroma stack stubbed so the pure rule layer runs:

    before  = eb3c12f^   (pre-fix routing)
    pr2     = eb3c12f    (the PR-2 routing/normalisation expansion)
    v2      = working tree (small follow-up: malfunction / order-stop / refund verbs)

DEV vs HELD-OUT discipline: the first generated set was inspected to design the
v2 rules, so v2's number on that set is optimistic. Pass the *held-out* set
(generated after the rules were written, never inspected) for v2's honest,
generalisation number.

    python3 src/eval_routing_accuracy.py --labeled docs/eval_generated_labeled.json --tag heldout
    python3 src/eval_routing_accuracy.py --labeled docs/eval_generated_labeled_dev.json --tag dev

Honest residual limitation: the questions are model-generated synthetic Dutch,
not logged Belgian customer tickets. What is removed is *author* bias in both
the phrasings and the labels; what remains is that this is synthetic data.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]

BEFORE_REF = "eb3c12f^"
PR2_REF = "eb3c12f"

# Modules the rule layer imports at module load but does not need to ROUTE.
_STUBS = [
    "langchain_chroma", "langchain_core", "langchain_core.output_parsers",
    "langchain_core.prompts", "langchain_ollama", "chromadb", "load_data", "settings",
]


def _exec_detector(src: str, tag: str, func: str):
    saved = {m: sys.modules.get(m) for m in _STUBS}
    for m in _STUBS:
        sys.modules[m] = MagicMock()
    try:
        ns: dict = {"__name__": f"ragapp_{tag}"}
        exec(compile(src, f"rag_app@{tag}", "exec"), ns)
        return ns[func]
    finally:
        for m, v in saved.items():
            if v is None:
                sys.modules.pop(m, None)
            else:
                sys.modules[m] = v


def load_detector(ref: str, func: str = "_detect_ticket_type"):
    """Exec src/rag_app.py as it existed at git `ref`, with the heavy stack stubbed."""
    src = subprocess.check_output(["git", "show", f"{ref}:src/rag_app.py"], text=True)
    return _exec_detector(src, ref.replace("^", "_p"), func)


def load_detector_working(func: str = "_detect_ticket_type"):
    """Exec the current working-tree src/rag_app.py (the v2 candidate)."""
    src = (ROOT / "src" / "rag_app.py").read_text(encoding="utf-8")
    return _exec_detector(src, "working", func)


VERSIONS = ["before", "pr2", "v2"]


def run(labeled_path: Path, tag: str) -> None:
    if not labeled_path.exists():
        sys.exit(f"missing {labeled_path} -- run src/label_eval_cases.py first")

    cases = json.loads(labeled_path.read_text(encoding="utf-8"))
    det = {
        "before": load_detector(BEFORE_REF),
        "pr2": load_detector(PR2_REF),
        "v2": load_detector_working(),
    }

    labeled = [c for c in cases if c.get("blind_label")]
    agreed = [c for c in labeled if c.get("agree")]
    for c in labeled:
        c["_truth"] = c["blind_label"]
        for v in VERSIONS:
            c[f"_{v}"] = det[v](c["question"])

    def acc(subset, v):
        return sum(1 for c in subset if c[f"_{v}"] == c["_truth"]), len(subset)

    full = {v: acc(labeled, v) for v in VERSIONS}
    agr = {v: acc(agreed, v) for v in VERSIONS}

    per_bucket: dict = defaultdict(lambda: {"n": 0, **{v: 0 for v in VERSIONS}})
    for c in agreed:
        b = per_bucket[c["_truth"]]
        b["n"] += 1
        for v in VERSIONS:
            b[v] += int(c[f"_{v}"] == c["_truth"])

    # Movement of the shipped routing (v2) vs the original (before), agreed set.
    toward = [c for c in agreed if c["_before"] != c["_truth"] and c["_v2"] == c["_truth"]]
    away = [c for c in agreed if c["_before"] == c["_truth"] and c["_v2"] != c["_truth"]]

    out_json = ROOT / "docs" / f"eval_routing_accuracy{'_' + tag if tag else ''}.json"
    out_md = ROOT / "docs" / f"eval_routing_accuracy{'_' + tag if tag else ''}.md"

    result = {
        "tag": tag, "source": labeled_path.name,
        "refs": {"before": BEFORE_REF, "pr2": PR2_REF, "v2": "working-tree"},
        "total_cases": len(cases), "labeled_cases": len(labeled), "agreed_cases": len(agreed),
        "full_set_accuracy": full, "agreed_set_accuracy": agr,
        "per_bucket_agreed": {k: dict(v) for k, v in per_bucket.items()},
        "v2_vs_before_moved_toward_truth": len(toward),
        "v2_vs_before_moved_away_from_truth": len(away),
    }
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    def pct(hn):
        h, n = hn
        return f"{100 * h / n:.0f}% ({h}/{n})" if n else "n/a"

    set_label = {"heldout": "vastgehouden (niet ingezien)", "dev": "ontwikkel (ingezien)"}.get(tag, tag or "set")
    lines = [
        "# Objectieve routing-accuratesse (onafhankelijk gegenereerd)",
        "",
        f"Testset: **{set_label}** -- bron `{labeled_path.name}`.",
        "",
        "De testvragen zijn door onafhankelijke modellen geschreven (qwen3 / gemma3 / "
        "llama3.1) en door een *ander* model blind geclassificeerd. De grondwaarheid is "
        "dat blinde label, niet mijn oordeel. De routingfunctie `_detect_ticket_type` is "
        "rechtstreeks uit git geladen op drie versies.",
        "",
        f"- before = `{BEFORE_REF}` (routing vóór de fix)",
        f"- pr2 = `{PR2_REF}` (de eerste routing/normalisatie-uitbreiding)",
        "- v2 = werkkopie (kleine vervolgfix: defect-/geluid-, stopzetten- en terug-verba)",
        "",
        f"Gegenereerde cases: **{len(cases)}**. Met blind label: **{len(labeled)}**. "
        f"Cross-model overeenstemming: **{len(agreed)}** -- de sterkste grondwaarheid.",
        "",
        "## Accuratesse tegenover de onafhankelijke grondwaarheid",
        "",
        "| set | before | pr2 | v2 |",
        "|-----|--------|-----|----|",
        f"| overeenstemmende set | {pct(agr['before'])} | {pct(agr['pr2'])} | **{pct(agr['v2'])}** |",
        f"| volledige gelabelde set | {pct(full['before'])} | {pct(full['pr2'])} | **{pct(full['v2'])}** |",
        "",
        "## Per categorie (overeenstemmende set, grondwaarheid-bucket)",
        "",
        "| categorie | n | before | pr2 | v2 |",
        "|-----------|---|--------|-----|----|",
    ]
    for b in sorted(per_bucket):
        v = per_bucket[b]
        lines.append(
            f"| {b} | {v['n']} | {pct((v['before'], v['n']))} | "
            f"{pct((v['pr2'], v['n']))} | {pct((v['v2'], v['n']))} |"
        )
    lines += [
        "",
        f"v2 tegenover before (overeenstemmende set): **{len(toward)}** beslissingen naar "
        f"correct, **{len(away)}** naar fout.",
        "",
        "## Eerlijke restbeperking",
        "",
        "De vragen zijn modelgegenereerd synthetisch Nederlands, geen gelogde Belgische "
        "klanttickets. Wat hier is weggenomen, is *auteurs*-bias in zowel de formuleringen "
        "als de labels; wat blijft, is dat dit synthetische data is. De v2-regels zijn "
        "ontworpen op de ontwikkelset; het eerlijke generalisatiecijfer is dat op de "
        "vastgehouden set.",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"[{tag or 'set'}] cases {len(cases)} | labeled {len(labeled)} | agreed {len(agreed)}")
    for scope, d in (("agreed", agr), ("full", full)):
        print(f"  {scope:6s}  before {pct(d['before'])}  pr2 {pct(d['pr2'])}  v2 {pct(d['v2'])}")
    print(f"  v2 vs before: toward {len(toward)}, away {len(away)}")
    print(f"  wrote {out_json.relative_to(ROOT)} and {out_md.relative_to(ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--labeled", default="docs/eval_generated_labeled.json")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    run(Path(a.labeled) if Path(a.labeled).is_absolute() else ROOT / a.labeled, a.tag)
