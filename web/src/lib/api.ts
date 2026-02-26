export type UploadKind = "image" | "video";
export type PromptType = "text" | "image" | "multi_image" | "video";
export type JobStatus = "queued" | "processing" | "succeeded" | "failed" | "expired";

export type UploadPrepareResponse = {
  media_asset_id: string;
  upload_method: string;
  upload_url: string;
  required_headers: Record<string, string>;
};

export type JobRecord = {
  job_id: string;
  status: JobStatus;
  progress_percent: number | null;
  provider_operation_id: string | null;
  world_id: string | null;
  error: { code?: string; message?: string } | null;
  created_at: string;
  updated_at: string;
};

export type WorldCard = {
  world_id: string;
  job_id: string;
  display_name: string | null;
  model: string | null;
  public: boolean;
  world_marble_url: string | null;
  thumbnail_url: string | null;
  created_at: string;
};

export type WorldListResponse = {
  items: WorldCard[];
  next_cursor: string | null;
};

export type WorldDetail = {
  world_id: string;
  job_id: string;
  status: JobStatus;
  display_name: string | null;
  model: string | null;
  public: boolean;
  world_marble_url: string | null;
  thumbnail_url: string | null;
  world_payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const mergedHeaders = new Headers(init?.headers ?? {});
  if (!isFormData && !mergedHeaders.has("Content-Type")) {
    mergedHeaders.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: mergedHeaders,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API ${response.status}: ${body}`);
  }
  if (response.status === 204) {
    return {} as T;
  }
  return (await response.json()) as T;
}

export async function bootstrapSession(): Promise<void> {
  await apiFetch("/v1/sessions/bootstrap", { method: "POST" });
}

export async function prepareUpload(input: {
  file_name: string;
  kind: UploadKind;
  extension: string;
  mime_type: string;
  metadata?: Record<string, unknown>;
}): Promise<UploadPrepareResponse> {
  return apiFetch<UploadPrepareResponse>("/v1/uploads/prepare", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function confirmUpload(mediaAssetId: string): Promise<void> {
  await apiFetch("/v1/uploads/confirm", {
    method: "POST",
    body: JSON.stringify({ media_asset_id: mediaAssetId }),
  });
}

export async function generateWorld(input: {
  source_media_asset_id?: string | null;
  prompt_type: PromptType;
  text_prompt?: string | null;
  disable_recaption?: boolean;
  is_pano?: boolean;
  reconstruct_images?: boolean;
  reference_media_asset_ids?: string[];
  display_name?: string | null;
  model: string;
  seed?: number | null;
  tags?: string[];
  public?: boolean;
}): Promise<{ job_id: string; status: JobStatus }> {
  return apiFetch("/v1/worlds/generate", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getJob(jobId: string): Promise<JobRecord> {
  return apiFetch<JobRecord>(`/v1/jobs/${jobId}`, { method: "GET" });
}

export async function listWorlds(cursor?: string | null): Promise<WorldListResponse> {
  const query = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
  return apiFetch<WorldListResponse>(`/v1/worlds${query}`, { method: "GET" });
}

export async function getWorldDetail(worldId: string): Promise<WorldDetail> {
  return apiFetch<WorldDetail>(`/v1/worlds/${worldId}`, { method: "GET" });
}

export async function trackViewerOpen(success: boolean): Promise<void> {
  await apiFetch("/v1/metrics/viewer-open", {
    method: "POST",
    body: JSON.stringify({ success }),
  });
}

export async function proxyUpload(mediaAssetId: string, file: File): Promise<void> {
  const formData = new FormData();
  formData.append("media_asset_id", mediaAssetId);
  formData.append("file", file);
  await apiFetch("/v1/uploads/proxy", {
    method: "POST",
    body: formData,
  });
}

export function uploadBinary(
  file: File,
  ticket: UploadPrepareResponse,
  onProgress: (value: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(ticket.upload_method || "PUT", ticket.upload_url, true);

    for (const [key, value] of Object.entries(ticket.required_headers ?? {})) {
      xhr.setRequestHeader(key, value);
    }

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) {
        return;
      }
      onProgress(Math.round((event.loaded / event.total) * 100));
    };

    xhr.onerror = () => reject(new Error("Upload request failed"));
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new Error(`Upload failed with status ${xhr.status}`));
      }
    };

    xhr.send(file);
  });
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}
