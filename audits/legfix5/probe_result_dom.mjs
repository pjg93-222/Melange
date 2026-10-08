import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const context = await chromium.launchPersistentContext(
  "C:\\tmp\\congress-result-dom-profile",
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
  await page
    .locator("#enterTerms")
    .fill('"Credit Card Competition Act" OR "routing mandate"~3');
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

  const result = await page.evaluate(() => {
    const cards = [
      ...document.querySelectorAll(
        "ol.basic-search-results-lists > li.expanded",
      ),
    ];
    const summarize = (node) => ({
      tag: node.tagName,
      id: node.id,
      className: node.className,
      text: node.textContent.replace(/\s+/g, " ").trim().slice(0, 400),
    });
    const summarizeCard = (card) =>
      card
        ? {
            directChildren: [...card.children].map(summarize),
            classifiedDescendants: [...card.querySelectorAll("[class]")]
              .slice(0, 100)
              .map(summarize),
          }
        : null;
    const amendment = cards.find((card) =>
      /S\.Amdt\./i.test(
        card.querySelector(".result-heading")?.textContent ?? "",
      ),
    );
    return {
      url: location.href,
      title: document.title,
      bill: summarizeCard(cards[0]),
      amendment: summarizeCard(amendment),
    };
  });
  console.log(JSON.stringify(result, null, 2));
} finally {
  await context.close();
}
