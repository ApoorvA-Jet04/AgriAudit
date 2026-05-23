import os
import json
import sys
from rag.embedder import create_embedding

# Define persistent storage location in a relative "chroma_db" folder in the workspace root
CHROMA_DIR = "chroma_db"
os.makedirs(CHROMA_DIR, exist_ok=True)

# =====================================================================
# PURE-PYTHON VECTOR STORAGE FALLBACK FOR WINDOWS / PYTHON 3.13
# =====================================================================
class FallbackCollection:
    def __init__(self, name, persist_path):
        self.name = name
        self.persist_path = persist_path
        self.data = {
            "ids": [],
            "documents": [],
            "embeddings": [],
            "metadatas": []
        }
        self._load()

    def _load(self):
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add(self, documents, embeddings, metadatas, ids):
        for doc, emb, meta, cid in zip(documents, embeddings, metadatas, ids):
            if cid in self.data["ids"]:
                idx = self.data["ids"].index(cid)
                self.data["documents"][idx] = doc
                self.data["embeddings"][idx] = emb
                self.data["metadatas"][idx] = meta
            else:
                self.data["ids"].append(cid)
                self.data["documents"].append(doc)
                self.data["embeddings"].append(emb)
                self.data["metadatas"].append(meta)
        self._save()

    def query(self, query_embeddings, n_results=5):
        if not self.data["embeddings"]:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
            
        query_vector = query_embeddings[0]
        scores = []
        
        # Calculate cosine similarity for all stored embeddings
        for idx, emb in enumerate(self.data["embeddings"]):
            dot = sum(x * y for x, y in zip(query_vector, emb))
            m1 = sum(x * x for x in query_vector) ** 0.5
            m2 = sum(x * x for x in emb) ** 0.5
            similarity = dot / (m1 * m2) if m1 > 0 and m2 > 0 else 0.0
            scores.append((similarity, idx))
            
        # Sort by similarity descending
        scores.sort(key=lambda x: x[0], reverse=True)
        top_scores = scores[:n_results]
        
        res_ids = []
        res_docs = []
        res_metas = []
        res_distances = []
        
        for score, idx in top_scores:
            res_ids.append(self.data["ids"][idx])
            res_docs.append(self.data["documents"][idx])
            res_metas.append(self.data["metadatas"][idx])
            res_distances.append(1.0 - score)  # Cosine distance
            
        return {
            "ids": [res_ids],
            "documents": [res_docs],
            "metadatas": [res_metas],
            "distances": [res_distances]
        }

class FallbackChromaClient:
    def __init__(self, path):
        self.path = path

    def get_or_create_collection(self, name):
        persist_path = os.path.join(self.path, f"{name}_fallback.json")
        return FallbackCollection(name, persist_path)

# Determine if we should use fallback
use_fallback = False
if sys.platform == "win32" and sys.version_info >= (3, 13):
    use_fallback = True

chroma_client = None
collection = None

if not use_fallback:
    try:
        import chromadb
        chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        collection = chroma_client.get_or_create_collection(name="tender_rules")
    except Exception as e:
        print(f"[*] Warning: Native ChromaDB load failed ({e}). Falling back to Pure-Python vector store.")
        use_fallback = True

if use_fallback:
    chroma_client = FallbackChromaClient(path=CHROMA_DIR)
    collection = chroma_client.get_or_create_collection(name="tender_rules")


def expand_query_string(query):
    """
    Enriches query with agricultural synonyms and expansion terms before embedding.
    """
    lower_query = query.lower()
    variations = []
    
    if "nitrogen" in lower_query or " n " in lower_query or "urea" in lower_query:
        variations.extend(["nitrogen percentage", "fertilizer nitrogen content", "N requirement", "nitrogen threshold"])
    if "phosphate" in lower_query or "phosphorus" in lower_query or "p2o5" in lower_query or "superphosphate" in lower_query:
        variations.extend(["phosphate composition", "phosphorus pentoxide specification", "P2O5 percentage", "superphosphate specifications"])
    if "potassium" in lower_query or "potash" in lower_query or " k " in lower_query:
        variations.extend(["potassium chloride", "potash content", "K percentage"])
    if "moisture" in lower_query or "water" in lower_query:
        variations.extend(["moisture content limit", "water percentage", "maximum moisture"])
    if "delivery" in lower_query or "timeline" in lower_query or "schedule" in lower_query:
        variations.extend(["delivery timeline days", "schedule timeline", "days to deliver"])
    if "packaging" in lower_query or "bag" in lower_query:
        variations.extend(["packaging type", "bag size weight", "bag material specification"])
        
    if variations:
        return f"{query} | synonyms: {', '.join(variations)}"
    return query


def store_chunks(chunks, embeddings, metadatas=None):
    """
    Stores chunks, embeddings, and IDs in ChromaDB (or local fallback).
    
    Args:
        chunks (list): List of text chunk strings.
        embeddings (list): List of embedding vector lists.
        metadatas (list, optional): List of metadata dicts corresponding to the chunks.
    """
    if not chunks or not embeddings:
        return
        
    if len(chunks) != len(embeddings):
        raise ValueError("Number of chunks and embeddings must match.")
        
    ids = [f"chunk_{i}_{abs(hash(chunk))}" for i, chunk in enumerate(chunks)]
    
    if not metadatas:
        metadatas = [{"source": "tender_document"} for _ in chunks]
        
    try:
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        # Add required logs: print("Stored chunk:", i)
        for i in range(len(chunks)):
            print("Stored chunk:", i)
            
    except Exception as e:
        raise RuntimeError(f"Failed to store chunks in database: {str(e)}")

def search_chunks(query, n_results=5):
    """
    Performs semantic search on the stored chunks by creating query embeddings.
    
    Args:
        query (str): The search query.
        n_results (int): Number of top results to retrieve (default 5).
        
    Returns:
        list: A list of dicts with keys 'chunk_id', 'text', and 'metadata'.
    """
    if not query or not query.strip():
        return []
        
    try:
        # Implement semantic query expansion before querying
        expanded_query = expand_query_string(query)
        query_embedding = create_embedding(expanded_query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Required logs: Print retrieved documents clearly
        print("RETRIEVED DOCUMENTS:")
        print(results["documents"])
        print("-" * 60)
        
        formatted_results = []
        if results and 'documents' in results and results['documents']:
            documents = results['documents'][0]
            ids = results['ids'][0]
            metadatas = results['metadatas'][0] if 'metadatas' in results and results['metadatas'] else [{}] * len(documents)
            
            for doc, cid, meta in zip(documents, ids, metadatas):
                formatted_results.append({
                    "chunk_id": cid,
                    "text": doc,
                    "metadata": meta
                })
                
        return formatted_results
    except Exception as e:
        raise RuntimeError(f"Semantic search failed: {str(e)}")
