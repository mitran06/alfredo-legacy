# HTTP API Reference

The Calendar Assistant exposes a lightweight REST API so other systems can converse with the agent, reset state, pull reminder notifications, and check service health. This document covers everything you need to integrate from anywhere on the network.

---

## 1. Service Overview

| Item                | Details |
| ------------------- | ------- |
| Base URL            | `http://<host>:<port>` (default `http://100.127.243.52:8000` when run locally) |
| Transport           | HTTP over JSON |
| Authentication      | None (add your own reverse proxy or gateway if required) |
| Content-Type        | `application/json` for requests/responses |
| Character encoding  | UTF-8 |

> Tip: run the server with `uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload` to accept remote connections.

---

## 2. Quick Start

1. Activate the project virtual environment and install dependencies: see the main `README.md`.
2. Launch the HTTP API server:

   ```powershell
   uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
   ```

3. Verify the service is up:

   ```powershell
   curl http://100.127.243.52:8000/health
   ```

   Expected response snippet:

   ```json
   {
     "is_started": true,
     "config_loaded": true,
     "conversation_stats": {
       "total_messages": 0,
       "user_messages": 0,
       "assistant_messages": 0,
       "pending_actions": 0
     },
     "reminder_stats": {
       "is_started": true,
       "enabled": true,
       "monitor": {
         "sent_reminders": 0,
         "custom_reminders_pending": 0,
         "service_state": "running"
       },
       "dispatcher": { "queue_size": 0 }
     }
   }
   ```

---

## 3. Endpoints

### 3.1 `POST /chat`

Send a message to the assistant and receive the AI response plus tool metadata.

| Aspect      | Description |
| ----------- | ----------- |
| Method      | `POST` |
| URL         | `/chat` |
| Request     | JSON body `{ "message": "string" }` |
| 200 Success | Returns AI response text, tool list, and metadata |
| Errors      | `500` for internal failures |

**Request schema**

```json
{
  "message": "What's on my calendar tomorrow?"
}
```

**Response schema**

```json
{
  "message": "Assistant reply text",
  "tools_used": ["list_events"],
  "metadata": {
    "model": "gemini-2.5-flash"
  }
}
```

**cURL example**

```powershell
curl -X POST http://100.127.243.52:8000/chat `
  -H "Content-Type: application/json" `
  -d '{"message": "Remind me tomorrow at 9am to call Alex"}'
```

**HTTPie alternative**

```bash
http POST :8000/chat message="What do I have on Friday?"
```

**JavaScript (fetch) snippet**

```javascript
const res = await fetch("http://100.127.243.52:8000/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message: "Schedule a lunch with Sam next Tuesday" }),
});
const data = await res.json();
console.log(data.message);
```

---

### 3.2 `POST /conversation/clear`

Reset the assistant's conversation memory.

| Aspect      | Description |
| ----------- | ----------- |
| Method      | `POST` |
| URL         | `/conversation/clear` |
| Request     | Empty body |
| 204 Success | Conversation state cleared |
| Errors      | `500` for failures |

**cURL example**

```powershell
curl -X POST http://100.127.243.52:8000/conversation/clear
```

---

### 3.3 `GET /stats`

Retrieve structured statistics about the conversation and reminder service.

| Aspect      | Description |
| ----------- | ----------- |
| Method      | `GET` |
| URL         | `/stats` |
| Response    | JSON with `conversation` and `reminders` objects |

**Sample response**

```json
{
  "conversation": {
    "total_messages": 12,
    "user_messages": 6,
    "assistant_messages": 6,
    "pending_actions": 1
  },
  "reminders": {
    "is_started": true,
    "monitor": {
      "sent_reminders": 4,
      "custom_reminders_pending": 2
    },
    "dispatcher": { "queue_size": 0 }
  }
}
```

**cURL example**

```powershell
curl http://100.127.243.52:8000/stats
```

---

### 3.4 `GET /notifications`

Fetch reminder notifications that have fired. This endpoint can either flush the in-memory queue (default) or provide a historical snapshot.

| Aspect      | Description |
| ----------- | ----------- |
| Method      | `GET` |
| URL         | `/notifications` |
| Query params| `limit` (default 20), `flush` (`true`/`false`, default `true`) |

