"""
tools/rag.py — RAG tools: rag_ingest, rag_search.

Uses a persistent ChromaDB collection stored in DATA_DIR/chroma/.
Documents are split into 300-char chunks with 50-char overlap.
Embeddings: all-MiniLM-L6-v2 (SentenceTransformers).
"""
import os

import requests
from bs4 import BeautifulSoup

from app.cache import cache
from app.config import DATA_DIR

_rag_collection  = None
_rag_doc_counter = [0]


def _get_rag_collection():
    global _rag_collection
    if _rag_collection is None:
        import chromadb
        from chromadb.utils import embedding_functions

        data_dir = os.path.join(DATA_DIR, "chroma")
        os.makedirs(data_dir, exist_ok=True)

        client   = chromadb.PersistentClient(path=data_dir)
        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        _rag_collection = client.get_or_create_collection(
            name="boozo_rag", embedding_function=embed_fn
        )
    return _rag_collection


def rag_ingest(source: str) -> str:
    """
    Ingest text or a URL into the persistent RAG knowledge base.
    URLs are scraped and Redis-cached for 24 h to avoid re-fetching.
    """
    try:
        if source.startswith("http://") or source.startswith("https://"):
            text = cache.get_url(source)
            if text is None:
                headers = {"User-Agent": "Mozilla/5.0"}
                resp    = requests.get(source, headers=headers, timeout=10)
                resp.raise_for_status()
                soup    = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer"]):
                    tag.decompose()
                text = soup.get_text(separator=" ", strip=True)
                cache.set_url(source, text)
            label = source
        else:
            text  = source
            label = f"text-{_rag_doc_counter[0]}"

        chunk_size, overlap = 300, 50
        chunks, start = [], 0
        while start < len(text):
            chunks.append(text[start: start + chunk_size])
            start += chunk_size - overlap

        coll = _get_rag_collection()
        for i, chunk in enumerate(chunks):
            coll.upsert(
                documents=[chunk],
                ids=[f"doc-{_rag_doc_counter[0]}-chunk-{i}"],
                metadatas=[{"source": label}],
            )
        _rag_doc_counter[0] += 1
        return f"Ingested {len(chunks)} chunks from '{label}' into knowledge base."
    except Exception as e:
        return f"Ingest error: {e}"


def rag_search(query: str) -> str:
    """Search the persistent RAG knowledge base for chunks relevant to the query."""
    try:
        coll  = _get_rag_collection()
        count = coll.count()
        if count == 0:
            return "Knowledge base is empty. Use rag_ingest(text_or_url) first."
        results = coll.query(query_texts=[query], n_results=min(3, count))
        docs    = results.get("documents", [[]])[0]
        metas   = results.get("metadatas", [[]])[0]
        if not docs:
            return "No relevant results found."
        parts = [f"[source: {m.get('source', 'unknown')}]\n{d}" for d, m in zip(docs, metas)]
        return "\n\n---\n\n".join(parts)
    except Exception as e:
        return f"Search error: {e}"
