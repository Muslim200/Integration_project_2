from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
RAW_MANUALS_DIR = ROOT_DIR / "data" / "manuals" / "raw"
PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"
CHROMA_DIR = ROOT_DIR / "data" / "chroma_db"
CHROMA_MANUALS_DIR = ROOT_DIR / "data" / "chroma_manuals"

DEFAULT_LLM_MODEL = "llama3.1:8b"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_COLLECTION = "support_tickets"
MANUALS_COLLECTION = "product_manuals"
