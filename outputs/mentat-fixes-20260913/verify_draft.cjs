const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require('C:/Users/pgoff/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{const browser=await chromium.launch({headless:true,channel:'chrome'});try{
const page=await browser.newPage({viewport:{width:1024,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.setContent('<!doctype html><html style="color-scheme:light"><body style="margin:0">'+fs.readFileSync('C:/Users/pgoff/.codex/visualizations/2026/09/13/01a098d0-0ca2-7ed0-9f70-03dc6a336893/mentat-chart-drafts.html','utf8')+'</body></html>');
await page.locator('#draft-a-cycle').selectOption('2026');assert.equal(await page.locator('#draft-b-cycle').inputValue(),'2024');
await page.locator('#draft-a-company').selectOption('example');assert.equal(await page.locator('#draft-b-company').inputValue(),'example');
await page.locator('#draft-link-company').uncheck();await page.locator('#draft-a-company').selectOption('all');assert.equal(await page.locator('#draft-b-company').inputValue(),'example');
await page.locator('#draft-link-state').check();await page.locator('#draft-a-state').selectOption('Virginia');assert.equal(await page.locator('#draft-b-state').inputValue(),'Virginia');
await page.locator('#draft-link-state').uncheck();await page.locator('#draft-b-state').selectOption('Texas');assert.equal(await page.locator('#draft-a-state').inputValue(),'Virginia');
await page.locator('#draft-b-type').selectOption('table');assert.equal(await page.locator('#draft-chart-b table').count(),1);assert.equal(await page.locator('#draft-chart-a .bars').count(),1);
await page.locator('#draft-a-state').selectOption('all');await page.locator('#draft-b-state').selectOption('all');await page.locator('#draft-b-type').selectOption('bars');
await page.screenshot({path:path.join(__dirname,'draft-desktop.png'),fullPage:true});
await page.locator('[data-view="workbook"]').click();await page.locator('[data-sheet="receipts"]').click();assert.match(await page.locator('#draft-table').textContent(),/Cycle-specific candidate link/);
for(const width of [1024,736,390,320]){await page.setViewportSize({width,height:1000});await page.locator('[data-view="charts"]').click();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Overflow at '+width);}
await page.screenshot({path:path.join(__dirname,'draft-mobile.png'),fullPage:true});assert.deepEqual(errors,[]);console.log('Draft verified: independent panes, optional linked filters, workbook tabs, 320–1024px.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
