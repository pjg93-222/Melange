import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const profile = "C:\\tmp\\congress-browser-profile";
const chrome = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const advancedSearch =
  "https://www.congress.gov/index.php/advanced-search/legislation";

const context = await chromium.launchPersistentContext(profile, {
  executablePath: chrome,
  headless: false,
  ignoreDefaultArgs: ["--enable-automation"],
  args: ["--disable-blink-features=AutomationControlled"],
  viewport: { width: 1400, height: 900 },
});

try {
  const page = context.pages()[0] || (await context.newPage());
  await page.goto(advancedSearch, {
    waitUntil: "domcontentloaded",
    timeout: 60_000,
  });

  for (const congress of [116, 117, 118, 119]) {
    await page.locator(`#congresses${congress}`).check();
  }
  await page.locator("#restrictionTypeIncludeBillText").check();
  await page.locator("#enterTerms").fill('"Credit Card Competition Act"');

  await Promise.all([
    page.waitForNavigation({
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    }),
    page
      .locator(
        "#advancedSearchLegislation button[type=submit][name=search]",
      )
      .click(),
  ]);
  await page.waitForTimeout(3_000);

  console.log("URL", page.url());
  console.log("TITLE", await page.title());
  const resultSummary = await page
    .locator("main")
    .innerText()
    .then((text) => text.match(/\d+-\d+ of [\d,]+/)?.[0] || null);
  console.log("RESULT_SUMMARY", resultSummary);

  const downloadLink = page.locator("a").filter({ hasText: "Download Results" });
  console.log("DOWNLOAD_LINK_COUNT", await downloadLink.count());
  await downloadLink.click();
  await page.waitForTimeout(500);

  const dialogs = await page
    .locator('[role="dialog"], .modal:visible')
    .evaluateAll((nodes) =>
      nodes.map((node) => ({
        id: node.id,
        className: node.className,
        text: node.innerText,
        controls: [...node.querySelectorAll("input,button,select")].map(
          (control) => ({
            tag: control.tagName,
            type: control.type,
            name: control.name,
            id: control.id,
            value: control.value,
            checked: control.checked,
            text: control.innerText,
          }),
        ),
      })),
    );
  console.log("DIALOGS", JSON.stringify(dialogs, null, 2));

  const downloadDialog = page.locator(".congress-default-modal:visible");
  await downloadDialog.locator("#checkAll").check();
  const downloadPromise = page.waitForEvent("download", { timeout: 60_000 });
  await downloadDialog
    .locator("button")
    .filter({ hasText: "Download Results" })
    .click();
  const download = await downloadPromise;
  const destination = path.resolve(
    "audits",
    "legfix5",
    "probe_credit_card_competition.csv",
  );
  await download.saveAs(destination);
  console.log("SAVED", destination);
} finally {
  await context.close();
}
