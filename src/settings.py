import os
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

# Temperature 0 keeps the answers deterministic. num_ctx limits how much text the
# model reads at once; the model's default context window is far larger than the
# RAG prompt needs and uses a lot of memory, so we cap it.
LLM_TEMPERATURE = 0.0
LLM_NUM_CTX = 8192

# How the app decides the ticket type:
#   "keyword" - use the rule-based keyword router (default)
#   "llm"     - ask the local model to classify the question
#   "hybrid"  - use the rules first, ask the model only if they find nothing
ROUTER_MODE = os.environ.get("RAG_ROUTER", "keyword").strip().lower()
if ROUTER_MODE not in {"keyword", "llm", "hybrid"}:
    ROUTER_MODE = "keyword"


def _resolve_ollama_base_url() -> str | None:
    """Resolve the Ollama base URL from env, or None to use langchain's default.

    On WSL2 the default localhost:11434 usually reaches Ollama running on Windows;
    if not, set OLLAMA_BASE_URL or OLLAMA_HOST to point at the host.
    """
    base = os.environ.get("OLLAMA_BASE_URL")
    if base:
        return base.strip()

    host = os.environ.get("OLLAMA_HOST")
    if host:
        host = host.strip()
        if host.startswith("http://") or host.startswith("https://"):
            return host
        # 0.0.0.0 is a bind address, not connectable; normalise to loopback.
        host = host.replace("0.0.0.0", "127.0.0.1")
        return f"http://{host}"

    return None


OLLAMA_BASE_URL = _resolve_ollama_base_url()
