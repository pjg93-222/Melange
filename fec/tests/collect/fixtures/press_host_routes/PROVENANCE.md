# press_host_routes fixtures

Recorded 2026-10-20 from the official member sites with the collector's own User-Agent
(`MelangeSystemsResearchCollector/1.0 (public-records research)`), one request at a time, at least
3 s apart, after reading each host's robots.txt (no `/wp-json/` or article path is disallowed on any
of these hosts). They back `../test_press_host_routes.R`; none of them is a live data artifact.

| File | Request | Notes |
|---|---|---|
| `husted_press_releases_slug.json` | `https://www.husted.senate.gov/wp-json/wp/v2/press_releases?slug=democrats-block-husteds-bill-forcing-data-centers-to-pay-their-own-way&_fields=id,date,date_gmt,modified,link,slug,title,content` | verbatim body |
| `kiggans_posts_slug.json` | `https://kiggans.house.gov/wp-json/wp/v2/posts?slug=kiggans-bill-to-ensure-proper-lifeguard-staffing-on-public-beaches-passes-the-house-with-bipartisan-support&_fields=...` | verbatim body |
| `lankford_press_releases_slug_stripped.json` | `https://www.lankford.senate.gov/wp-json/wp/v2/press_releases?slug=lankford-subcommittee-examines-judicial-review-in-federal-regulatory-process&_fields=id,date,link,slug,title,content` | the CDX inventory listed this post as `...-processnttnt` |
| `lankford_press_releases_search.json` | `https://www.lankford.senate.gov/wp-json/wp/v2/press_releases?search=lankford%20abraham%20accords%20caucus&per_page=20&_fields=slug,link` | the truncated listing slug `lankford-abraham-accords-caucus-` matches exactly one of these 20 |
| `lankford_press_releases_prefix_match.json` | `...press_releases?slug=lankford-abraham-accords-caucus-members-commemorate-four-year-anniversary-of-historic-agreement&_fields=id,date,link,slug,title,content` | the record the search resolves to |
| `takano_press_release.html` | `https://takano.house.gov/newsroom/press-releases/rep-takano-sen-sanders-reintroduce-32-hour-workweek-act` | `<script>`, `<style>`, `<svg>`, comments and `<link>` removed; the retired `/media-center/` and `/issues/takano.house.gov/newsroom/` forms of the same slug answer HTTP 410 |
| `algreen_press_release.html` | `https://algreen.house.gov/media/press-releases/icymi-austin-american-statesman-article-below-titled-texas-leading-nation` | same trimming; the upstream extractor returns no body for this page (it takes the whole `<body>`, which its junk filter then rejects) |

The trimmed pages were checked to give the same upstream-extractor result as the untrimmed ones.
