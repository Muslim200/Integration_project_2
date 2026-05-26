from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from langchain_core.documents import Document

from settings import RAW_DATA_DIR


COLUMN_ALIASES = {
    "ticket_id": ["ticket id", "ticket_id", "id"],
    "product": ["product purchased", "product", "product category", "category"],
    "ticket_type": ["ticket type", "type", "issue type"],
    "subject": ["ticket subject", "subject", "title"],
    "description": ["ticket description", "description", "customer complaint", "question"],
    "resolution": ["resolution", "answer", "solution", "response"],
    "priority": ["ticket priority", "priority"],
    "status": ["ticket status", "status"],
}


def find_csv_file(data_dir: Path = RAW_DATA_DIR) -> Path:
    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV file found in {data_dir}. Download the Kaggle dataset and place the CSV there."
        )
    return csv_files[0]


def _normalize_column_name(name: str) -> str:
    return name.strip().lower().replace("-", " ").replace("_", " ")


def _resolve_columns(df: pd.DataFrame) -> dict[str, str | None]:
    normalized = {_normalize_column_name(column): column for column in df.columns}
    resolved: dict[str, str | None] = {}

    for canonical, aliases in COLUMN_ALIASES.items():
        resolved[canonical] = None
        for alias in aliases:
            if alias in normalized:
                resolved[canonical] = normalized[alias]
                break

    return resolved


def _value(row: pd.Series, column: str | None) -> str:
    if not column:
        return ""
    value = row.get(column, "")
    if pd.isna(value):
        return ""
    return str(value).strip()


def _clean_text(text: str, product: str = "") -> str:
    text = text.replace("{product_purchased}", product or "the product")
    text = text.replace("{product}", product or "the product")
    return " ".join(text.split())


def load_ticket_dataframe(csv_path: Path | None = None) -> pd.DataFrame:
    csv_path = csv_path or find_csv_file()
    df = pd.read_csv(csv_path)
    df = df.dropna(how="all").reset_index(drop=True)
    return df


def tickets_to_documents(
    df: pd.DataFrame,
    ticket_type: str | None = None,
    product: str | None = None,
    limit: int | None = None,
) -> list[Document]:
    columns = _resolve_columns(df)

    if ticket_type and columns["ticket_type"]:
        df = df[df[columns["ticket_type"]].astype(str).str.lower() == ticket_type.lower()]

    if product and columns["product"]:
        df = df[df[columns["product"]].astype(str).str.lower() == product.lower()]

    if limit:
        df = df.head(limit)

    documents: list[Document] = []

    for index, row in df.iterrows():
        subject = _value(row, columns["subject"])
        product_name = _value(row, columns["product"])
        description = _clean_text(_value(row, columns["description"]), product_name)
        resolution = _clean_text(_value(row, columns["resolution"]), product_name)
        subject = _clean_text(subject, product_name)

        if not description and not subject:
            continue

        ticket_id = _value(row, columns["ticket_id"]) or str(index)
        issue_type = _value(row, columns["ticket_type"])
        priority = _value(row, columns["priority"])
        status = _value(row, columns["status"])

        page_content = "\n".join(
            part
            for part in [
                f"Ticket ID: {ticket_id}",
                f"Product: {product_name}" if product_name else "",
                f"Ticket type: {issue_type}" if issue_type else "",
                f"Subject: {subject}" if subject else "",
                f"Customer problem: {description}" if description else "",
                f"Previous resolution: {resolution}" if resolution else "",
            ]
            if part
        )

        documents.append(
            Document(
                page_content=page_content,
                metadata={
                    "ticket_id": ticket_id,
                    "product": product_name,
                    "ticket_type": issue_type,
                    "priority": priority,
                    "status": status,
                },
            )
        )

    return documents


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the support ticket dataset.")
    parser.add_argument("--csv", type=Path, default=None, help="Path to a CSV file.")
    parser.add_argument("--ticket-type", default=None, help="Optional exact ticket type filter.")
    parser.add_argument("--product", default=None, help="Optional exact product filter.")
    parser.add_argument("--limit", type=int, default=5, help="Number of documents to preview.")
    args = parser.parse_args()

    df = load_ticket_dataframe(args.csv)
    documents = tickets_to_documents(
        df,
        ticket_type=args.ticket_type,
        product=args.product,
        limit=args.limit,
    )

    print(f"Rows in CSV: {len(df)}")
    print(f"Documents after filtering: {len(documents)}")
    print()

    for document in documents[: args.limit]:
        print(document.page_content)
        print("-" * 80)


if __name__ == "__main__":
    main()
