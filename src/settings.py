import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
RAW_MANUALS_DIR = ROOT_DIR / "data" / "manuals" / "raw"
PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"
# Env-overridable so an alternate embedding index can be built beside the default.
CHROMA_DIR = Path(os.environ.get("RAG_CHROMA_DIR", str(ROOT_DIR / "data" / "chroma_db")))
CHROMA_MANUALS_DIR = Path(os.environ.get("RAG_CHROMA_MANUALS_DIR", str(ROOT_DIR / "data" / "chroma_manuals")))

DEFAULT_LLM_MODEL = os.environ.get("RAG_LLM_MODEL", "llama3.1:8b")
DEFAULT_EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "nomic-embed-text")
DEFAULT_COLLECTION = "support_tickets"
MANUALS_COLLECTION = "product_manuals"


def _resolve_ollama_base_url() -> str | None:
    """Resolve the Ollama base URL from env, or None to use langchain's default.

    On WSL2 with mirrored networking the default localhost:11434 reaches Ollama
    on Windows; with NAT networking set OLLAMA_BASE_URL/OLLAMA_HOST to the host.
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

# Cap the context window: llama3.1:8b's 128k default KV cache needs ~20 GiB and
# OOMs; 8192 fits and is ample for the RAG prompt.
LLM_NUM_CTX = int(os.environ.get("RAG_LLM_NUM_CTX", "8192"))
LLM_TEMPERATURE = float(os.environ.get("RAG_LLM_TEMPERATURE", "0.0"))

# Ticket-type routing strategy (RAG_ROUTER), picking the Chroma metadata filter:
# keyword = rule layer (default, deterministic); llm = zero-shot classification;
# hybrid = keyword then llm. See _route_ticket_type for the dispatch.
ROUTER_MODE = os.environ.get("RAG_ROUTER", "keyword").strip().lower()
if ROUTER_MODE not in {"keyword", "llm", "hybrid"}:
    ROUTER_MODE = "keyword"

# keep_alive override for Ollama clients (None = default ~5m residency). Set
# RAG_OLLAMA_KEEP_ALIVE=0 on small GPUs to unload between calls and avoid VRAM
# overcommit, which can corrupt embeddings to NaN under memory pressure.
OLLAMA_KEEP_ALIVE = os.environ.get("RAG_OLLAMA_KEEP_ALIVE") or None
