import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
RAW_MANUALS_DIR = ROOT_DIR / "data" / "manuals" / "raw"
PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"
# Vector-store locations. Both default to the canonical dirs under data/ but are
# env-overridable so a second embedding model (e.g. bge-m3, 1024-dim) can be
# indexed side-by-side without clobbering the nomic index for A/B evaluation.
CHROMA_DIR = Path(os.environ.get("RAG_CHROMA_DIR", str(ROOT_DIR / "data" / "chroma_db")))
CHROMA_MANUALS_DIR = Path(os.environ.get("RAG_CHROMA_MANUALS_DIR", str(ROOT_DIR / "data" / "chroma_manuals")))

DEFAULT_LLM_MODEL = os.environ.get("RAG_LLM_MODEL", "llama3.1:8b")
DEFAULT_EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "nomic-embed-text")
DEFAULT_COLLECTION = "support_tickets"
MANUALS_COLLECTION = "product_manuals"


def _resolve_ollama_base_url() -> str | None:
    """Resolve the Ollama server URL from the environment.

    Returns None when nothing is configured, so langchain-ollama falls back to
    its own default (http://localhost:11434). On WSL2 with mirrored networking
    that default already reaches an Ollama server running on Windows. When WSL2
    uses NAT networking instead, set OLLAMA_BASE_URL (or OLLAMA_HOST) to the
    Windows host, e.g. http://<windows-ip>:11434.
    """
    base = os.environ.get("OLLAMA_BASE_URL")
    if base:
        return base.strip()

    host = os.environ.get("OLLAMA_HOST")
    if host:
        host = host.strip()
        if host.startswith("http://") or host.startswith("https://"):
            return host
        # OLLAMA_HOST is usually host:port (e.g. "0.0.0.0:11434"); a 0.0.0.0
        # bind address is not connectable, so normalise it to loopback.
        host = host.replace("0.0.0.0", "127.0.0.1")
        return f"http://{host}"

    return None


OLLAMA_BASE_URL = _resolve_ollama_base_url()

# llama3.1:8b advertises a 128k-token context window. Letting Ollama allocate
# the KV cache for the full window needs ~20 GiB of RAM and OOMs on a typical
# 16-32 GiB machine. Bound the context explicitly so the model fits; 8192 is
# ample for the RAG prompt (system + retrieved docs + question + answer).
LLM_NUM_CTX = int(os.environ.get("RAG_LLM_NUM_CTX", "8192"))
LLM_TEMPERATURE = float(os.environ.get("RAG_LLM_TEMPERATURE", "0.0"))

# Ticket-type routing strategy (RAG_ROUTER), picking the Chroma metadata filter:
# keyword = rule layer (default, deterministic); llm = zero-shot classification;
# hybrid = keyword then llm. See _route_ticket_type for the dispatch.
ROUTER_MODE = os.environ.get("RAG_ROUTER", "keyword").strip().lower()
if ROUTER_MODE not in {"keyword", "llm", "hybrid"}:
    ROUTER_MODE = "keyword"

# Optional keep_alive override for all Ollama clients. None = Ollama's own
# default (models stay resident ~5m). Set RAG_OLLAMA_KEEP_ALIVE=0 to unload a
# model immediately after each call. Useful on small GPUs (e.g. 8 GB) where the
# LLM and a separate embedding model cannot be resident simultaneously: forcing
# immediate unload prevents VRAM overcommit (which can corrupt embeddings to NaN
# under memory pressure). Has no effect on answer content, only on residency.
OLLAMA_KEEP_ALIVE = os.environ.get("RAG_OLLAMA_KEEP_ALIVE") or None
