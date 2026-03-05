from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from database import get_db
from services.rag import answer_query
from routes.auth import get_current_user
from models.schemas import ChatRequest
from utils.audit import log_event

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/query")
async def query(body: ChatRequest, user=Depends(get_current_user)):
    db = get_db()
    user_id = str(user["_id"])

    history = []
    conversation_id = body.conversation_id

    if conversation_id:
        conv = await db.conversations.find_one(
            {"_id": ObjectId(conversation_id), "user_id": user_id}
        )
        if conv:
            history = conv.get("messages", [])
    else:
        result = await db.conversations.insert_one({
            "user_id": user_id,
            "messages": [],
            "created_at": datetime.utcnow(),
        })
        conversation_id = str(result.inserted_id)

    rag_result = await answer_query(body.message, user["role"], history)

    user_msg = {"role": "user", "content": body.message, "timestamp": datetime.utcnow()}
    assistant_msg = {
        "role": "assistant",
        "content": rag_result["answer"],
        "sources": rag_result["sources"],
        "timestamp": datetime.utcnow(),
    }

    await db.conversations.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$push": {"messages": {"$each": [user_msg, assistant_msg]}}},
    )

    await log_event(
        "chat_query",
        user_id,
        user["email"],
        user["role"],
        conversation_id=conversation_id,
        query=body.message,
        sources=[s["document_id"] for s in rag_result["sources"]],
        latency_ms=rag_result["latency_ms"],
    )

    return {
        "conversation_id": conversation_id,
        "answer": rag_result["answer"],
        "sources": rag_result["sources"],
        "latency_ms": rag_result["latency_ms"],
    }


@router.get("/conversations")
async def list_conversations(user=Depends(get_current_user)):
    db = get_db()
    cursor = db.conversations.find(
        {"user_id": str(user["_id"])},
        {"messages": {"$slice": -1}, "created_at": 1},
    ).sort("created_at", -1).limit(20)
    convs = await cursor.to_list(length=20)
    return [
        {
            "id": str(c["_id"]),
            "created_at": c["created_at"],
            "last_message": c["messages"][0]["content"] if c.get("messages") else "",
        }
        for c in convs
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, user=Depends(get_current_user)):
    db = get_db()
    conv = await db.conversations.find_one(
        {"_id": ObjectId(conversation_id), "user_id": str(user["_id"])}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = conv.get("messages", [])
    for m in messages:
        m["timestamp"] = m["timestamp"].isoformat() if hasattr(m.get("timestamp"), "isoformat") else str(m.get("timestamp", ""))
    return {"id": conversation_id, "messages": messages}
