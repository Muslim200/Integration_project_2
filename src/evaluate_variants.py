from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from rag_app import answer_question
from settings import ROOT_DIR


DEFAULT_CASES_PATH = ROOT_DIR / "data" / "evaluation" / "test_cases.json"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "docs" / "evaluatie_resultaten.md"
DEFAULT_MODES = ["tickets", "manuals", "hybrid"]


def _source_summary(docs) -> tuple[int, int, list[str]]:
    ticket_count = 0
    manual_count = 0
    labels: list[str] = []

    for doc in docs:
        metadata = doc.metadata
        if metadata.get("source_type") == "product_manual":
            manual_count += 1
            labels.append(
                f"manual:{metadata.get('product', '')}:{metadata.get('manual_file', '')}:p{metadata.get('page', '')}"
            )
        else:
            ticket_count += 1
            labels.append(
                f"ticket:{metadata.get('ticket_id', '')}:{metadata.get('product', '')}:{metadata.get('ticket_type', '')}"
            )

    return ticket_count, manual_count, labels


def _load_cases(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _select_cases(cases: list[dict], case_ids: list[str] | None, limit: int | None) -> list[dict]:
    if case_ids:
        wanted = set(case_ids)
        cases = [case for case in cases if case["id"] in wanted]
    if limit:
        cases = cases[:limit]
    return cases


def _write_report(results: list[dict], output_path: Path) -> None:
    lines = [
        "# Evaluatie RAG varianten",
        "",
        "Dit rapport vergelijkt dezelfde klantvragen in drie modi:",
        "",
        "- `tickets`: alleen historische supporttickets.",
        "- `manuals`: alleen producthandleidingen.",
        "- `hybrid`: tickets plus producthandleidingen.",
        "",
        "Gebruik de antwoorden om handmatig te beoordelen welke bron het meest nuttig is per type vraag.",
        "",
    ]

    current_case = None
    for result in results:
        case = result["case"]
        if current_case != case["id"]:
            current_case = case["id"]
            lines.extend(
                [
                    f"## {case['id']}",
                    "",
                    f"**Categorie:** {case['category']}  ",
                    f"**Taal:** {case['language']}  ",
                    "",
                    f"**Vraag:** {case['question']}",
                    "",
                    f"**Verwachting:** {case['expected']}",
                    "",
                ]
            )

        lines.extend(
            [
                f"### Mode: `{result['mode']}`",
                "",
                f"- Tijd: {result['elapsed']:.1f}s",
                f"- Ticketbronnen: {result['ticket_count']}",
                f"- Manualbronnen: {result['manual_count']}",
                f"- Bronnen: {', '.join(result['sources']) if result['sources'] else 'geen'}",
                "",
                "**Antwoord:**",
                "",
                result["answer"],
                "",
                "**Handmatige score:** ___ / 5",
                "",
                "**Opmerking:**",
                "",
                "",
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAG evaluation cases in tickets/manuals/hybrid modes.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH, help="Path to test_cases.json.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Markdown report output path.")
    parser.add_argument("--case-id", action="append", default=None, help="Run only a specific case id. Can be repeated.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N selected cases.")
    parser.add_argument("--modes", default=",".join(DEFAULT_MODES), help="Comma-separated modes: tickets,manuals,hybrid.")
    args = parser.parse_args()

    cases = _select_cases(_load_cases(args.cases), args.case_id, args.limit)
    modes = [mode.strip() for mode in args.modes.split(",") if mode.strip()]

    results: list[dict] = []
    for case in cases:
        for mode in modes:
            print(f"Running {case['id']} [{mode}]...", flush=True)
            start = time.perf_counter()
            answer, docs = answer_question(case["question"], source_mode=mode)
            elapsed = time.perf_counter() - start
            ticket_count, manual_count, sources = _source_summary(docs)
            results.append(
                {
                    "case": case,
                    "mode": mode,
                    "answer": answer,
                    "elapsed": elapsed,
                    "ticket_count": ticket_count,
                    "manual_count": manual_count,
                    "sources": sources,
                }
            )

    _write_report(results, args.output)
    print(f"Report written to: {args.output}")


if __name__ == "__main__":
    main()

