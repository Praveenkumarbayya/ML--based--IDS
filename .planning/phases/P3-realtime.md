# Phase 3 — Real-time alert stream

## Goal
Malicious predictions push to every connected dashboard client in under 100ms
via WebSocket. No polling.

## Tasks
1. `api/realtime.py` — `WebSocketManager` holding a set of connections, with
   `broadcast(payload: dict)` that gathers and handles dead connections.
2. `ws://.../ws/alerts` endpoint — authenticates via the same API key, then
   subscribes the socket to the broadcast manager.
3. Hook `broadcast` into `/predict` and `/predict/batch` — fire when any
   prediction is Malicious, payload includes the new alert id, ts, confidence,
   and the top features that drove the decision (SHAP-lite: largest feature
   values).
4. Graceful shutdown: close all sockets on FastAPI lifespan exit.
5. Integration test with httpx WebSocket client.

## Acceptance
- Open `wscat -c ws://host/ws/alerts -H "X-API-Key: ..."`.
- In another terminal, POST a malicious-looking payload to `/predict`.
- The wscat socket receives a JSON alert within 100 ms.
