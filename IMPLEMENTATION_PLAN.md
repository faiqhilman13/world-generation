# Interior World
## Super Detailed Implementation Plan (World Labs API Grounded)

**Document version:** v1.0  
**Date:** 2026-02-25  
**Owner:** Product + Engineering  
**Primary target:** Recreate an Interior-AI-style product for interior designers, property agents, construction companies, and architecture workflows, where users upload sketches/photos and explore generated spaces interactively.

---

## 0. Why This Document Exists
This is a decision-complete implementation plan so engineering can execute without guesswork. It includes product scope, architecture, data models, endpoint contracts, async orchestration, UX behavior, QA, infra, rollout, and risk controls.

This plan is anchored to the official World Labs docs:

- https://docs.worldlabs.ai/api
- https://docs.worldlabs.ai/api/reference/media-assets/prepare-upload
- https://docs.worldlabs.ai/api/reference/media-assets/get
- https://docs.worldlabs.ai/api/reference/worlds/generate
- https://docs.worldlabs.ai/api/reference/worlds/get
- https://docs.worldlabs.ai/api/reference/worlds/list
- https://docs.worldlabs.ai/api/reference/operations/get

---

## 1. Product Goals

### 1.1 Core goals
1. Users can upload a real image or sketch/wireframe.
2. System generates a high-fidelity designed world using World Labs.
3. System exposes an interactive, immersive exploration mode:
   - mouse-look/pan/orbit where possible
   - keyboard movement (WASD)
   - zoom controls
4. Users can browse previous generated worlds and reopen them.
5. End-to-end flow is production-reliable for long-running generation jobs.

### 1.2 Secondary goals
1. Support style transfer-like behavior (source image + optional style reference).
2. Support “before/after” presentation experience.
3. Keep architecture extensible for future auth, credits, and billing.

### 1.3 Non-goals (v1)
1. Team collaboration/multi-user RBAC.
2. Enterprise tenancy.
3. Native mobile apps.
4. Full BIM/CAD import pipeline.

---

## 2. Implementation Scope for v1

### 2.1 In scope
1. Anonymous session-based usage.
2. Upload + world generation + operation polling.
3. Gallery/history of generated worlds.
4. Viewer mode with immersive camera interactions.
5. Public share links for selected worlds.
6. Robust retries, timeout handling, and observability.

### 2.2 Out of scope for v1
1. Payments and subscriptions.
2. Multi-org workspaces.
3. Fine-grained ACL UI (we keep permission controls backend-first).

---

## 3. Canonical External API Map (World Labs)

This section defines the exact external dependency contract we implement against.

### 3.1 Authentication
- Header: `WLT-Api-Key: <api-key>`
- Required on all World Labs API calls.

### 3.2 Media asset preparation
- Endpoint: `POST https://api.worldlabs.ai/marble/v1/media-assets:prepare_upload`
- Body includes:
  - `file_name`
  - `kind` (`image` or `video`)
  - `extension`
  - `metadata` (optional)
- Response includes:
  - `media_asset` (contains `media_asset_id` and metadata)
  - `upload_info` (contains upload URL/method/headers and curl hint)

### 3.3 Media asset retrieval
- Endpoint: `GET https://api.worldlabs.ai/marble/v1/media-assets/{media_asset_id}`
- Returns media metadata for previously prepared/uploaded asset.

### 3.4 World generation
- Endpoint: `POST https://api.worldlabs.ai/marble/v1/worlds:generate`
- Expected request features:
  - `world_prompt` (supports text/image/multi-image/video prompt classes)
  - `display_name`
  - `model` (`Marble 0.1-mini` or `Marble 0.1-plus`)
  - `permission` (`public`, `allowed_readers`, `allowed_writers`)
  - `seed`
  - `tags`
- Returns long-running operation payload:
  - `done`
  - `operation_id`
  - `created_at`
  - `updated_at`
  - `expires_at`
  - `error`
  - `metadata`
  - `response` (when done)

