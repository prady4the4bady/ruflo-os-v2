import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

export function useWallpaper() {
  const [wallpaper, setWallpaper] = useState<string | null>(null);

  useEffect(() => {
    invoke<string | null>("get_wallpaper")
      .then((path) => {
        if (path) setWallpaper(path);
      })
      .catch(() => {
        // No wallpaper configured – leave null (CSS fallback takes over)
      });
  }, []);

  return wallpaper;
}
