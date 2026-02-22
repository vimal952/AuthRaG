import io
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from bson import ObjectId
import PyPDF2
import docx
from database import get_db
from vector_store import add_chunks, delete_document_chunks
from services.embedding import embed_texts, chunk_text
from routes.auth import get_current_user, require_admin
from utils.audit import log_event
from config import settings

router = APIRouter(prefix="/api/documents", tags=["documents"])

ROLE_ORDER = {"user": 0, "employee": 1, "admin": 2}


def extract_text(file_bytes: bytes, filename: str) -> str:
    if filename.endswith(".pdf"):
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    elif filename.endswith(".docx"):
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        return file_bytes.decode("utf-8", errors="ignore")


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    access_level: str = Form(...),
    admin=Depends(require_admin),
):
    if access_level not in ("admin", "employee", "all"):
        raise HTTPException(status_code=400, detail="Invalid access_level")

    content = await file.read()
    text = extract_text(content, file.filename)

    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from document")

    document_id = str(uuid.uuid4())
    db = get_db()

    chunks = chunk_text(text, settings.MAX_CHUNK_SIZE, settings.CHUNK_OVERLAP)
    embeddings = embed_texts(chunks)

    vector_chunks = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        vector_chunks.append({
            "id": f"{document_id}_{i}",
            "embedding": emb,
            "text": chunk,
            "metadata": {
                "document_id": document_id,
                "title": title,
                "access_level": access_level,
                "chunk_index": i,
                "abstraction_type": access_level,
            },
        })

    add_chunks(vector_chunks)

    doc_record = {
        "_id": ObjectId(),
        "document_id": document_id,
        "title": title,
        "filename": file.filename,
        "access_level": access_level,
        "uploaded_by": str(admin["_id"]),
        "uploaded_by_email": admin["email"],
        "chunk_count": len(chunks),
        "uploaded_at": datetime.utcnow(),
    }
    await db.documents.insert_one(doc_record)

    await log_event(
        "document_upload",
        str(admin["_id"]),
        admin["email"],
        admin["role"],
        document_id=document_id,
        title=title,
        access_level=access_level,
        chunk_count=len(chunks),
    )

    return {"document_id": document_id, "title": title, "chunks": len(chunks)}


@router.get("/")
async def list_documents(user=Depends(get_current_user)):
    db = get_db()
    user_role = user["role"]

    query = {}
    if user_role == "user":
        query["access_level"] = "all"
    elif user_role == "employee":
        query["access_level"] = {"$in": ["employee", "all"]}

    cursor = db.documents.find(query, {"_id": 0})
    docs = await cursor.to_list(length=200)
    return docs


@router.delete("/{document_id}")
async def delete_document(document_id: str, admin=Depends(require_admin)):
    db = get_db()
    doc = await db.documents.find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    delete_document_chunks(document_id)
    await db.documents.delete_one({"document_id": document_id})

    await log_event(
        "document_delete",
        str(admin["_id"]),
        admin["email"],
        admin["role"],
        document_id=document_id,
        title=doc.get("title"),
    )
    return {"message": "Document deleted"}