### 3.5 World retrieval
- Endpoint: `GET https://api.worldlabs.ai/marble/v1/worlds/{world_id}`
- Returns world payload including world identifiers, URLs (`world_marble_url`), prompt info, permissions, assets, metadata.

### 3.6 Worlds listing
- Endpoint: `POST https://api.worldlabs.ai/marble/v1/worlds:list`
- Supports filters:
  - `page_size`, `page_token`
  - `status`
  - `model`
  - `tags`
  - `is_public`
  - `created_after`, `created_before`
  - `sort_by`
- Returns world list plus pagination token.

### 3.7 Operation retrieval
- Endpoint: `GET https://api.worldlabs.ai/marble/v1/operations/{operation_id}`
- Used for polling until completion.
- Contract:
  - `done = false`: still processing
  - `done = true` + `error = null`: success
  - `done = true` + `error != null`: failure
  - `response` populated on success

### 3.8 Known error semantics
- World generate docs indicate possible `400`, `402`, `500`.
- Operation retrieval docs indicate `401`, `404`, `500`.
- List docs indicate `400`, `500`.

---

## 4. High-Level System Architecture

## 4.1 Components
1. **Frontend (`web`)**: Next.js (TypeScript, App Router)
2. **API (`api`)**: FastAPI for internal orchestration and normalized contracts
3. **Worker (`worker`)**: Celery async pipelines for long-running jobs
4. **DB**: Postgres
5. **Queue/Cache**: Redis
6. **Object Storage**: S3-compatible bucket for input artifacts and optional derivatives
7. **Observability**: OpenTelemetry + structured logs + metrics

### 4.2 Why this architecture
1. World generation is asynchronous and can take minutes.
2. Browser should never poll external provider directly with API keys.
3. Internal model must normalize external payload changes.
4. Worker queue prevents API thread blocking and enables robust retries.

---

## 5. End-to-End User Flow (Authoritative)

### 5.1 Upload and generate flow
1. User opens app.
2. Backend creates/reads anonymous session cookie (`sid`).
3. User uploads source image/sketch.
4. Backend asks World Labs for upload preparation (`media-assets:prepare_upload`).
5. Backend returns upload instructions to client.
6. Client uploads file to signed URL with required headers.
7. Backend verifies asset by `GET /media-assets/{media_asset_id}`.
8. Backend creates generation job and enqueues worker.
9. Worker calls `worlds:generate`.
10. Worker stores `operation_id` and begins polling operations endpoint.
11. On completion, worker resolves `world_id` from operation response metadata/response.
12. Worker fetches final world via `GET /worlds/{world_id}`.
13. Worker persists normalized world + asset URLs.
14. Frontend job card transitions `queued -> processing -> succeeded`.
15. User opens immersive viewer.

### 5.2 Gallery flow
1. Frontend calls internal `/v1/worlds` list endpoint.
2. API queries local DB (not World Labs each time).
3. Returns paginated normalized records.
4. Optional sync endpoint can backfill from `worlds:list` when needed.

---

## 6. Internal API Specification (Our Product)

### 6.1 Session bootstrap
`POST /v1/sessions/bootstrap`
- Creates/refreshes anonymous session.
- Returns session descriptor.

### 6.2 Create upload ticket
`POST /v1/uploads/prepare`
- Input:
  - `file_name`
  - `kind`
  - `extension`
  - `mime_type`
  - `metadata?`
- Backend forwards to World Labs prepare-upload.
- Output:
  - `media_asset_id`
  - `upload_method`
  - `upload_url`
  - `required_headers`

### 6.3 Confirm upload
`POST /v1/uploads/confirm`
- Input: `media_asset_id`
- Backend calls World Labs media get.
- Marks asset as ready if retrievable.

### 6.4 Generate world job
`POST /v1/worlds/generate`
- Input:
  - `source_media_asset_id`
  - `prompt_type` (`text` | `image` | `multi_image` | `video`)
  - `text_prompt?`
  - `display_name?`
  - `model`
  - `seed?`
  - `tags?`
  - `public?`
