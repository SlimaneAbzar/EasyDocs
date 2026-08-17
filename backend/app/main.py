from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import create_access_token, get_current_user, hash_password, verify_password
from .database import Base, engine, get_db
from .document import chunk_text, extract_text_by_page
from .models import ChatSession, Document, Query, User
from .rag import ask_question, delete_document_chunks, get_embedding_model, store_document_chunks
from .schemas import (
    AnswerResponse,
    ChatSessionDetail,
    ChatSessionResponse,
    DocumentResponse,
    QueryHistoryItem,
    QuestionRequest,
    SessionMessage,
    TokenResponse,
    UserCreate,
)

app = FastAPI(title="EasyDocs API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    get_embedding_model()


# --- Auth ---

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


# --- Documents ---

@app.get("/api/documents", response_model=list[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
    )
    return result.scalars().all()


@app.post("/api/documents/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    pdf_bytes = await file.read()
    if not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF file")

    pages = extract_text_by_page(pdf_bytes)
    if not pages:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    doc = Document(
        user_id=current_user.id,
        filename=file.filename,
        page_count=len(pages),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    chunks = chunk_text(pages)
    store_document_chunks(doc.id, chunks)

    return doc


@app.delete("/api/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your document")

    delete_document_chunks(document_id)
    await db.delete(doc)
    await db.commit()


# --- Q&A ---

@app.post("/api/documents/{document_id}/ask", response_model=AnswerResponse)
async def ask(
    document_id: int,
    data: QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your document")

    response = ask_question(document_id, data.question)

    session_id = data.session_id
    if not session_id:
        session = ChatSession(
            user_id=current_user.id,
            document_id=document_id,
            title=data.question[:80],
        )
        db.add(session)
        await db.flush()
        session_id = session.id

    query = Query(
        user_id=current_user.id,
        document_id=document_id,
        session_id=session_id,
        question=data.question,
        answer=response["answer"],
        language=response["language"],
    )
    db.add(query)
    await db.commit()

    return AnswerResponse(
        answer=response["answer"],
        language=response["language"],
        sources=response["sources"],
        session_id=session_id,
    )


# --- Sessions ---

@app.get("/api/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession, Document.filename)
        .join(Document, ChatSession.document_id == Document.id)
        .where(ChatSession.id == session_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    session, filename = row
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session")

    queries_result = await db.execute(
        select(Query)
        .where(Query.session_id == session_id)
        .order_by(Query.asked_at.asc())
    )
    queries = queries_result.scalars().all()

    return ChatSessionDetail(
        id=session.id,
        document_id=session.document_id,
        title=session.title,
        created_at=session.created_at,
        filename=filename,
        messages=[
            SessionMessage(question=q.question, answer=q.answer, asked_at=q.asked_at)
            for q in queries
        ],
    )


# --- History ---

@app.get("/api/history/sessions", response_model=list[ChatSessionResponse])
async def get_session_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
    )
    return result.scalars().all()


@app.get("/api/history", response_model=list[QueryHistoryItem])
async def get_history(
    document_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Query, Document.filename)
        .join(Document, Query.document_id == Document.id)
        .where(Query.user_id == current_user.id)
        .order_by(Query.asked_at.desc())
    )

    if document_id:
        stmt = stmt.where(Query.document_id == document_id)

    result = await db.execute(stmt)
    rows = result.all()

    return [
        QueryHistoryItem(
            id=query.id,
            document_id=query.document_id,
            filename=filename,
            session_id=query.session_id,
            question=query.question,
            answer=query.answer,
            language=query.language,
            asked_at=query.asked_at,
        )
        for query, filename in rows
    ]
