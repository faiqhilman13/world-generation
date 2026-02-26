"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { WorldDetail } from "@/lib/api";

type WorldViewerProps = {
  world: WorldDetail;
};

type CameraState = {
  x: number;
  y: number;
  zoom: number;
  yaw: number;
  pitch: number;
};

type ViewerMode = "marble" | "splat" | "fallback";

function resolveAssetLinks(world: WorldDetail): {
  panoUrl: string | null;
  thumbnailUrl: string | null;
  spzUrl: string | null;
} {
  const payload = world.world_payload as Record<string, unknown>;
  const assets = (payload.assets as Record<string, unknown> | undefined) ?? {};
  const imagery = (assets.imagery as Record<string, unknown> | undefined) ?? {};
  const splats = (assets.splats as Record<string, unknown> | undefined) ?? {};
  const spzUrls = (splats.spz_urls as Record<string, unknown> | undefined) ?? {};

  const panoUrl =
    typeof imagery.pano_url === "string" ? imagery.pano_url : null;
  const thumbnailUrl =
    typeof assets.thumbnail_url === "string"
      ? (assets.thumbnail_url as string)
      : world.thumbnail_url;
  const spzUrl =
    (typeof spzUrls.full_res === "string" && (spzUrls.full_res as string)) ||
    (typeof spzUrls["500k"] === "string" && (spzUrls["500k"] as string)) ||
    (typeof spzUrls["100k"] === "string" && (spzUrls["100k"] as string)) ||
    null;

  return { panoUrl, thumbnailUrl: thumbnailUrl ?? null, spzUrl };
}

function resolveMode(world: WorldDetail): ViewerMode {
  if (world.world_marble_url) {
    return "marble";
  }
  const payload = world.world_payload as Record<string, unknown>;
  if (typeof payload.splat_asset_url === "string" || typeof payload.splat_url === "string") {
    return "splat";
  }
  return "fallback";
}

