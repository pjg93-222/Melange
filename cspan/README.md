# C-SPAN video scraper (chromote / headless Chrome)

Harvests C-SPAN **Videos** search results and, for each program page, extracts
the speaker-labelled **transcript** plus the **HLS media URL** (so audio can be
played / downloaded). Built for the member-guest interview format — the
`Rep./Sen. <Name> on <Topic>` segments (e.g. *"Rep. Adam Smith on Trump
Administration Foreign Affairs and Military Policies"*) — but it captures every
speaker turn and leaves roster attribution to the downstream resolver.

Default query = **Washington Journal** (`seriesid=13`), Videos, 2020-01-01 →
2025-12-31, most-recent-event first (9,666 programs as of build).

---

## ⚠️ Access / authorization

C-SPAN actively discourages automated access, so read this before running:

* **robots.txt** disallows named AI crawlers (`ClaudeBot`, `GPTBot`, …)
  site-wide, and disallows `/transcript`, `/ajax`, `/common/services` for **all**
  user agents. It sets `Crawl-delay: 4`.
* **CloudFront** intermittently returns `403` to automated clients.
* A **real headless Chrome (chromote) is not blocked** — the 403s target obvious
  bot fingerprints, not a genuine browser.

This tool therefore runs an **honest** headless Chrome: real Chrome UA, real
headers, real viewport, and it **respects a crawl-delay**. It does **not** spoof
TLS fingerprints, rotate proxies, or solve CAPTCHAs. **Run it only with
authorization for the content** (the underlying congressional footage is federal
public record; C-SPAN's site terms are a separate matter — that's the operator's
call, made here explicitly).

---

## Prerequisites

* **R ≥ 4.x** with packages: `chromote`, `jsonlite` (both already installed on
  this machine — R 4.6.0, chromote 0.5.1).
* **Google Chrome** (auto-detected by chromote).
* **ffmpeg** — *only* if you want `--audio` (MP3 extraction). Not required for
  text. Install: `winget install Gyan.FFmpeg` or `choco install ffmpeg`, or pass
  `--ffmpeg "C:\path\to\ffmpeg.exe"`.

Run with the full path to Rscript if it's not on PATH:
`"C:\Program Files\R\R-4.6.0\bin\Rscript.exe"`.

---

## Usage

```sh
# 1) SEARCH — paginate through #loadmore, write the program manifest
Rscript cspan_scrape.R search [--url U] [--max N] [--out DIR] [--loaddelay 2]

# 2) SCRAPE — visit each program page, extract transcript + media URL
Rscript cspan_scrape.R scrape [--members-only] [--max N] [--audio]
                              [--delay 4] [--out DIR] [--force]

# one-off / debug a single program (by URL or numeric id)
Rscript cspan_scrape.R one <program-url-or-id> [--audio] [--out DIR]

# download audio for one program id via ffmpeg
Rscript cspan_scrape.R audio <program-id> [--ffmpeg PATH] [--out DIR]

# progress summary
Rscript cspan_scrape.R status [--out DIR]
```

Typical member-interview run:

```sh
Rscript cspan_scrape.R search --out D:/cspan_out
Rscript cspan_scrape.R scrape --members-only --out D:/cspan_out
```

### Flags

| flag | default | meaning |
|------|---------|---------|
| `--out DIR` | `%MONEYBALL_ROOT%\cspan_out` | output directory |
| `--url U` | the WJ series-13 query | override the search URL (any C-SPAN Videos search) |
| `--max N` | (all) | cap number of results / programs (testing) |
| `--members-only` | off | scrape only programs whose **title** looks like a member guest |
| `--audio` | off | also extract `<id>.mp3` via ffmpeg |
| `--delay S` | `4` | seconds between distinct **page loads** (honours Crawl-delay) |
| `--loaddelay S` | `2` | seconds between `#loadmore` clicks (same page, XHR append) |
| `--ffmpeg P` | `ffmpeg` | path to ffmpeg |
| `--force` | off | re-scrape programs already captured |
| `--no-block` | off | don't block images/fonts/media/ads (slower; only if a page misrenders) |

Both stages are **resumable** — `scrape` skips any program whose
`transcripts/<id>.json` already exists (use `--force` to redo, e.g. to pick up a
transcript C-SPAN published after your first pass).

---

## Output (`<out>/`)

```
videos.csv               manifest: id,url,title,date,last_aired,abstract,member_guess
transcripts/<id>.json    per-program record (metadata + media_url + merged turns)
turns.csv                flat per-turn rows (see below)
audio/<id>.mp3           only with --audio
```

`transcripts/<id>.json`:

```json
{ "id":"670729", "url":"https://www.c-span.org/program/washington-journal/.../670729",
  "title":"Rep. Adam Smith on ...", "page_title":"...", "date":"2025-12-19",
  "media_url":"https://m3u8-0.c-spanvideo.org/program/program.670729.tsc.m3u8",
  "n_turns":135,
  "turns":[ {"offset":31,"time":"00:00:31","name":"Adam Smith","role":"","text":"..."} , ... ] }
```

`turns.csv` columns: `id,url,title,date,seq,time,offset,speaker,role,is_member_role,nwords,text`.

---

## How extraction works (important for data quality)

* **Search results**: iterates `#search-results h3`, resolves each to its
  enclosing `a.title` for the program URL. Ad rows carry no `<h3>`, so they drop
  out. `#loadmore` is clicked until it disappears / results stop growing.
* **Transcript**: reads `#video-transcript-table tr`. Per row the speaker name is
  the first `<strong>`, the role is `strong.transcript-cr-title`, the text is
  `p.transcript-text`. The full text is already in the DOM (the "Show More" link
  is CSS-only), but we still click any visible toggle first, per spec.
* **Carry-forward**: a speaker's turn spans many rows; only the **first** row has
  the `<strong>` name — continuation rows have an **empty** `<strong>`. The
  scraper carries the last named speaker forward onto empty rows, then merges
  consecutive same-speaker rows into one flowing turn. (Without this, member
  speech gets truncated under blank speakers.)
* **Media / audio**: the HLS master playlist is
  `https://m3u8-0.c-spanvideo.org/program/program.<ID>.tsc.m3u8` (read from the
  page, with the id-derived URL as fallback). It carries AAC audio + multiple
  video renditions. `--audio` runs ffmpeg to pull an MP3.

### Attribution is NOT done here (by design)

The transcript includes the **host** (e.g. Greta Brawner), **callers**, and
sometimes **news-clip** captions (which appear with mis-captioned names like
`PRES. TRUMP` and drop naturally). This scraper captures **every** turn verbatim
and marks nothing as authoritative. Deciding which turns are the 533 current
members of Congress is the job of the downstream roster resolver
(`fec/fetch_interviews.py` style `resolve_full` — full-name/nickname match,
drop-never-guess). `member_guess` in `videos.csv` is only a recall-favouring
**prefilter** to save scraping effort; former members and look-alikes are meant
to be filtered later.

Text is C-SPAN closed-caption **UPPERCASE**; whitespace is collapsed but casing
is preserved verbatim (no lossy normalization).

### Known edge cases

* **No transcript**: recent airings often have no transcript yet → `n_turns:0`.
  These are recorded (and skipped on re-run); re-fetch later with `--force`.
* **Embedded clips** inside a segment add non-member turns with rough captions;
  they don't corrupt the member's own turns (separated by host/other labels).
