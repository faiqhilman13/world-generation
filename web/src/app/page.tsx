"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { WorldViewerModal } from "@/components/world-viewer-modal";
import {
  bootstrapSession,
  confirmUpload,
  generateWorld,
  getApiBaseUrl,
  getJob,
  getWorldDetail,
  listWorlds,
  prepareUpload,
  proxyUpload,
  trackViewerOpen,
  type JobRecord,
  type PromptType,
  type UploadKind,
  type WorldCard,
  type WorldDetail,
} from "@/lib/api";

type Stage =
  | "idle"
  | "bootstrapping"
  | "preparing"
  | "uploading"
  | "confirming"
  | "generating"
  | "finalizing"
  | "error";

const MODEL_OPTIONS = ["Marble 0.1-mini", "Marble 0.1-plus"];
const IMAGE_EXTENSIONS = new Set(["jpg", "jpeg", "png", "webp"]);
const VIDEO_EXTENSIONS = new Set(["mp4", "mov", "webm"]);
const IMAGE_MIME_TYPES = new Set(["image/jpeg", "image/jpg", "image/png", "image/webp"]);
const VIDEO_MIME_TYPES = new Set(["video/mp4", "video/quicktime", "video/webm"]);

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [uploadKind, setUploadKind] = useState<UploadKind>("image");
  const [promptType, setPromptType] = useState<PromptType>("image");
  const [displayName, setDisplayName] = useState<string>("");
  const [textPrompt, setTextPrompt] = useState<string>("");
  const [model, setModel] = useState<string>(MODEL_OPTIONS[0]);
  const [publicWorld, setPublicWorld] = useState<boolean>(true);
  const [tags, setTags] = useState<string>("interior");

  const [stage, setStage] = useState<Stage>("idle");
  const [uploadPercent, setUploadPercent] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [confirmedMediaAssetId, setConfirmedMediaAssetId] = useState<string | null>(null);

  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [worlds, setWorlds] = useState<WorldCard[]>([]);
  const [isLoadingWorlds, setIsLoadingWorlds] = useState<boolean>(false);

  const [isViewerOpen, setIsViewerOpen] = useState<boolean>(false);
  const [viewerWorld, setViewerWorld] = useState<WorldDetail | null>(null);

  const isBusy = stage !== "idle" && stage !== "error";

  const stageLabel = useMemo(() => {
    if (stage === "idle") return "Ready";
    if (stage === "bootstrapping") return "Preparing";
    if (stage === "preparing") return "Preparing Upload";
    if (stage === "uploading") return `Uploading ${uploadPercent}%`;
    if (stage === "confirming") return "Confirming Upload";
    if (stage === "generating") return "Submitting Generation";
    if (stage === "finalizing") return "Finalizing";
    return "Error";
  }, [stage, uploadPercent]);

  useEffect(() => {
    const init = async () => {
      setStage("bootstrapping");
      try {
        await bootstrapSession();
        await refreshWorlds();
        setStage("idle");
      } catch (error) {
        setStage("error");
        setErrorMessage(
          error instanceof Error ? error.message : "Session bootstrap failed.",
        );
      }
    };
    void init();
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      const activeJobs = jobs.filter(
        (job) => job.status === "queued" || job.status === "processing",
      );
      if (activeJobs.length === 0) {
        return;
      }

      void (async () => {
        const updatedJobs = await Promise.all(
          activeJobs.map(async (job) => {
            try {
              return await getJob(job.job_id);
            } catch {
              return job;
            }
          }),
        );

        setJobs((prev) => {
          const map = new Map(prev.map((job) => [job.job_id, job]));
          for (const job of updatedJobs) {
            map.set(job.job_id, job);
          }
          return Array.from(map.values()).sort(
            (a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at),
          );
        });

        if (updatedJobs.some((job) => job.status === "succeeded")) {
          await refreshWorlds();
        }
      })();
    }, 3000);
    return () => clearInterval(timer);
  }, [jobs]);

  const refreshWorlds = async () => {
    setIsLoadingWorlds(true);
    try {
      const response = await listWorlds();
      setWorlds(response.items);
    } finally {
      setIsLoadingWorlds(false);
    }
  };

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setStage("error");
      setErrorMessage("Select an input file before upload.");
      return;
    }

    setErrorMessage(null);
    setUploadPercent(0);
    setConfirmedMediaAssetId(null);

    try {
      setStage("preparing");
      const extension = file.name.includes(".")
        ? (file.name.split(".").pop() ?? "").toLowerCase()
        : "";
      const mimeType = (file.type || "application/octet-stream").toLowerCase();

      if (uploadKind === "image") {
        if (!IMAGE_EXTENSIONS.has(extension) || !IMAGE_MIME_TYPES.has(mimeType)) {
          throw new Error(
            "Unsupported image format. Use PNG, JPG, JPEG, or WEBP.",
          );
        }
        try {
          await createImageBitmap(file);
        } catch {
          throw new Error(
            "Invalid image data. Please select a valid PNG, JPG, JPEG, or WEBP file.",
          );
        }
      }
      if (uploadKind === "video") {
        if (!VIDEO_EXTENSIONS.has(extension) || !VIDEO_MIME_TYPES.has(mimeType)) {
          throw new Error("Unsupported video format. Use MP4, MOV, or WEBM.");
        }
      }

      const ticket = await prepareUpload({
        file_name: file.name,
        kind: uploadKind,
        extension,
        mime_type: mimeType,
        metadata: { size_bytes: file.size },
      });

      setStage("uploading");
      // Use API proxy upload by default to avoid provider signed-URL browser CORS issues.
      setUploadPercent(35);
      await proxyUpload(ticket.media_asset_id, file);
      setUploadPercent(100);

      setStage("confirming");
      await confirmUpload(ticket.media_asset_id);

      setConfirmedMediaAssetId(ticket.media_asset_id);
      setStage("idle");
    } catch (error) {
      setStage("error");
      setErrorMessage(error instanceof Error ? error.message : "Upload flow failed.");
    }
  };

  const handleGenerate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!confirmedMediaAssetId) {
      setStage("error");
      setErrorMessage("Upload and confirm a media asset before generation.");
      return;
    }

    try {
      setStage("generating");
      const response = await generateWorld({
        source_media_asset_id: confirmedMediaAssetId,
        prompt_type: promptType,
        text_prompt: textPrompt || null,
        display_name: displayName || null,
        model,
        public: publicWorld,
        tags: tags
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      });

      const createdJob = await getJob(response.job_id);
      setJobs((prev) => [createdJob, ...prev]);
      setStage("finalizing");
      setTimeout(() => {
        setStage("idle");
      }, 700);
    } catch (error) {
      setStage("error");
      setErrorMessage(error instanceof Error ? error.message : "Generate request failed.");
    }
  };

  const openViewer = async (worldId: string) => {
    if (!worldId || worldId === "undefined") {
      setErrorMessage("Cannot open viewer: missing world ID.");
      setStage("error");
      return;
    }
    try {
      const detail = await getWorldDetail(worldId);
      try {
        await trackViewerOpen(true);
      } catch {}
      setViewerWorld(detail);
      setIsViewerOpen(true);
    } catch (error) {
      try {
        await trackViewerOpen(false);
      } catch {}
      setErrorMessage(error instanceof Error ? error.message : "Failed to load viewer.");
      setStage("error");
    }
  };

  const copyShareLink = async (worldId: string) => {
    if (!worldId || worldId === "undefined") {
      setErrorMessage("Cannot copy link: missing world ID.");
      setStage("error");
      return;
    }
    const base = window.location.origin;
    await navigator.clipboard.writeText(`${base}/worlds/${worldId}`);
  };

  return (
    <main className="mx-auto min-h-screen w-full max-w-7xl px-5 py-10 md:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-accent">Interior World</p>
          <h1 className="mt-2 text-3xl font-semibold">Generation Studio</h1>
          <p className="mt-2 text-sm text-foreground/70">
            Upload a source, dispatch a World Labs generation job, then inspect viewer output.
          </p>
        </div>
        <div className="rounded-xl border border-line bg-surface px-4 py-3 text-sm">
          <p className="font-semibold">{stageLabel}</p>
          <p className="text-xs text-foreground/60">API: {getApiBaseUrl()}</p>
        </div>
      </div>

      {errorMessage ? (
        <p className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </p>
      ) : null}

      <section className="grid gap-6 lg:grid-cols-[1.05fr_1.15fr]">
        <div className="space-y-6">
          <form
            onSubmit={handleUpload}
            className="rounded-2xl border border-line bg-surface p-5 shadow-[0_12px_32px_rgba(31,30,27,0.08)]"
          >
            <h2 className="text-lg font-semibold">1. Upload Source</h2>
            <div className="mt-4 space-y-4">
              <label className="block space-y-1">
                <span className="text-sm font-medium">Input Kind</span>
                <select
                  className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm"
                  value={uploadKind}
                  onChange={(event) => setUploadKind(event.target.value as UploadKind)}
                  disabled={isBusy}
                >
                  <option value="image">Image</option>
                  <option value="video">Video</option>
                </select>
              </label>

              <label className="block space-y-1">
                <span className="text-sm font-medium">Reference File</span>
                <input
                  className="block w-full rounded-xl border border-line bg-white px-3 py-2 text-sm file:mr-4 file:rounded-lg file:border-0 file:bg-accent-soft file:px-3 file:py-2 file:text-accent"
                  type="file"
                  accept={uploadKind === "image" ? ".jpg,.jpeg,.png,.webp" : ".mp4,.mov,.webm"}
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                  disabled={isBusy}
                />
              </label>

              <div className="h-2 overflow-hidden rounded-full bg-white">
                <div
                  className="h-full bg-accent transition-all"
                  style={{
                    width: `${stage === "uploading" ? uploadPercent : confirmedMediaAssetId ? 100 : 8}%`,
                  }}
                />
              </div>

              <button
                type="submit"
                className="rounded-xl bg-accent px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isBusy || !file}
              >
                Run Upload Flow
              </button>

              {confirmedMediaAssetId ? (
                <p className="rounded-lg bg-accent-soft px-3 py-2 text-xs">
                  Confirmed media_asset_id:{" "}
                  <span className="font-mono">{confirmedMediaAssetId}</span>
                </p>
              ) : null}
            </div>
          </form>

          <form
            onSubmit={handleGenerate}
            className="rounded-2xl border border-line bg-surface p-5 shadow-[0_12px_32px_rgba(31,30,27,0.08)]"
          >
            <h2 className="text-lg font-semibold">2. Generate World</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="space-y-1">
                <span className="text-sm font-medium">Display Name</span>
                <input
                  className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm"
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  placeholder="Sunlit Loft Concept"
                />
              </label>

              <label className="space-y-1">
                <span className="text-sm font-medium">Model</span>
                <select
                  className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm"
                  value={model}
                  onChange={(event) => setModel(event.target.value)}
                >
                  {MODEL_OPTIONS.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-1">
                <span className="text-sm font-medium">Prompt Type</span>
                <select
                  className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm"
                  value={promptType}
                  onChange={(event) => setPromptType(event.target.value as PromptType)}
                >
                  <option value="image">Image</option>
                  <option value="text">Text</option>
                  <option value="multi_image">Multi Image</option>
                  <option value="video">Video</option>
                </select>
              </label>

              <label className="space-y-1">
                <span className="text-sm font-medium">Tags (comma separated)</span>
                <input
                  className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm"
                  value={tags}
                  onChange={(event) => setTags(event.target.value)}
                />
              </label>

              <label className="space-y-1 sm:col-span-2">
                <span className="text-sm font-medium">Text Prompt (for text mode)</span>
                <textarea
                  className="min-h-20 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm"
                  value={textPrompt}
                  onChange={(event) => setTextPrompt(event.target.value)}
                  placeholder="Warm Japanese-modern living room with oak and stone finishes."
                />
              </label>
            </div>

            <label className="mt-3 flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={publicWorld}
                onChange={(event) => setPublicWorld(event.target.checked)}
              />
              Public world
            </label>
            <p className="mt-1 text-xs text-foreground/60">
              Private worlds may fail to open on the external Marble viewer unless authenticated.
            </p>

            <button
              type="submit"
              className="mt-4 rounded-xl bg-[#0f766e] px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isBusy || !confirmedMediaAssetId}
            >
              Submit Generation
            </button>
          </form>
        </div>

        <div className="space-y-6">
          <section className="rounded-2xl border border-line bg-surface p-5">
            <h2 className="text-lg font-semibold">Job Tracker</h2>
            <div className="mt-4 space-y-3">
              {jobs.length === 0 ? (
                <p className="text-sm text-foreground/65">
                  No jobs yet. Start with upload + generation.
                </p>
              ) : (
                jobs.map((job) => (
                  <article
                    key={job.job_id}
                    className="rounded-xl border border-line bg-[#fefbf3] p-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold">{job.status}</p>
                      <p className="font-mono text-xs">{job.job_id.slice(0, 8)}</p>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-white">
                      <div
                        className="h-full bg-accent transition-all"
                        style={{ width: `${job.progress_percent ?? 5}%` }}
                      />
                    </div>
                    {job.world_id ? (
                      <p className="mt-2 text-xs text-foreground/70">
                        world_id: <span className="font-mono">{job.world_id}</span>
                      </p>
                    ) : null}
                    {job.error?.message ? (
                      <p className="mt-2 text-xs text-red-700">{job.error.message}</p>
                    ) : null}
                  </article>
                ))
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-line bg-surface p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Generated Worlds</h2>
              <button
                type="button"
                className="rounded-lg border border-line px-3 py-1 text-xs hover:bg-accent-soft"
                onClick={() => void refreshWorlds()}
              >
                {isLoadingWorlds ? "Refreshing..." : "Refresh"}
              </button>
            </div>
            <div className="mt-4 grid gap-3">
              {worlds.length === 0 ? (
                <p className="text-sm text-foreground/65">
                  Worlds will appear here after jobs succeed.
                </p>
              ) : (
                worlds
                  .filter((world) => Boolean(world.world_id && world.world_id !== "undefined"))
                  .map((world) => (
                  <article
                    key={world.world_id}
                    className="rounded-xl border border-line bg-[#fefbf3] p-3"
                  >
                    <h3 className="text-sm font-semibold">
                      {world.display_name ?? world.world_id}
                    </h3>
                    <p className="mt-1 text-xs text-foreground/65">
                      model: {world.model ?? "unknown"}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-white"
                        onClick={() => void openViewer(world.world_id)}
                      >
                        Open World
                      </button>
                      <Link
                        href={`/worlds/${world.world_id}`}
                        className="rounded-lg border border-line px-3 py-1.5 text-xs"
                      >
                        Viewer Page
                      </Link>
                      <button
                        type="button"
                        className="rounded-lg border border-line px-3 py-1.5 text-xs"
                        onClick={() => void copyShareLink(world.world_id)}
                      >
                        Copy Share Link
                      </button>
                      <button
                        type="button"
                        className="rounded-lg border border-line px-3 py-1.5 text-xs"
                        onClick={() => {
                          setDisplayName(world.display_name ?? "");
                          setPromptType("image");
                        }}
                      >
                        Re-run with edits
                      </button>
                      {world.thumbnail_url ? (
                        <a
                          className="rounded-lg border border-line px-3 py-1.5 text-xs"
                          href={world.thumbnail_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Download Preview
                        </a>
                      ) : null}
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        </div>
      </section>

      <WorldViewerModal
        open={isViewerOpen}
        world={viewerWorld}
        onClose={() => {
          setIsViewerOpen(false);
          setViewerWorld(null);
        }}
      />
    </main>
  );
}
