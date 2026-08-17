import os
import time

import chromadb
import google.generativeai as genai
from sentence_transformers import SentenceTransformer

CHROMA_HOST = os.environ.get("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8000"))

embedding_model = None
chroma_client = None
gemini_model = None

SYSTEM_PROMPT = """You are a document assistant helping people understand official documents \
(bank letters, leases, insurance policies, government correspondence).

CONTEXT FROM DOCUMENT:
---
{context}
---

USER'S QUESTION: {question}

INSTRUCTIONS:
1. Answer using ONLY the document excerpts above. Do not use outside knowledge.
2. Respond in the SAME LANGUAGE as the user's question. If the question is in Arabic, respond in Arabic. If in French, respond in French.
3. For each claim in your answer, cite the source as [Page X].
4. Use simple, clear language. The reader may not be familiar with legal, financial, or technical terminology. If you must use a technical term, briefly explain it.
5. If the document excerpts do not contain enough information to answer the question, say so clearly. Do not guess.
6. Structure your answer with short paragraphs. Use bullet points for lists of requirements or conditions."""


def get_embedding_model():
    global embedding_model
    if embedding_model is None:
        embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return embedding_model


def get_chroma_client():
    global chroma_client
    if chroma_client is None:
        for attempt in range(5):
            try:
                chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
                chroma_client.heartbeat()
                break
            except Exception:
                if attempt < 4:
                    time.sleep(2)
                else:
                    raise
    return chroma_client


def get_gemini_model():
    global gemini_model
    if gemini_model is None:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        gemini_model = genai.GenerativeModel("gemini-3.5-flash")
    return gemini_model


def store_document_chunks(document_id: int, chunks: list[dict]) -> None:
    client = get_chroma_client()
    collection_name = f"doc_{document_id}"

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.create_collection(name=collection_name)

    texts = [c["text"] for c in chunks]
    model = get_embedding_model()
    embeddings = model.encode(texts).tolist()

    collection.add(
        ids=[f"chunk_{i}" for i in range(len(chunks))],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{"page_number": c["page_number"], "chunk_index": c["chunk_index"]} for c in chunks],
    )


def retrieve_relevant_chunks(document_id: int, question: str, top_k: int = 5) -> list[dict]:
    client = get_chroma_client()
    collection = client.get_collection(f"doc_{document_id}")

    model = get_embedding_model()
    question_embedding = model.encode([question]).tolist()

    results = collection.query(query_embeddings=question_embedding, n_results=top_k)

    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "text": results["documents"][0][i],
            "page_number": results["metadatas"][0][i]["page_number"],
        })
    return chunks


def ask_question(document_id: int, question: str) -> dict:
    chunks = retrieve_relevant_chunks(document_id, question)

    context = "\n".join(
        f"[Page {c['page_number']}] {c['text']}" for c in chunks
    )

    prompt = SYSTEM_PROMPT.format(context=context, question=question)

    model = get_gemini_model()
    response = model.generate_content(prompt)
    answer = response.text

    sources = [{"page_number": c["page_number"], "text_excerpt": c["text"][:150]} for c in chunks]

    return {"answer": answer, "language": "auto", "sources": sources}


def delete_document_chunks(document_id: int) -> None:
    client = get_chroma_client()
    try:
        client.delete_collection(f"doc_{document_id}")
    except Exception:
        pass
