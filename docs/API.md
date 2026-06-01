# API Reference — Finance Research Agent

Base URL (local): `http://localhost:8000`
Interactive docs (OpenAPI/Swagger): `GET /docs` · ReDoc: `GET /redoc`

## Authentication

Optional. If `API_AUTH_KEY` is set on the server, every `/query*` request must
include the header:

```
X-API-Key: <your-key>
```

If unset (default for the demo), the endpoints are open.

---

## `GET /health`

Liveness/readiness probe. Used by the container `HEALTHCHECK`, load balancer
target groups, and Kubernetes probes.

**Response `200`**
```json
{
  "status": "ok",
  "app": "finance-research-agent",
  "version": "1.0.0",
  "environment": "development"
}
```

---

## `POST /query`

Run the agent and return the **complete** answer once generation finishes.

### Request body
| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string (1–2000) | yes | The user's financial research question. |
| `conversation_id` | string | no | Pass an existing id to continue a conversation (reuses memory). Omit to start a new one. |

```json
{
  "query": "What was the latest Fed interest rate decision?",
  "conversation_id": null
}
```

### Response `200` — `application/json`
| Field | Type | Description |
|---|---|---|
| `conversation_id` | string | Reuse this for follow-up turns. |
| `query` | string | Echo of the input query. |
| `answer` | string | Final answer incl. inline `[n]` citations and an appended **Sources** list. |
| `route` | `"search"` \| `"direct"` | Path the agent chose. |
| `route_reason` | string | One-sentence justification. |
| `sources` | array | Numbered sources (see below). |

`sources[]` item:
```json
{ "index": 1, "title": "Fed holds rates steady", "url": "https://..." }
```

**Example (search path)**
```json
{
  "conversation_id": "3f9a1c2e8b7d4f06a1c2e8b7d4f06a1c",
  "query": "What was the latest Fed interest rate decision?",
  "answer": "At its latest meeting the Federal Reserve held the federal funds target range at 4.25–4.50% [1], citing still-elevated core inflation [2].\n\n---\n**Sources:**\n[1] FOMC statement\n    https://www.federalreserve.gov/...\n[2] Reuters coverage\n    https://www.reuters.com/...",
  "route": "search",
  "route_reason": "Query contains a time-sensitive signal (fast-path).",
  "sources": [
    {"index": 1, "title": "FOMC statement", "url": "https://www.federalreserve.gov/..."},
    {"index": 2, "title": "Reuters coverage", "url": "https://www.reuters.com/..."}
  ]
}
```

**Example (direct path)** — `"What is diversification?"` returns `route: "direct"`,
`sources: []`, and a definitional answer.

---

## `POST /query/stream`

Same request body as `/query`, but streams the answer as **Server-Sent Events**
(`Content-Type: text/event-stream`). Each `data:` line is one JSON event with a
`type` discriminator. Consume events until `type: "done"` (or `"error"`).

### Event sequence
| `type` | Payload | Meaning |
|---|---|---|
| `metadata` | `conversation_id` | Sent first; capture for follow-ups. |
| `route` | `route`, `reason` | Routing decision. |
| `sources` | `sources[]`, `provider` | Emitted on the search path before tokens. |
| `token` | `content` | One chunk of answer text. Concatenate in order. |
| `done` | `answer` | Full answer text (incl. sources). Stream complete. |
| `error` | `message` | Generation failed; stream ends. |

**Sample stream**
```
data: {"type": "metadata", "conversation_id": "3f9a..."}

data: {"type": "route", "route": "search", "reason": "Query is time-sensitive."}

data: {"type": "sources", "sources": [{"index": 1, "title": "...", "url": "..."}], "provider": "tavily"}

data: {"type": "token", "content": "The EUR/USD rate is "}

data: {"type": "token", "content": "1.0847 [1]."}

data: {"type": "done", "answer": "The EUR/USD rate is 1.0847 [1].\n\n---\n**Sources:**\n[1] ..."}
```

### Consuming the stream (JavaScript)
```js
const res = await fetch("/query/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ query: "Current EUR/USD rate?" }),
});
const reader = res.body.getReader();
const decoder = new TextDecoder();
let buffer = "";
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  for (const line of buffer.split("\n\n")) {
    if (!line.startsWith("data: ")) continue;
    const evt = JSON.parse(line.slice(6));
    if (evt.type === "token") process.stdout.write(evt.content);
  }
  buffer = buffer.endsWith("\n\n") ? "" : buffer.split("\n\n").pop();
}
```

---

## Error codes

Errors return a JSON body: `{ "error_code": "...", "message": "..." }`.

| HTTP | `error_code` | When |
|---|---|---|
| `401` | `unauthorized` | `API_AUTH_KEY` set and `X-API-Key` missing/wrong. |
| `422` | `invalid_request` / validation | Body fails schema (e.g. empty `query`). |
| `502` | `search_provider_error` | Web search backend failed/unavailable. |
| `502` | `llm_error` | LLM provider call failed. |
| `500` | `configuration_error` | Server misconfigured (e.g. missing `OPENAI_API_KEY`). |
| `500` | `internal_error` | Unexpected error. |
| `503` | — | Agent not yet initialised (during startup). |

On the **streaming** endpoint, recoverable failures surface as a terminal
`{"type": "error", "message": "..."}` event rather than an HTTP error, because
headers are already sent once streaming begins.
