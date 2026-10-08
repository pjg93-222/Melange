const {chromium}=require(require.resolve('playwright',{paths:[require('path').join(require('os').homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules')]}));
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const base=process.env.MENTAT_VERIFY_URL||'http://127.0.0.1:8837';
(async()=>{
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  const page=await browser.newPage({viewport:{width:1440,height:1050},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const results=[];
  try {
    for(const [id,year,amount] of [
      ['fairshake-20260908','2024','$106,708.00'],
      ['fairshake-20260908','2026','$7,170,138.40'],
      ['snapshot-2eb1b6d618fa4595b4ddbe8043753ede','2026','$7,170,138.40']]) {
      await page.goto(base+`/?a.source=snapshot&a.id=${id}&a.committee=C00835959&a.cycle=${year}#evidence`);
      await page.locator('[data-pane=a] .pane-rows').waitFor({timeout:45000});
      await page.waitForFunction(()=>!document.querySelector('[data-pane=a] .pane-message'),{},{timeout:45000});
      await page.locator('[data-pane=a] .pane-rows').click();
      const network=page.locator('[data-pane=a] .evidence-network');
      await network.getByRole('searchbox').fill('Andy Barr');
      const rows=network.locator('tbody tr:visible');
      assert.equal(await rows.count(),1);
      const text=await rows.innerText();
      assert.ok(text.includes(amount),text);
      assert.match(text,/FAIRSHAKE.*DEFEND AMERICAN JOBS/s);
      assert.match(text,/C00835959.*C00836221/s);
      assert.match(await network.innerText(),/Backing is assumed from recorded PAC transfers/);
      results.push({id,year,amount,text});
    }
    await page.locator('.evidence-network').screenshot({path:path.join(__dirname,'evidence-desktop.png')});
    await page.setViewportSize({width:390,height:844});
    const dimensions=await page.evaluate(()=>({viewport:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
    assert.ok(dimensions.scroll<=dimensions.viewport+1,JSON.stringify(dimensions));
    await page.locator('.evidence-network').screenshot({path:path.join(__dirname,'evidence-mobile.png')});
    await page.setViewportSize({width:1440,height:1050});
    await page.goto(base+'/?industry=Crypto&cycle=2026&drawer=C00835959&drawerDirection=Support#graph');
    const explorer=page.locator('.graph-explorer');
    await explorer.waitFor({timeout:60000});
    await explorer.getByRole('searchbox').fill('Andy Barr');
    assert.equal(await explorer.locator('tbody tr').count(),1);
    assert.match(await explorer.locator('tbody tr').innerText(),/7,170,138\.40/);
    assert.equal(await explorer.getByRole('checkbox').isChecked(),true);
    await explorer.locator('tbody tr button').first().click();
    const detail=explorer.getByRole('region',{name:'Selected candidate evidence'});
    assert.match(await detail.innerText(),/C00835959.*C00836221/s);
    await detail.getByRole('button',{name:'C00835959',exact:true}).click();
    assert.equal(await explorer.locator('tbody tr').count(),1,'Focusing the upstream PAC retains descendant spending');
    await explorer.screenshot({path:path.join(__dirname,'graph-desktop.png')});
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(__dirname,'browser-results.json'),JSON.stringify({base,results,dimensions,errors,graph:'Andy Barr found by natural name; root focus retains descendant'},null,2));
    console.log('PASS: three real snapshot selections, exact amounts, named routes, natural-name search, mobile containment, Graph descendant focus.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
