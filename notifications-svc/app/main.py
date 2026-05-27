from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, select
from pydantic import BaseModel
import aio_pika
import asyncio
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@postgres:5432/notifications_db")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(100))


class NotificationCreate(BaseModel):
    title: str
    message: str
    channel: str


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    channel: str

    class Config:
        from_attributes = True


app = FastAPI(title="Notifications Service", version="1.0.0")
rabbitmq_connection = None


async def get_rabbitmq():
    global rabbitmq_connection
    for attempt in range(10):
        try:
            rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
            logger.info("Connected to RabbitMQ")
            return rabbitmq_connection
        except Exception as e:
            logger.warning(f"RabbitMQ not ready (attempt {attempt+1}): {e}")
            await asyncio.sleep(3)
    logger.error("Could not connect to RabbitMQ")
    return None


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    asyncio.create_task(get_rabbitmq())
    logger.info("notifications-svc-s09 started on port 8131")


async def get_session():
    async with async_session() as session:
        yield session


async def publish_notification(notification: dict):
    global rabbitmq_connection
    if rabbitmq_connection and not rabbitmq_connection.is_closed:
        try:
            channel = await rabbitmq_connection.channel()
            queue = await channel.declare_queue("notifications", durable=True)
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(notification).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key="notifications",
            )
            logger.info(f"Published notification to RabbitMQ: {notification['id']}")
        except Exception as e:
            logger.error(f"Failed to publish to RabbitMQ: {e}")


@app.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Notification))
    return result.scalars().all()


@app.post("/notifications", response_model=NotificationResponse, status_code=201)
async def create_notification(data: NotificationCreate, session: AsyncSession = Depends(get_session)):
    notification = Notification(**data.model_dump())
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    await publish_notification({"id": notification.id, "title": notification.title,
                                 "message": notification.message, "channel": notification.channel})
    return notification


@app.get("/notifications/{notification_id}", response_model=NotificationResponse)
async def get_notification(notification_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@app.delete("/notifications/{notification_id}", status_code=204)
async def delete_notification(notification_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    await session.delete(notification)
    await session.commit()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "notifications-svc-s09"}