- Output:
  - `job_id`
  - `status`

### 6.5 Get job
`GET /v1/jobs/{job_id}`
- Returns normalized lifecycle data:
  - status enum
  - progress percent
  - provider operation id
  - world id if done
  - error object if failed

### 6.6 List worlds
`GET /v1/worlds?cursor=...&limit=...`
- Returns user session world list and minimal card metadata.

### 6.7 Get world details
`GET /v1/worlds/{world_id}`
- Returns full normalized world payload for viewer.

---

## 7. Data Model (Postgres)

### 7.1 `sessions`
- `id` UUID PK
- `sid` TEXT UNIQUE NOT NULL
- `created_at` TIMESTAMPTZ
- `updated_at` TIMESTAMPTZ

### 7.2 `media_assets`
- `id` UUID PK
- `session_id` FK
- `provider_media_asset_id` TEXT UNIQUE
- `file_name` TEXT
- `kind` TEXT CHECK (`image`,`video`,`binary`)
- `extension` TEXT
- `mime_type` TEXT
- `provider_payload` JSONB
- `created_at` TIMESTAMPTZ
- `updated_at` TIMESTAMPTZ

### 7.3 `world_jobs`
- `id` UUID PK
- `session_id` FK
- `source_media_asset_id` FK
- `provider_operation_id` TEXT UNIQUE NULL
- `provider_world_id` TEXT UNIQUE NULL
- `status` TEXT CHECK (`queued`,`processing`,`succeeded`,`failed`,`expired`)
- `progress_percent` INT NULL
- `request_payload` JSONB
- `operation_payload` JSONB
- `world_payload` JSONB
- `error_code` TEXT NULL
- `error_message` TEXT NULL
- `created_at` TIMESTAMPTZ
- `updated_at` TIMESTAMPTZ

### 7.4 `world_views` (derived cache for fast listing)
- `id` UUID PK
- `world_job_id` FK UNIQUE
- `display_name` TEXT
- `model` TEXT
- `public` BOOLEAN
- `world_marble_url` TEXT
- `thumbnail_url` TEXT NULL
- `created_at` TIMESTAMPTZ
- `updated_at` TIMESTAMPTZ

### 7.5 `audit_logs`
- `id` BIGSERIAL PK
- `session_id` FK
- `event_type` TEXT
- `event_payload` JSONB
- `created_at` TIMESTAMPTZ

---

## 8. Job State Machine (Strict)

### 8.1 States
1. `queued`
2. `processing`
3. `succeeded`
4. `failed`
5. `expired`

### 8.2 Transition rules
- `queued -> processing` when worker submits to World Labs.
- `processing -> succeeded` when operation `done=true`, `error=null`, world resolved.
- `processing -> failed` when operation `done=true`, `error!=null`.
- `processing -> expired` when operation exceeded max polling horizon.

### 8.3 Retry policy
- Network/timeouts: exponential backoff with jitter.
- 5xx provider responses: retry capped (e.g., 8 attempts).
- 4xx semantic failures: no retry, fail fast.

---

## 9. World Labs Integration Module Design

### 9.1 Adapter boundaries
Create `WorldLabsClient` with strict methods:
1. `prepare_upload(...)`
2. `get_media_asset(media_asset_id)`
3. `generate_world(...)`
4. `get_operation(operation_id)`
5. `get_world(world_id)`
6. `list_worlds(...)`

### 9.2 Transport rules
- Timeout default: 30s
- Retry only on idempotent/read calls and configured safe write scenarios.
- Always include:
  - `WLT-Api-Key`
  - `Content-Type: application/json` where required

### 9.3 Prompt builders
Implement typed prompt builders for:
- `WorldTextPrompt`
- `ImagePrompt`
- `MultiImagePrompt`
- `VideoPrompt`

