# E2E Test Suite

## Purpose

This suite validates the full user journey from session bootstrap through world viewing, plus core failure and observability behavior.

## Environment Setup

1. From repo root:
   - `cd "C:\Users\faiqh\Software Projects\interior-world"`
2. Start services:
   - `docker compose up -d --build`
3. Confirm endpoints:
   - Web: `http://localhost:3001`
   - API health: `http://localhost:8000/health`
   - Metrics: `http://localhost:8000/metrics`

## Core E2E Scenarios

### 1. Session Bootstrap + CORS
- Open web app in browser.
- Verify network call `POST /v1/sessions/bootstrap` succeeds.
- Verify preflight (`OPTIONS`) for API calls succeeds (status 200).

### 2. Upload Prepare -> Proxy Upload -> Confirm
- Select image input and choose a valid file.
- Run upload flow.
- Expected:
  - `POST /v1/uploads/prepare` returns 200 and `media_asset_id`.
  - Frontend sends file via `POST /v1/uploads/proxy` (server-side upload to provider signed URL).
  - `POST /v1/uploads/confirm` returns 200.
  - UI shows confirmed media asset ID.

### 3. Generation Orchestration
- Submit generation using confirmed media asset.
- Expected:
  - `POST /v1/worlds/generate` returns `job_id`.
  - `GET /v1/jobs/{job_id}` transitions:
    - `queued` -> `processing` -> `succeeded` (or explicit failure state).
  - Worker logs show provider operation polling.

### 3A. Prompt Mode Coverage Matrix
- Validate all supported prompt modes:
  - `text`: no source upload required, text prompt required.
  - `image`: uploaded image source required.
  - `multi_image`: source image and/or reference image list required.
  - `video`: uploaded video source required.
- For each mode:
  - Submit generate request from UI.
  - Confirm queued job creation.
  - Confirm World Labs request payload matches selected mode.

### 4. Gallery + World Detail
- Refresh worlds list from UI.
- Expected:
  - New world appears in gallery card list.
  - `GET /v1/worlds` returns world card payload.
  - `GET /v1/worlds/{world_id}` returns detail payload.

### 5. Viewer Modes
- Open world in modal and dedicated `/worlds/{worldId}` page.
- Expected one of:
  - Marble URL mode (open in new tab, with fallback links).
  - Splat preview mode (canvas interactions: drag, WASD, wheel, shift).
  - Fallback mode with clear unsupported message.

### 6. Share Link
- Click `Copy Share Link`.
- Open copied URL in new tab.
- Expected: world detail route loads same world.

### 7. Error Path Coverage
- Trigger known validation path:
  - `prompt_type=text` with empty `text_prompt`.
- Expected:
  - API returns validation failure.
  - UI shows explicit error state/message (no silent fail).

### 8. Observability Smoke
- Verify metrics endpoint is reachable.
- Verify logs include request and worker job events.
- Verify viewer open metric event endpoint:
  - `POST /v1/metrics/viewer-open` responds `204`.

## Upload CORS Troubleshooting

1. Validate API preflight:
   - `curl -i -X OPTIONS http://localhost:8000/v1/sessions/bootstrap -H "Origin: http://localhost:3001" -H "Access-Control-Request-Method: POST"`
2. Validate proxy route exists:
   - `curl http://localhost:8000/openapi.json` and confirm `/v1/uploads/proxy` is present.
3. If direct upload fails with provider bucket CORS:
   - Confirm `POST /v1/uploads/proxy` returns 200 (browser no longer needs to hit provider signed URL directly).

## Operational Log Commands

- All services, follow mode:
  - `docker compose logs -f`
- Specific services:
  - `docker compose logs -f api worker web`
- Last 100 lines:
  - `docker compose logs --tail 100`

## Exit Criteria

1. All core scenarios pass without manual DB edits.
2. Successful world generation reaches `succeeded` state and opens in viewer.
3. Failure scenarios produce user-visible and logged errors.
4. No service crash/restart loop during full run.

## Known Follow-up (Not in this suite yet)

1. Browser automation via Playwright for repeatable CI E2E runs.
2. Performance/load test for concurrent generation sessions.
3. Staging soak test with production-like provider latency.
