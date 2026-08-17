# EasyDocs

A full-stack document Q&A app that lets you upload PDFs and ask questions about them in any language. Uses RAG (Retrieval-Augmented Generation) to find relevant sections and answer with page citations.

---

## Features

- Upload PDFs and ask questions in English, Arabic, or any language
- Answers cite specific pages so you can verify against the original document
- Chat sessions are saved so you can return to a conversation later
- Drag-and-drop file upload
- JWT authentication with per-user document isolation

---

## Tech Stack

### Backend
- **Python / FastAPI** — async REST API with Pydantic validation and dependency injection
- **PostgreSQL** — stores users, documents, chat sessions, and query history via async SQLAlchemy with asyncpg
- **ChromaDB** — vector database for storing and retrieving document chunk embeddings by similarity
- **sentence-transformers (all-MiniLM-L6-v2)** — generates embeddings locally for each document chunk, no external API needed
- **Google Gemini API (gemini-3.5-flash)** — LLM that generates answers from retrieved context, with multilingual support
- **PyMuPDF** — extracts text page-by-page from uploaded PDFs
- **JWT (python-jose) + bcrypt** — token-based auth with hashed passwords

### Frontend
- **React 19** — SPA with component-based UI and context-based auth state
- **React Router** — client-side routing between dashboard, chat, and history views
- **react-markdown** — renders LLM markdown responses as formatted HTML in chat
- **Axios** — HTTP client with JWT interceptor for authenticated requests
- **nginx** — serves the production build and reverse-proxies API calls to the backend

### Infrastructure
- **Docker Compose** — orchestrates 4 services (frontend, backend, postgres, chromadb)
- **GitHub Actions CI** — runs ruff linting and frontend build checks on push

---

## How it works

When you upload a PDF, the backend extracts text page-by-page with PyMuPDF, splits it into overlapping chunks, generates vector embeddings with sentence-transformers, and stores them in ChromaDB. When you ask a question, the question is embedded with the same model, ChromaDB returns the most similar chunks, and those chunks are sent as context to Gemini with a system prompt that instructs it to answer only from the provided context and cite page numbers. The response streams back as markdown with `[Page N]` citations.

---

## Run locally

1. Clone the repo
2. Get a free API key from [Google AI Studio](https://aistudio.google.com/apikey)
3. Copy `.env.example` to `.env` and fill in your key:
   ```
   GEMINI_API_KEY=your-key-here
   SECRET_KEY=any-random-string
   ```
4. Start everything:
   ```
   docker compose up --build
   ```
5. Open http://localhost:3000