**Sample response**

```json
{
  "notifications": [
    {
      "message": "🔔 Soon: 'Weekly Sync' starts in 10 minutes at 09:00 AM",
      "created_at": "2025-10-10T13:45:00.123456+00:00"
    }
  ]
}
```

**cURL example pulling without flushing**

```powershell
curl "http://100.127.243.52:8000/notifications?limit=50&flush=false"
```

Integrate this with cron jobs, worker queues, or messaging systems to forward reminders to SMS, Slack, etc.

---

### 3.5 `GET /health`

Returns a holistic status snapshot.

| Aspect      | Description |
| ----------- | ----------- |
| Method      | `GET` |
| URL         | `/health` |
| Response    | JSON containing readiness indicators for services |

Use this endpoint for uptime monitoring, readiness checks, or dashboard widgets.

---

## 4. Error Handling

All endpoints return standard HTTP status codes.

| Code | Meaning                          | Notes |
| ---- | -------------------------------- | ----- |
| 200  | OK                               | Successful fetch/operation |
| 204  | No Content                       | Conversation cleared |
| 400  | Bad Request                      | Malformed payload (reserved for future validation) |
| 404  | Not Found                        | Invalid route |
| 500  | Internal Server Error            | Unhandled exception inside assistant or downstream services |

**Error payload format**

```json
{
  "detail": "Failed to process message: <error reason>"
}
```

---

## 5. Integration Patterns

1. **Server-to-Server**: schedule recurring jobs (e.g., via Airflow or Cron) to query `/notifications` and forward them to messaging platforms.
2. **Web Apps**: use `/chat` from a front-end to embed the assistant directly in an internal tool; maintain user session context by mapping your user ID to an assistant session for multi-user deployments.
3. **Bots**: connect WhatsApp/Slack bots that proxy incoming messages to `/chat` and relay the assistant's response back to the channel.
4. **Monitoring**: hook `/health` into Prometheus blackbox exporter, Pingdom, or similar.

---

## 6. Deployment Considerations

- **Authentication**: Add an API gateway, reverse proxy (NGINX, Traefik), or FastAPI dependency to inject auth tokens before exposing publicly.
- **TLS**: terminate HTTPS at a load balancer or wrap Uvicorn with an SSL certificate (`--ssl-keyfile` / `--ssl-certfile`).
- **Scaling**: run Uvicorn with multiple workers (`uvicorn ... --workers 4`) and front with a process manager like `gunicorn` or `supervisord`.
- **State**: conversation memory currently lives in-process. For multi-instance deployments, add a shared store (Redis/Postgres) and extend `AssistantApp` accordingly.
- **Timeouts**: configure client-side HTTP timeouts; the `/chat` endpoint duration depends on the Gemini response time.

---

## 7. Tooling Snippets

### Postman

1. Import a new request with `POST http://100.127.243.52:8000/chat`.
2. Set headers `Content-Type: application/json`.
3. Body (raw JSON): `{ "message": "List my events for next week" }`.
4. Save the collection for reuse and add tests verifying presence of `tools_used`.

### Python Requests

```python
import requests

BASE_URL = "http://100.127.243.52:8000"

resp = requests.post(
    f"{BASE_URL}/chat",
    json={"message": "Schedule a dentist appointment on 15th May at 2pm"},
    timeout=60,
)
resp.raise_for_status()
print(resp.json()["message"])
```

### PowerShell Invoke-RestMethod

```powershell
$body = @{ message = "What's on my calendar tomorrow?" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://100.127.243.52:8000/chat" -ContentType "application/json" -Body $body
```

---

## 8. Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `ECONNREFUSED` when calling API | Ensure Uvicorn is running and reachable from your network. Bind to `0.0.0.0` for remote access. |
| `500 Failed to process message` | Check server logs for Gemini/MCP errors; confirm API keys and OAuth credentials are valid. |
| Empty `/notifications` response | No reminders have fired yet; set `flush=false` to review recent history. |
| Long `/chat` latency | Gemini may be processing a complex request; consider asynchronous client patterns or queueing. |

---

For deeper customization (custom reminder channels, persistent memory, authentication), extend `src/app/assistant_app.py` or wrap this API behind your preferred gateway.
