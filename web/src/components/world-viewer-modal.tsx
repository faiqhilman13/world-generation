"use client";

import { WorldViewer } from "@/components/world-viewer";
import type { WorldDetail } from "@/lib/api";

type WorldViewerModalProps = {
  open: boolean;
  world: WorldDetail | null;
  onClose: () => void;
};

export function WorldViewerModal({ open, world, onClose }: WorldViewerModalProps) {
  if (!open || !world) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[95vh] w-full max-w-6xl overflow-auto rounded-2xl bg-surface p-4 shadow-2xl">
        <div className="mb-3 flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">{world.display_name ?? world.world_id}</h2>
            <p className="text-xs text-foreground/60">Status: {world.status}</p>
          </div>
          <button
            className="rounded-lg border border-line px-3 py-1 text-sm hover:bg-accent-soft"
            onClick={onClose}
            type="button"
          >
            Close
          </button>
        </div>
        <WorldViewer world={world} />
      </div>
    </div>
  );
}
