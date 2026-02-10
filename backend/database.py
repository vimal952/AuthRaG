from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

client: AsyncIOMotorClient = None


async def connect_db():
    global client
    client = AsyncIOMotorClient(settings.MONGO_URL)
    await client[settings.MONGO_DB].users.create_index("email", unique=True)
    await client[settings.MONGO_DB].audit_logs.create_index("timestamp")
    await client[settings.MONGO_DB].audit_logs.create_index("user_id")
    await client[settings.MONGO_DB].conversations.create_index("user_id")


async def close_db():
    global client
    if client:
        client.close()


def get_db():
    return client[settings.MONGO_DB]
