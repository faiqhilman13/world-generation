"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { WorldViewer } from "@/components/world-viewer";
import { getWorldDetail, trackViewerOpen, type WorldDetail } from "@/lib/api";

export default function WorldDetailPage() {
  const params = useParams<{ worldId?: string | string[] }>();
  const worldIdRaw = params?.worldId;
  const worldId = Array.isArray(worldIdRaw) ? worldIdRaw[0] : worldIdRaw;
  const routeError = !worldId || worldId === "undefined" ? "Missing world ID in route." : null;
  const [world, setWorld] = useState<WorldDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const headingLabel = world?.display_name ?? (routeError ? "World Viewer" : `World ${worldId || ""}`);

  useEffect(() => {
    if (routeError) {
      return;
    }

    const run = async () => {
      try {
        const detail = await getWorldDetail(worldId);
        try {
          await trackViewerOpen(true);
        } catch {}
        setWorld(detail);
      } catch (loadError) {
        try {
          await trackViewerOpen(false);
        } catch {}
        setError(loadError instanceof Error ? loadError.message : "Failed to load world detail.");
      }
    };
    void run();
  }, [worldId, routeError]);

  return (
    <main className="mx-auto min-h-screen w-full max-w-6xl px-6 py-8">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">
            {headingLabel}
          </h1>
          <p className="text-sm text-foreground/60">Dedicated viewer route</p>
        </div>
        <Link href="/" className="rounded-lg border border-line px-3 py-2 text-sm hover:bg-accent-soft">
          Back to Dashboard
        </Link>
      </div>

      {routeError || error ? (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {routeError ?? error}
        </p>
      ) : null}

      {world ? (
        <WorldViewer world={world} />
      ) : routeError || error ? null : (
        <p className="rounded-lg border border-line bg-surface px-4 py-3 text-sm text-foreground/70">
          Loading world...
        </p>
      )}
    </main>
  );
}
