# Архитектура системы уведомлений

## project_code: notifications-s09

## Обзор

Система состоит из трёх микросервисов для управления и доставки уведомлений (notifications):

1. **API Gateway** — точка входа для внешних клиентов, принимает REST-запросы, маршрутизирует к notifications-svc-s09.
2. **notifications-svc-s09** (порт 8131) — основной сервис: хранит уведомления в PostgreSQL, обрабатывает CRUD через REST, публикует события в RabbitMQ.
3. **Notification Processor** — фоновый воркер, читает события из RabbitMQ и выполняет фактическую отправку (email/push).

## Диаграмма взаимодействия

```
[Клиент]
   │  HTTP
   ▼
[API Gateway :80]
   │  HTTP /api/notifications → upstream: notifications-svc-s09
   ▼
[notifications-svc-s09 :8131]  ←──── PostgreSQL (notifications_db)
   │
   │  AMQP (publish)
   ▼
[RabbitMQ :5672]
   │
   │  AMQP (consume)
   ▼
[Notification Processor]
```

## Сервисы

### API Gateway
- **Язык/Фреймворк**: Python (FastAPI)
- **Роль**: Принимает входящие HTTP-запросы от фронтенда/клиентов, проксирует к notifications-svc-s09.
- **Порт**: 80

### notifications-svc-s09
- **Язык/Фреймворк**: Python (FastAPI)
- **База данных**: PostgreSQL (`notifications_db`)
- **Роль**: CRUD для ресурса `notifications` с полем `channel` (str).
- **Порт**: 8131
- **Эндпоинты**:
  - `GET    /notifications` — список всех уведомлений
  - `POST   /notifications` — создать уведомление
  - `GET    /notifications/{id}` — получить по ID
  - `DELETE /notifications/{id}` — удалить

### Notification Processor
- **Язык**: Python
- **Роль**: Подписывается на очередь RabbitMQ, при поступлении нового уведомления выполняет отправку (логирует канал и сообщение).
- **Взаимодействие**: AMQP с RabbitMQ

## Технологический стек

| Компонент            | Технология              |
|----------------------|-------------------------|
| Язык                 | Python 3.11             |
| Веб-фреймворк        | FastAPI + Uvicorn       |
| База данных          | PostgreSQL 15           |
| ORM                  | SQLAlchemy + asyncpg    |
| Очередь сообщений    | RabbitMQ 3              |
| Контейнеризация      | Docker + Docker Compose |
| Внешний протокол     | REST (JSON over HTTP)   |
| Внутренний протокол  | AMQP (async messaging)  |

## Обоснование решений

- **REST** выбран для внешнего API: удобен для фронтенда и сторонних клиентов, легко тестируется через curl/Postman.
- **AMQP / RabbitMQ** для межсервисного общения: обеспечивает слабую связность — падение Notification Processor не влияет на основной сервис (сообщения накапливаются в очереди).
- **PostgreSQL** — надёжное хранилище с поддержкой ACID.
- **FastAPI** — высокая производительность, автоматическая генерация OpenAPI-документации.

## Zero Downtime & Устойчивость

- Сервисы запускаются с `restart: unless-stopped`.
- notifications-svc-s09 ожидает готовности PostgreSQL через `healthcheck`.
- Notification Processor использует retry при подключении к RabbitMQ.
- API Gateway проксирует с таймаутами.

## Запуск

```bash
docker-compose up --build
```

После запуска API доступен по адресу `http://localhost/api/notifications`.

## Проверка

```bash
# Создать уведомление
curl -X POST http://localhost/api/notifications \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "message": "Hello", "channel": "email"}'

# Получить список
curl http://localhost/api/notifications
```