### 9.4 Permission builder
`permission = { public, allowed_readers, allowed_writers }`
- v1 default: public false for user-private generation unless user opts in.

---

## 10. Viewer Architecture

### 10.1 Viewer goals
1. Responsive and smooth camera interaction.
2. Deterministic cleanup (avoid WebGL memory leaks).
3. Graceful fallback on weak devices.

### 10.2 Viewer modes
1. **Marble URL mode**: if provider returns directly embeddable interactive world URL.
2. **Splat asset mode**: if provider returns/derivable Gaussian splat asset URL.
3. **Fallback mode**: static preview with CTA if interactive payload unavailable.

### 10.3 Camera controls
- Mouse drag: look/orbit
- Scroll: zoom
- Keyboard: WASD translation
- Shift: fast mode
- Arrow keys: yaw/pitch fallback

### 10.4 Rendering safeguards
- Cap DPR for low-end devices.
- Auto-disable heavy post-effects.
- Pause render loop when tab hidden.

---

## 11. Frontend UX Blueprint

### 11.1 Main layout
1. Left panel:
   - uploader
   - mode/type selectors
   - prompt controls
   - model settings
2. Right panel:
   - job grid
   - world cards
   - status indicators

### 11.2 World card actions
- `Open World`
- `Download Preview`
- `Copy Share Link`
- `Re-run with edits`

### 11.3 Long-running job UX
- Persistent status labels:
  - Preparing
  - Uploading
  - Generating
  - Finalizing
- Polling heartbeat indicator.
- Never lose job card on refresh (server truth + local cache).

---

## 12. Security & Privacy

### 12.1 API key handling
- Never expose `WLT-Api-Key` to browser.
- Store in server-side secret manager.

### 12.2 Upload security
- Validate extension + MIME before prepare call.
- Enforce file size caps by config.
- Reject mismatched upload content type on confirmation.

### 12.3 Session isolation
- Every query scoped by `sid`.
- Prevent world/job enumeration by random IDs + scope checks.

### 12.4 Abuse controls
- IP + session rate limits on generation endpoint.
- Cooldown per session for repeated failures.

---

## 13. Observability Plan

### 13.1 Logging
Structured JSON logs with:
- request_id
- session_id
- job_id
- operation_id
- world_id
- provider_latency_ms
- status_transition

### 13.2 Metrics
- `world_generate_requests_total`
- `world_generate_failures_total`
- `operation_poll_cycles_histogram`
- `time_to_world_ready_seconds`
- `viewer_open_success_rate`

### 13.3 Tracing
- Trace spans from API request to worker completion.
- Include external call spans per World Labs endpoint.

### 13.4 Alerts
- Failure ratio > threshold in rolling 15m.
- Poll timeout spikes.
- Median generation time degradation.

---

## 14. Testing Strategy

### 14.1 Unit tests
1. Request validation and schema coercion.
2. Status mapping from operation payload.
3. Prompt builders for all prompt types.
4. Permission serialization.

### 14.2 Integration tests
1. Prepare upload -> confirm upload path.
2. Generate world -> poll operation -> fetch world.
3. Error mapping for known provider failure statuses.

### 14.3 End-to-end tests (Playwright)
1. Upload image and generate world.
2. Refresh while processing; card persists.
3. Open viewer and move camera.
4. Error path shown if provider fails.

### 14.4 Contract tests
- Snapshot representative World Labs responses.
- Validate parser resilience for nullable/unknown fields.

---

## 15. Deployment & Environments

### 15.1 Environments
1. `dev`
2. `staging`
3. `prod`

### 15.2 Environment variables
- `WORLDLABS_API_KEY`
- `WORLDLABS_BASE_URL` (default `https://api.worldlabs.ai/marble/v1`)
- `DATABASE_URL`
- `REDIS_URL`
- `SESSION_COOKIE_SECRET`
- `APP_BASE_URL`

