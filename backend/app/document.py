import fitz


def extract_text_by_page(pdf_bytes: bytes) -> list[dict]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append({"page_number": i + 1, "text": text})
    doc.close()
    return pages


def chunk_text(pages: list[dict], chunk_size: int = 500, overlap: int = 100) -> list[dict]:
    chunks = []
    chunk_index = 0

    for page in pages:
        text = page["text"]
        page_num = page["page_number"]
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text_str = text[start:end]

            if chunk_text_str.strip():
                chunks.append({
                    "text": chunk_text_str.strip(),
                    "page_number": page_num,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1

            start += chunk_size - overlap

    return chunks