export function WorldViewer({ world }: WorldViewerProps) {
  const mode = useMemo(() => resolveMode(world), [world]);
  const assetLinks = useMemo(() => resolveAssetLinks(world), [world]);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const hudTickRef = useRef(0);
  const keysRef = useRef<Set<string>>(new Set());
  const cameraRef = useRef<CameraState>({
    x: 0,
    y: 0,
    zoom: 1,
    yaw: 0,
    pitch: 0,
  });
  const dragRef = useRef<{ active: boolean; x: number; y: number }>({
    active: false,
    x: 0,
    y: 0,
  });
  const [cameraHint, setCameraHint] = useState<string>("x:0 y:0 zoom:1.00");

  useEffect(() => {
    if (mode !== "splat") {
      return;
    }
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }

    let running = true;
    const devicePixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(Math.floor(rect.width * devicePixelRatio), 1);
      canvas.height = Math.max(Math.floor(rect.height * devicePixelRatio), 1);
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    const onVisibility = () => {
      running = document.visibilityState === "visible";
    };
    document.addEventListener("visibilitychange", onVisibility);

    const onKeyDown = (event: KeyboardEvent) => {
      keysRef.current.add(event.key.toLowerCase());
    };
    const onKeyUp = (event: KeyboardEvent) => {
      keysRef.current.delete(event.key.toLowerCase());
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);

    const onMouseDown = (event: MouseEvent) => {
      dragRef.current = { active: true, x: event.clientX, y: event.clientY };
    };
    const onMouseMove = (event: MouseEvent) => {
      if (!dragRef.current.active) {
        return;
      }
      const deltaX = event.clientX - dragRef.current.x;
      const deltaY = event.clientY - dragRef.current.y;
      dragRef.current = { active: true, x: event.clientX, y: event.clientY };
      const camera = cameraRef.current;
      camera.yaw += deltaX * 0.005;
      camera.pitch = Math.max(-1, Math.min(1, camera.pitch + deltaY * 0.005));
    };
    const onMouseUp = () => {
      dragRef.current.active = false;
    };
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const camera = cameraRef.current;
      camera.zoom = Math.max(0.3, Math.min(2.6, camera.zoom - event.deltaY * 0.0015));
    };

    canvas.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });

    const render = () => {
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (!width || !height) {
        frameRef.current = window.requestAnimationFrame(render);
        return;
      }

      if (running) {
        const camera = cameraRef.current;
        const keys = keysRef.current;
        const speed = keys.has("shift") ? 6 : 3;
        if (keys.has("w")) camera.y -= speed;
        if (keys.has("s")) camera.y += speed;
        if (keys.has("a")) camera.x -= speed;
        if (keys.has("d")) camera.x += speed;
        if (keys.has("arrowleft")) camera.x -= speed * 0.6;
        if (keys.has("arrowright")) camera.x += speed * 0.6;
        if (keys.has("arrowup")) camera.y -= speed * 0.6;
        if (keys.has("arrowdown")) camera.y += speed * 0.6;
      }

      const camera = cameraRef.current;
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = "#101622";
      ctx.fillRect(0, 0, width, height);

      ctx.save();
      ctx.translate(width / 2 + camera.x, height / 2 + camera.y);
      ctx.scale(camera.zoom, camera.zoom);
      ctx.rotate(camera.yaw * 0.12);
      ctx.strokeStyle = "rgba(87, 177, 199, 0.42)";
      ctx.lineWidth = 1;
      for (let i = -20; i <= 20; i += 1) {
        ctx.beginPath();
        ctx.moveTo(-450, i * 22 + camera.pitch * 70);
        ctx.lineTo(450, i * 22 + camera.pitch * 70);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(i * 22, -320);
        ctx.lineTo(i * 22, 320);
        ctx.stroke();
      }
      ctx.restore();

      ctx.fillStyle = "rgba(245, 245, 245, 0.92)";
      ctx.font = "14px var(--font-geist-mono), monospace";
      ctx.fillText("Splat preview mode", 16, 24);
      ctx.fillText("WASD + mouse drag + wheel zoom + shift", 16, 46);
      hudTickRef.current += 1;
      if (hudTickRef.current % 8 === 0) {
        setCameraHint(
          `x:${camera.x.toFixed(0)} y:${camera.y.toFixed(0)} zoom:${camera.zoom.toFixed(2)}`,
        );
      }
      frameRef.current = window.requestAnimationFrame(render);
    };
    frameRef.current = window.requestAnimationFrame(render);

    return () => {
      if (frameRef.current !== null) {
        window.cancelAnimationFrame(frameRef.current);
      }
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      canvas.removeEventListener("mousedown", onMouseDown);
      canvas.removeEventListener("wheel", onWheel);
    };
  }, [mode]);

  if (mode === "marble" && world.world_marble_url) {
    return (
      <div className="flex h-[70vh] w-full flex-col items-center justify-center rounded-2xl border border-line bg-[#f4f2ea] p-6 text-center">
        <p className="text-lg font-semibold">Interactive Marble Viewer</p>
        <p className="mt-2 max-w-xl text-sm text-foreground/70">
          Provider viewer URLs may block iframe embedding. Open this world in a new tab.
        </p>
        <a
          href={world.world_marble_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 rounded-xl bg-accent px-4 py-2 text-sm font-medium text-white"
        >
          Open World in New Tab
        </a>
        <div className="mt-3 flex flex-wrap items-center justify-center gap-2 text-xs">
          {assetLinks.panoUrl ? (
            <a
              href={assetLinks.panoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border border-line px-3 py-1.5"
            >
              Open Panorama
            </a>
          ) : null}
          {assetLinks.thumbnailUrl ? (
            <a
              href={assetLinks.thumbnailUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border border-line px-3 py-1.5"
            >
              Open Thumbnail
            </a>
          ) : null}
          {assetLinks.spzUrl ? (
            <a
              href={assetLinks.spzUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border border-line px-3 py-1.5"
            >
              Download SPZ
            </a>
          ) : null}
        </div>
      </div>
    );
  }

  if (mode === "splat") {
    return (
      <div className="space-y-2">
        <canvas
          ref={canvasRef}
          className="h-[70vh] w-full rounded-2xl border border-line bg-[#101622]"
        />
        <p className="text-xs text-foreground/70">{cameraHint}</p>
      </div>
    );
  }

  return (
    <div className="flex h-[70vh] w-full flex-col items-center justify-center rounded-2xl border border-dashed border-line bg-[#f4f2ea] p-6 text-center">
      <p className="text-lg font-semibold">Interactive payload unavailable</p>
      <p className="mt-2 max-w-xl text-sm text-foreground/70">
        This world does not currently expose a supported interactive URL or splat asset.
        Use preview mode and retry generation with a different model/prompt.
      </p>
    </div>
  );
}
