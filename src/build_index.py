from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from load_data import load_ticket_dataframe, tickets_to_documents
from settings import CHROMA_DIR, DEFAULT_COLLECTION, DEFAULT_EMBEDDING_MODEL


def _batched(items: list, batch_size: int):
    for start in range(0, len(items), batch_size):
        yield start, items[start : start + batch_size]


def build_index(
    csv_path: Path | None = None,
    ticket_type: str | None = None,
    product: str | None = None,
    limit: int | None = None,
    reset: bool = True,
) -> None:
    print("Loading ticket CSV...", flush=True)
    df = load_ticket_dataframe(csv_path)
    print(f"Loaded {len(df)} rows.", flush=True)

    print("Converting tickets to documents...", flush=True)
    documents = tickets_to_documents(
        df,
        ticket_type=ticket_type,
        product=product,
        limit=limit,
    )

    if not documents:
        raise ValueError("No usable ticket documents found. Check the CSV columns or filters.")

    print(f"Created {len(documents)} ticket documents.", flush=True)
    print("Splitting documents into chunks...", flush=True)
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
    chunks = splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks.", flush=True)

    if reset and CHROMA_DIR.exists():
        print(f"Resetting existing vector database at {CHROMA_DIR}...", flush=True)
        shutil.rmtree(CHROMA_DIR)

    print(f"Connecting to Ollama embedding model: {DEFAULT_EMBEDDING_MODEL}", flush=True)
    embeddings = OllamaEmbeddings(model=DEFAULT_EMBEDDING_MODEL)

    vectorstore = Chroma(
        embedding_function=embeddings,
        collection_name=DEFAULT_COLLECTION,
        persist_directory=str(CHROMA_DIR),
    )

    batch_size = 100
    for start, batch in _batched(chunks, batch_size):
        vectorstore.add_documents(batch)
        done = min(start + len(batch), len(chunks))
        print(f"Indexed {done}/{len(chunks)} chunks...", flush=True)

    print(f"Indexed {len(documents)} tickets as {len(chunks)} chunks.")
    print(f"Vector database: {CHROMA_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Chroma vector index.")
    parser.add_argument("--csv", type=Path, default=None, help="Path to a CSV file.")
    parser.add_argument("--ticket-type", default=None, help="Optional exact ticket type filter.")
    parser.add_argument("--product", default=None, help="Optional exact product filter.")
    parser.add_argument("--limit", type=int, default=None, help="Optional max number of rows.")
    parser.add_argument("--no-reset", action="store_true", help="Append to the existing Chroma index.")
    args = parser.parse_args()

    build_index(
        csv_path=args.csv,
        ticket_type=args.ticket_type,
        product=args.product,
        limit=args.limit,
        reset=not args.no_reset,
    )


if __name__ == "__main__":
    main()
