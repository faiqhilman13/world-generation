# Upgrades

## Prompt Mode Expansion (Delivered)

### Delivered
1. Added full World Labs prompt mode support in the app:
   - `WorldTextPrompt`
   - `ImagePrompt`
   - `MultiImagePrompt`
   - `VideoPrompt`
2. Backend request contract now supports:
   - `source_media_asset_id` (optional for text mode)
   - `reference_media_asset_ids` (multi-image)
   - `disable_recaption`
   - `is_pano`
   - `reconstruct_images`
3. Frontend now supports:
   - prompt type selector for all 4 prompt modes
   - primary source upload (image/video)
   - multi-reference image upload for multi-image mode
   - prompt-specific validation before submit
4. Database updated so text-only generation can run without a source media asset.

## Next Suggested Upgrades

### 1. Reference roles for multi-image
Allow tagging each reference as `layout`, `furniture`, `wall`, `lighting`, etc.

### 2. Reference ordering UI
Add drag-reorder for reference images before generation.

### 3. Advanced multi-image controls
Expose optional azimuth input per image for spherical placement.

### 4. Prompt presets
Add interior-design presets (Scandinavian, Japandi, Industrial, Luxury, etc.).
