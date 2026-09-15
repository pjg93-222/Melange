/* Backstop repairs.

   1. test_original_studio_contributions_browser.cjs drives controls that now
      live inside the Data source panel, and F3 folds that panel away after the
      first successful load. This is the approved behaviour (R1 draws the folded
      summary line), so the test opens the panel the way a reader does - with the
      permanent header button - and keeps it open, because settleSource folds it
      once and never again.

   2. test_chart_comparison_browser.cjs was ALREADY red before this lane: the
      2906980d1 redesign renamed its toolbar control to "Canvas only in every
      chart" / "Builder in every chart" and the test still looked for "Hide all
      options" / "Show all options". chart-comparison.js is byte-identical to
      its pre-lane backup, so this failure is not lane F-client's; it is fixed
      here so the backstop signal is usable. Its destination selects are inside
      the Data source panel too, in the page and in pane C. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\tests',
  bak: '.bak-20260914-Fc',
  eol: 'lf',
  files: [
    {
      path: 'test_original_studio_contributions_browser.cjs',
      eol: 'lf',
      edits: [
        {
          find: "  await page.waitForFunction(()=>document.querySelector('#studio-canvas svg')&&document.querySelector('#studio-verified-summary').textContent.includes('$325.00'));\n" +
            "  assert.equal(await page.locator('#studio-source-mode').inputValue(),'contributions');\n",
          replace: "  await page.waitForFunction(()=>document.querySelector('#studio-canvas svg')&&document.querySelector('#studio-verified-summary').textContent.includes('$325.00'));\n" +
            "  // The Data source panel folds itself away after the first successful load,\n" +
            "  // so open it the way a reader does. It is folded once and never again.\n" +
            "  await page.waitForFunction(()=>!document.getElementById('studio-source-details').open);\n" +
            "  await page.locator('#studio-scope-change').click();\n" +
            "  assert.equal(await page.locator('#studio-dataset').isVisible(),true);\n" +
            "  assert.equal(await page.locator('#studio-source-mode').inputValue(),'contributions');\n"
        }
      ]
    },
    {
      path: 'test_chart_comparison_browser.cjs',
      eol: 'lf',
      edits: [
        {find: "name:'Hide all options',exact:true", replace: "name:'Canvas only in every chart',exact:true", count: 3},
        {find: "name:'Show all options',exact:true", replace: "name:'Builder in every chart',exact:true", count: 2},
        {
          find: " await page.locator('#studio-destination').selectOption('recipient_state');",
          replace: " // The destination view lives in the Data source panel, which folds itself\n" +
            " // away after the first load in the page and in every pane.\n" +
            " await page.locator('#studio-scope-change').click();\n" +
            " await page.locator('#studio-destination').selectOption('recipient_state');"
        },
        {
          find: " await frame('C').locator('#studio-destination').selectOption('represented_state');",
          replace: " await frame('C').locator('#studio-scope-change').click();\n" +
            " await frame('C').locator('#studio-destination').selectOption('represented_state');"
        }
      ]
    }
  ]
};
