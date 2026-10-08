import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const context = await chromium.launchPersistentContext(
  "C:\\tmp\\congress-pages-interchange-profile-2",
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
    "https://www.congress.gov/bill/118th-congress/house-bill/3881/cosponsors",
    { waitUntil: "domcontentloaded", timeout: 90_000 },
  );
  await page.waitForSelector("#main", { timeout: 120_000 });
  const result = await page.evaluate(() => {
    const clean = (value) =>
      String(value ?? "").replace(/\s+/g, " ").trim().slice(0, 800);
    const memberLinks = [
      ...document.querySelectorAll('a[href*="/member/"]'),
    ].map((link) => {
      const container =
        link.closest("tr, li, article, .item_table") ?? link.parentElement;
      return {
        text: clean(link.textContent),
        href: link.href,
        containerTag: container?.tagName ?? null,
        containerId: container?.id ?? null,
        containerClass: clean(container?.className),
        containerText: clean(container?.textContent),
        directChildren: container
          ? [...container.children].map((child) => ({
              tag: child.tagName,
              className: clean(child.className),
              text: clean(child.textContent),
            }))
          : [],
      };
    });
    const tables = [...document.querySelectorAll("table")].map((table) => ({
      id: table.id,
      className: clean(table.className),
      headers: [...table.querySelectorAll("th")].map((th) =>
        clean(th.textContent),
      ),
      rows: [...table.querySelectorAll("tr")]
        .slice(0, 12)
        .map((row) => clean(row.textContent)),
    }));
    return {
      url: location.href,
      title: document.title,
      mainText: clean(document.querySelector("#main")?.innerText),
      memberLinks,
      tables,
      pageSize: [...document.querySelectorAll("select")].map((select) => ({
        name: select.name,
        className: clean(select.className),
        value: select.value,
        options: [...select.options].map((option) => ({
          text: clean(option.textContent),
          value: option.value,
        })),
      })),
      pagination: [...document.querySelectorAll(".pagination a")].map(
        (link) => ({
          text: clean(link.textContent),
          aria: link.getAttribute("aria-label"),
          className: clean(link.className),
          href: link.href,
        }),
      ),
    };
  });
  console.log(JSON.stringify(result, null, 2));
} finally {
  await context.close();
}