### 15.3 Deployment targets
- Web/API: containerized deployment (Fly/Render/Kubernetes-compatible)
- Worker: dedicated worker deployment
- Postgres/Redis managed services

---

## 16. CI/CD Plan

### 16.1 CI checks
1. Lint
2. Typecheck
3. Unit tests
4. Integration tests with mocked provider
5. Build artifacts

### 16.2 CD gates
1. Staging deploy on merge to `main`.
2. Smoke tests against staging.
3. Manual promotion to production.

---

## 17. Phased Execution Plan (Detailed)

## Phase 1: Foundations (3-4 days)
**Status (2026-02-25): Completed**

1. Monorepo scaffold (`web`, `api`, `worker`, `infra`).
2. Local docker-compose (postgres, redis, api, worker, web).
3. DB migrations and seed scripts.
4. Session bootstrap endpoint.

### Exit criteria
- Achieved in repo (`/health` endpoint + compose service healthchecks implemented).

## Phase 2: Upload pipeline (2-3 days)
**Status (2026-02-25): Completed**

1. Implement World Labs prepare-upload adapter.
2. Implement upload-confirm endpoint.
3. Persist media assets and validation metadata.
4. Build frontend uploader with progress and failure states.

### Exit criteria
- Achieved in local flow (prepare -> direct upload -> confirm), plus proxy-upload fallback for signed-URL CORS failures (`POST /v1/uploads/proxy`).

## Phase 3: Generation orchestration (4-6 days)
**Status (2026-02-25): Completed (with staged-provider validation pending)**

1. Implement `/v1/worlds/generate`.
2. Queue worker and operation polling loop.
3. Persist job transitions and world payloads.
4. Implement `/v1/jobs/{id}` and `/v1/worlds` listing.

### Exit criteria
- Implemented end-to-end orchestration in code, including worker polling and persistence.

## Phase 4: Viewer and immersive UX (4-6 days)
**Status (2026-02-25): Completed (v1 baseline)**

1. Implement world detail page and viewer modal.
2. Add camera controls and lifecycle cleanup.
3. Add fallback modes for unsupported payloads/devices.

### Exit criteria
- Achieved for implemented viewer modes (Marble URL mode, splat-preview mode, fallback mode).

## Phase 5: Hardening + observability (3-4 days)
**Status (2026-02-25): Completed in codebase; production rollout tasks pending**

1. Metrics + tracing + dashboards.
2. Retry tuning and timeout thresholds.
3. Error UX and runbooks.
4. Final QA and release checklist.

### Exit criteria
- Partially achieved: code and docs are in place; staging soak + production promotion still pending.

---

## 18. Risk Register

### 18.1 API shape drift risk
- **Risk:** external response fields evolve.
- **Mitigation:** strict adapter + tolerant parser + contract tests.

### 18.2 Long generation latency
- **Risk:** poor UX.
- **Mitigation:** progressive states, robust polling, persistent cards.

### 18.3 402 insufficient credits
- **Risk:** failed jobs.
- **Mitigation:** explicit error messaging + throttling + admin alert.

### 18.4 Viewer format incompatibility
- **Risk:** some worlds not directly splat-renderable.
- **Mitigation:** mode abstraction (Marble URL vs splat asset vs fallback).

---

## 19. Explicit Defaults and Decisions

1. **Provider:** World Labs only.
2. **Frontend:** Next.js + TypeScript.
3. **Backend:** FastAPI + Celery.
4. **Data store:** Postgres + Redis.
5. **Auth model:** anonymous session in v1.
6. **Public/private:** default private unless user toggles public.
7. **Job polling interval:** start 2s, adaptive up to 10s.
8. **Max poll horizon:** 20 minutes (configurable).

---

## 20. Definition of Done (v1)

