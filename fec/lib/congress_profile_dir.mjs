import os from "node:os";
import path from "node:path";

// Stable, non-synced Chrome profile: %TEMP% is wiped by Storage Sense and the repo lives in OneDrive.
export function defaultCongressProfileDir(env = process.env, platform = process.platform) {
  if (platform === "win32") {
    const base = env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local");
    return path.join(base, "Melange", "congress-pages-profile");
  }
  return path.join(os.tmpdir(), "congress-pages-profile");
}
