# Система уведомлений — notifications-s09

Финальный проект курса по распределённым системам. Группа ИКС-433, студент Каршибоев М.

## Что это?

Микросервисная система управления уведомлениями (notifications). Позволяет создавать уведомления с указанием канала доставки (email, push, sms), хранить их в PostgreSQL и асинхронно отправлять через RabbitMQ.

## Зачем это?

Демонстрирует принципы распределённых систем:
- Разделение ответственности между сервисами
- Слабая связность через очередь сообщений (AMQP)
- REST для внешнего API
- Docker Compose для воспроизводимого запуска

## Сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| api-gateway | 80 | Точка входа, проксирует `/api/*` к notifications-svc |
| notifications-svc-s09 | 8131 | CRUD для уведомлений, PostgreSQL |
| notification-processor | — | Воркер, читает из RabbitMQ и отправляет |
| postgres | 5432 | База данных |
| rabbitmq | 5672 / 15672 | Очередь + Management UI |

## Как запустить

```bash
docker-compose up --build
```

## API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | /api/notifications | Список уведомлений |
| POST | /api/notifications | Создать уведомление |
| GET | /api/notifications/{id} | Получить по ID |
| DELETE | /api/notifications/{id} | Удалить |

### Пример создания уведомления

```bash
curl -X POST http://localhost/api/notifications \
  -H "Content-Type: application/json" \
  -d '{"title": "Привет", "message": "Ваш заказ готов!", "channel": "email"}'
```

### Пример получения списка

```bash
curl http://localhost/api/notifications
```

## OpenAPI Документация

После запуска: http://localhost:8131/docs (notifications-svc)

## RabbitMQ Management UI

http://localhost:15672 (guest / guest)