1. Upload -> generate -> view flow works without manual intervention. **Status:** Implemented in local stack.
2. >95% successful completion in staging for supported inputs. **Status:** Pending staging verification.
3. Clear user-visible errors for all major failure categories. **Status:** Implemented baseline error states/messages.
4. P95 generation latency tracked and monitored. **Status:** Metrics instrumentation added; dashboards/alerts pending.
5. No critical memory leaks in viewer under repeated open/close cycles. **Status:** Cleanup safeguards implemented; stress testing pending.
6. Production deployment with rollback runbook validated. **Status:** Runbook added; production validation pending.

---

## 21. Appendix A: External API Call Sequence (Concrete)

1. `POST /marble/v1/media-assets:prepare_upload`
2. Client `PUT <upload_url>` with `required_headers`
3. `GET /marble/v1/media-assets/{media_asset_id}`
4. `POST /marble/v1/worlds:generate`
5. `GET /marble/v1/operations/{operation_id}` (repeat until done)
6. `GET /marble/v1/worlds/{world_id}`
7. Optional sync/backfill: `POST /marble/v1/worlds:list`

---

## 22. Appendix B: Internal Error Taxonomy

- `UPLOAD_PREPARE_FAILED`
- `UPLOAD_PROXY_FAILED`
- `UPLOAD_CONFIRM_FAILED`
- `GENERATION_SUBMIT_FAILED`
- `GENERATION_PROVIDER_402`
- `GENERATION_PROVIDER_4XX`
- `GENERATION_PROVIDER_5XX`
- `OPERATION_TIMEOUT`
- `WORLD_FETCH_FAILED`
- `VIEWER_UNSUPPORTED_PAYLOAD`

Each error includes:
- `code`
- `display_message`
- `retryable`
- `provider_context`

---

## 23. Appendix C: Implementation Checklist (Task Tracker)

### Backend
- [ ] Session middleware (cookie/session handling implemented per-route; dedicated middleware not added yet)
- [x] Upload prepare endpoint
- [x] Upload confirm endpoint
- [x] World generate endpoint
- [x] Job status endpoint
- [x] World list endpoint
- [x] World detail endpoint
- [x] Adapter retries/backoff
- [x] Structured logging
- [x] Migrations

### Worker
- [x] Generate task
- [x] Poll task
- [x] Finalize world task
- [x] Timeout/expiry task

### Frontend
- [x] Upload form
- [x] Mode/prompt controls
- [x] Job cards
- [x] Status polling hooks
- [x] Viewer modal
- [ ] Gallery pagination (cursor-based pagination UI not yet exposed)
- [ ] Error toasts/states (inline error panels implemented; toast system pending)

### QA/Infra
- [x] Unit tests
- [x] Integration tests (provider-mocked API integration coverage)
- [ ] E2E tests
- [ ] Staging deployment
- [ ] Dashboards + alerts
- [x] Production runbook

---

## 24. Final Notes
This plan is intentionally detailed so implementation can begin immediately. The critical constraint is robust handling of long-running World Labs operations and consistent normalization of provider responses into stable internal contracts.

As soon as execution starts, any unknown provider payload nuances should be captured in adapter contract tests and reflected in a living `API_COMPATIBILITY_NOTES.md` document.

---

## 25. Execution Progress Snapshot (2026-02-25)

### Completed deliverables
1. Monorepo architecture implemented: `web`, `api`, `worker`, `infra`.
2. World Labs adapter integrated with required endpoints and `WLT-Api-Key` header.
3. Upload pipeline implemented end-to-end (prepare, direct upload, confirm, persistence) with API proxy-upload fallback for provider signed-URL CORS issues.
4. Async generation orchestration implemented (queue dispatch, operation polling, world finalization).
5. Viewer flow implemented (modal viewer + dedicated world route + fallback behavior).
6. Observability baseline implemented (structured logs, metrics endpoint, tracing hooks).

### Remaining high-priority tasks
1. Staging deployment and live-provider smoke tests with real keys.
2. E2E browser tests for upload/generate/viewer refresh scenarios.
3. Dashboard + alert wiring for production metrics.
4. Optional: convert per-route session handling into a dedicated middleware layer.
