import asyncio
import aio_pika
import json
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [processor] %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")


async def send_notification(notification: dict):
    """Simulate sending a notification via the specified channel."""
    channel = notification.get("channel", "unknown")
    title = notification.get("title", "")
    message = notification.get("message", "")
    notification_id = notification.get("id")

    if channel == "email":
        logger.info(f"[EMAIL] Sending notification #{notification_id}: '{title}' — {message}")
    elif channel == "push":
        logger.info(f"[PUSH ] Sending notification #{notification_id}: '{title}' — {message}")
    elif channel == "sms":
        logger.info(f"[SMS  ] Sending notification #{notification_id}: '{title}' — {message}")
    else:
        logger.info(f"[{channel.upper():<5}] Sending notification #{notification_id}: '{title}' — {message}")


async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            logger.info(f"Received notification from queue: {data}")
            await send_notification(data)
        except Exception as e:
            logger.error(f"Error processing message: {e}")


async def main():
    logger.info("Notification Processor starting...")

    for attempt in range(20):
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            logger.info("Connected to RabbitMQ")
            break
        except Exception as e:
            logger.warning(f"Waiting for RabbitMQ (attempt {attempt + 1}): {e}")
            await asyncio.sleep(5)
    else:
        logger.error("Could not connect to RabbitMQ after 20 attempts. Exiting.")
        return

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)
        queue = await channel.declare_queue("notifications", durable=True)

        logger.info("Waiting for notifications in queue 'notifications'...")
        await queue.consume(process_message)

        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())