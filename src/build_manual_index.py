from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from settings import (
    CHROMA_MANUALS_DIR,
    DEFAULT_EMBEDDING_MODEL,
    MANUALS_COLLECTION,
    RAW_MANUALS_DIR,
)


PRODUCT_NAME_MAP = {
    "samsung_galaxy": "Samsung Galaxy",
    "hp_pavilion": "HP Pavilion",
    "gopro_hero": "GoPro Hero",
    "lg_oled": "LG OLED",
    "canon_dslr": "Canon DSLR Camera",
    "dell_xps": "Dell XPS",
}


def _batched(items: list, batch_size: int):
    for start in range(0, len(items), batch_size):
        yield start, items[start : start + batch_size]


def _infer_product_name(pdf_path: Path) -> str:
    normalized_name = pdf_path.stem.lower().replace("-", "_").replace(" ", "_")
    normalized_name = normalized_name.replace("_manual", "")

    for key, product in PRODUCT_NAME_MAP.items():
        if key in normalized_name:
            return product

    return pdf_path.stem.replace("_", " ").replace("-", " ").title()


def _load_manual_pdf(pdf_path: Path) -> list[Document]:
    product = _infer_product_name(pdf_path)
    loader = PyPDFLoader(str(pdf_path))
    pages = loader.load()

    documents: list[Document] = []
    for page in pages:
        content = " ".join(page.page_content.split())
        if len(content) < 80:
            continue

        metadata = dict(page.metadata)
        metadata.update(
            {
                "source_type": "product_manual",
                "product": product,
                "manual_file": pdf_path.name,
                "page": metadata.get("page", ""),
            }
        )
        documents.append(Document(page_content=content, metadata=metadata))

    return documents


def build_manual_index(manuals_dir: Path = RAW_MANUALS_DIR, reset: bool = True) -> None:
    pdf_files = sorted(manuals_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF manuals found in {manuals_dir}. Place your downloaded manuals there first."
        )

    print(f"Found {len(pdf_files)} manual PDF files.", flush=True)
    documents: list[Document] = []

    for pdf_path in pdf_files:
        product = _infer_product_name(pdf_path)
        print(f"Loading {pdf_path.name} as product: {product}", flush=True)
        documents.extend(_load_manual_pdf(pdf_path))

    if not documents:
        raise ValueError("No usable text could be extracted from the manual PDFs.")

    print(f"Loaded {len(documents)} manual pages.", flush=True)
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)
    chunks = splitter.split_documents(documents)
    print(f"Created {len(chunks)} manual chunks.", flush=True)

    if reset and CHROMA_MANUALS_DIR.exists():
        print(f"Resetting existing manual vector database at {CHROMA_MANUALS_DIR}...", flush=True)
        shutil.rmtree(CHROMA_MANUALS_DIR)

    embeddings = OllamaEmbeddings(model=DEFAULT_EMBEDDING_MODEL)
    vectorstore = Chroma(
        collection_name=MANUALS_COLLECTION,
        persist_directory=str(CHROMA_MANUALS_DIR),
        embedding_function=embeddings,
    )

    batch_size = 100
    for start, batch in _batched(chunks, batch_size):
        vectorstore.add_documents(batch)
        done = min(start + len(batch), len(chunks))
        print(f"Indexed {done}/{len(chunks)} manual chunks...", flush=True)

    print(f"Indexed {len(pdf_files)} manuals as {len(chunks)} chunks.")
    print(f"Manual vector database: {CHROMA_MANUALS_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Chroma vector index for product manuals.")
    parser.add_argument("--manuals-dir", type=Path, default=RAW_MANUALS_DIR, help="Directory with PDF manuals.")
    parser.add_argument("--no-reset", action="store_true", help="Append to the existing manual index.")
    args = parser.parse_args()

    build_manual_index(manuals_dir=args.manuals_dir, reset=not args.no_reset)


if __name__ == "__main__":
    main()

