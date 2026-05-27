import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
RAW_MANUALS_DIR = ROOT_DIR / "data" / "manuals" / "raw"
PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"
CHROMA_DIR = ROOT_DIR / "data" / "chroma_db"
CHROMA_MANUALS_DIR = ROOT_DIR / "data" / "chroma_manuals"

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
