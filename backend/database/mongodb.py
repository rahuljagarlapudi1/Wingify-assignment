import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from config.settings import settings
from models.user import User
from models.document import Document


logger = logging.getLogger(__name__)


class Database:
    client: AsyncIOMotorClient | None = None


db = Database()


async def connect_to_mongo():
    try:
        db.client = AsyncIOMotorClient(settings.MONGODB_URL)
        await init_beanie(
        database=db.client[settings.DATABASE_NAME],
        document_models=[User, Document],
        )
        logger.info("Connected to MongoDB")
        print("Connected to MongoDB %s", settings.MONGODB_URL)
    except Exception as e:
        logger.exception("Failed to connect to MongoDB: %s", e)
        raise


async def close_mongo_connection():
    if db.client:
        db.client.close()
        logger.info("Disconnected from MongoDB")