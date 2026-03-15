from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from database import get_db
from routes.auth import require_admin, get_current_user
from models.schemas import RoleUpdateRequest
from services.llm import check_health
from utils.audit import log_event
from vector_store import get_collection

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def list_users(admin=Depends(require_admin)):
    db = get_db()
    cursor = db.users.find({}, {"password": 0})
    users = await cursor.to_list(length=500)
    return [
        {
            "id": str(u["_id"]),
            "email": u["email"],
            "name": u["name"],
            "role": u["role"],
            "created_at": u.get("created_at"),
        }
        for u in users
    ]


@router.patch("/users/{user_id}/role")
async def update_role(user_id: str, body: RoleUpdateRequest, admin=Depends(require_admin)):
    db = get_db()
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if str(target["_id"]) == str(admin["_id"]):
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": body.role}})
    await log_event(
        "role_change",
        str(admin["_id"]),
        admin["email"],
        admin["role"],
        target_user_id=user_id,
        target_email=target["email"],
        old_role=target["role"],
        new_role=body.role,
    )
    return {"message": f"Role updated to {body.role}"}


@router.get("/audit-logs")
async def get_audit_logs(
    page: int = 1,
    limit: int = 50,
    action: str = None,
    admin=Depends(require_admin),
):
    db = get_db()
    query = {}
    if action:
        query["action"] = action

    total = await db.audit_logs.count_documents(query)
    cursor = (
        db.audit_logs.find(query)
        .sort("timestamp", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )
    logs = await cursor.to_list(length=limit)
    for log in logs:
        log["_id"] = str(log["_id"])
        if isinstance(log.get("timestamp"), datetime):
            log["timestamp"] = log["timestamp"].isoformat()

    return {"total": total, "page": page, "logs": logs}


@router.get("/analytics")
async def get_analytics(admin=Depends(require_admin)):
    db = get_db()
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    query_logs = await db.audit_logs.find(
        {"action": "chat_query", "timestamp": {"$gte": last_7d}}
    ).to_list(length=10000)

    total_queries = len(query_logs)
    latencies = [l.get("latency_ms", 0) for l in query_logs if l.get("latency_ms")]
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0
    queries_24h = sum(1 for l in query_logs if l["timestamp"] >= last_24h)

    accessed_docs = {}
    for log in query_logs:
        for doc_id in log.get("sources", []):
            accessed_docs[doc_id] = accessed_docs.get(doc_id, 0) + 1

    top_docs_raw = sorted(accessed_docs.items(), key=lambda x: x[1], reverse=True)[:5]
    top_docs = []
    for doc_id, count in top_docs_raw:
        doc = await db.documents.find_one({"document_id": doc_id})
        top_docs.append({
            "document_id": doc_id,
            "title": doc["title"] if doc else "Deleted",
            "access_count": count,
        })

    user_counts = {}
    for log in query_logs:
        email = log.get("user_email", "unknown")
        user_counts[email] = user_counts.get(email, 0) + 1

    total_docs = await db.documents.count_documents({})
    total_users = await db.users.count_documents({})
    total_employees = await db.users.count_documents({"role": "employee"})

    upload_logs = await db.audit_logs.find(
        {"action": "document_upload", "timestamp": {"$gte": last_7d}}
    ).to_list(length=100)

    collection = get_collection()
    vector_count = collection.count() if collection else 0
    llm_healthy = await check_health()

    daily = {}
    for log in query_logs:
        day = log["timestamp"].strftime("%Y-%m-%d")
        daily[day] = daily.get(day, 0) + 1

    return {
        "total_queries": total_queries,
        "queries_24h": queries_24h,
        "avg_llm_latency_ms": avg_latency,
        "total_documents": total_docs,
        "total_vectors": vector_count,
        "total_users": total_users,
        "total_employees": total_employees,
        "top_accessed_docs": top_docs,
        "active_users": [
            {"email": e, "query_count": c}
            for e, c in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ],
        "daily_queries": [{"date": d, "count": c} for d, c in sorted(daily.items())],
        "llm_healthy": llm_healthy,
        "uploads_7d": len(upload_logs),
    }


@router.get("/document-access/{document_id}")
async def document_access_log(document_id: str, admin=Depends(require_admin)):
    db = get_db()
    logs = await db.audit_logs.find(
        {"action": "chat_query", "sources": document_id}
    ).sort("timestamp", -1).limit(100).to_list(length=100)

    for log in logs:
        log["_id"] = str(log["_id"])
        if isinstance(log.get("timestamp"), datetime):
            log["timestamp"] = log["timestamp"].isoformat()

    return logs
