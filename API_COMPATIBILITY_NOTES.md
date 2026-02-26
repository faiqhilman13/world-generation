# API Compatibility Notes

## World Labs base URL handling

The plan references endpoint paths in the form `/marble/v1/...`.

### Implemented default

- `WORLDLABS_BASE_URL` default is `https://api.worldlabs.ai`.
- The adapter always calls exact paths:
  - `POST /marble/v1/media-assets:prepare_upload`
  - `GET /marble/v1/media-assets/{media_asset_id}`
  - `POST /marble/v1/worlds:generate`
  - `GET /marble/v1/worlds/{world_id}`
  - `POST /marble/v1/worlds:list`
  - `GET /marble/v1/operations/{operation_id}`
- If `WORLDLABS_BASE_URL` is set to a value already ending in `/marble/v1`, the adapter de-duplicates the path prefix so requests stay correct.

## Upload response tolerance

`upload_info` field names can vary across providers and revisions.
The adapter currently accepts:

- URL: `upload_info.url` or `upload_info.upload_url`
- Method: `upload_info.method` or `upload_info.upload_method` or `upload_info.http_method`
- Headers: `upload_info.headers` or `upload_info.required_headers`

## World prompt payload defaults

The World Labs world prompt variant object can differ by schema revisions.  
Current implementation uses these normalized shapes:

- `text` -> `{"type":"text","text_prompt":"<text_prompt>","disable_recaption?":<bool>}`
- `image` -> `{"type":"image","image_prompt":{"source":"media_asset","media_asset_id":"<source_media_asset_id>"},"text_prompt?":"<text>","disable_recaption?":<bool>,"is_pano?":<bool>}`
- `multi_image` -> `{"type":"multi-image","multi_image_prompt":[{"content":{"source":"media_asset","media_asset_id":"<id>"}}...],"text_prompt?":"<text>","disable_recaption?":<bool>,"reconstruct_images?":true}`
- `video` -> `{"type":"video","video_prompt":{"source":"media_asset","media_asset_id":"<source_media_asset_id>"},"text_prompt?":"<text>","disable_recaption?":<bool>}`

Internal generate request validation rules:

- `text`: requires `text_prompt`; does not require `source_media_asset_id`.
- `image`: requires `source_media_asset_id` that belongs to the current session.
- `multi_image`: requires `source_media_asset_id` or `reference_media_asset_ids`.
- `video`: requires `source_media_asset_id` that belongs to the current session.

## Operation success world resolution

`world_id` is currently resolved from this ordered set:

1. `response.world_id`
2. `response.world.world_id`
3. `metadata.world_id`
4. `metadata.world.world_id`
