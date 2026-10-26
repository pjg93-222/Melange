import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";
import { defaultCongressProfileDir } from "../lib/congress_profile_dir.mjs";

test("windows default is under LOCALAPPDATA, not temp", () => {
  const dir = defaultCongressProfileDir({ LOCALAPPDATA: "C:/Users/x/AppData/Local" }, "win32");
  assert.equal(dir, path.join("C:/Users/x/AppData/Local", "Melange", "congress-pages-profile"));
});

test("windows falls back to homedir AppData/Local", () => {
  const dir = defaultCongressProfileDir({}, "win32");
  assert.ok(dir.endsWith(path.join("AppData", "Local", "Melange", "congress-pages-profile")));
});

test("non-windows uses tmpdir", () => {
  assert.ok(defaultCongressProfileDir({}, "linux").endsWith("congress-pages-profile"));
});
