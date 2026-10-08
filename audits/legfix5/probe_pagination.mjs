import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const context = await chromium.launchPersistentContext(
  "C:\\tmp\\congress-pagination-profile",
  {
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    headless: false,
    ignoreDefaultArgs: ["--enable-automation"],
    args: ["--disable-blink-features=AutomationControlled"],
    viewport: { width: 1400, height: 900 },
  },
);

try {
  const page = context.pages()[0] || (await context.newPage());
  await page.goto(
    "https://www.congress.gov/index.php/advanced-search/legislation",
    { waitUntil: "domcontentloaded", timeout: 60_000 },
  );
  await page.waitForFunction(
    () => Boolean(document.querySelector("#advancedSearchLegislation")),
    undefined,
    { timeout: 120_000 },
  );
  for (const congress of [116, 117, 118, 119]) {
    await page.locator(`#congresses${congress}`).check();
  }
  await page.locator("#restrictionTypeIncludeBillText").check();
  await page.locator("#enterTerms").fill('"credit union"');
  await Promise.all([
    page.waitForNavigation({
      waitUntil: "domcontentloaded",
      timeout: 90_000,
    }),
    page
      .locator(
        "#advancedSearchLegislation button[type=submit][name=search]",
      )
      .click(),
  ]);

  const baseUrl = page.url();
  const trials = [];
  for (const pageNumber of [1, 2, 4]) {
    const trialUrl = new URL(baseUrl);
    trialUrl.searchParams.set("pageSize", "250");
    trialUrl.searchParams.set("pageSort", "documentNumber:asc");
    trialUrl.searchParams.set("page", String(pageNumber));
    await page.goto(trialUrl.href, {
      waitUntil: "domcontentloaded",
      timeout: 90_000,
    });
    const trial = await page.evaluate(() => {
      const cards = [
        ...document.querySelectorAll(
          "ol.basic-search-results-lists > li.expanded",
        ),
      ];
      const summarizeCard = (card) => {
        const heading = card.querySelector(".result-heading");
        const link = heading?.querySelector("a");
        return {
          heading: heading?.textContent.replace(/\s+/g, " ").trim() ?? null,
          href: link?.href ?? null,
        };
      };
      const mainText = document.querySelector("#main")?.innerText ?? "";
      return {
        url: location.href,
        resultHeader:
          mainText.match(/Search Results\s+[\d,-]+ of [\d,]+/)?.[0] ?? null,
        pageSize: document.querySelector(".pageSizeSelect")?.value ?? null,
        pageSort: document.querySelector("#pageSort")?.value ?? null,
        currentPage:
          document.querySelector("#currentPageNumber")?.value ?? null,
        expandedCount: cards.length,
        first: cards.length ? summarizeCard(cards[0]) : null,
        last: cards.length ? summarizeCard(cards.at(-1)) : null,
        next: document.querySelector(".pagination a.next")?.href ?? null,
      };
    });
    trials.push(trial);
  }
  console.log(JSON.stringify({ baseUrl, trials }, null, 2));
} finally {
  await context.close();
}
