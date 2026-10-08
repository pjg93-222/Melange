from pathlib import Path
p=Path('outputs/tabs-polish-20260921/capture.cjs')
s=p.read_text()
s=s.replace("viewport:{width:1440,height:1050}","viewport:{width:1168,height:880}")
s=s.replace("process.env.UI_PHASE||'before'","process.env.UI_PHASE||'after'")
s=s.replace("id:'Synthetic',label:'Fictional credit union sample'","id:'Credit Unions',label:'Credit Unions'")
s=s.replace("for(const width of [1440,390])", "for(const width of [1168,900,390])")
s=s.replace("height:width===1440?1050:844", "height:width===1168?880:844")
s=s.replace("width:1440,height:1050", "width:1168,height:880")
s=s.replace("    let extraSnapshot=false;", """    crossReference.report.digest_available=true;
    crossReference.report.digest={basis:'Synthetic inspection threshold: $100,000.00. No production evidence is shown.',refunds:{
      linked_count:1,linked:[{company:savedEvidence.company,cycle:2024,refund_amount:-2000,original_amount:50000,refund_record_id:'R1',original_record_id:'O1',refund_source_url:'https://docquery.fec.gov/pdf/333/three.pdf',original_source_url:'https://docquery.fec.gov/pdf/000/orig.pdf'}],
      unlinked_count:1,unlinked:[{company:savedEvidence.company,cycle:2024,amount:-7500,description:'RETURN OF ERRONEOUS DEBIT',record_id:'U1'}]},outliers:{
      non_giving_count:1,non_giving:[{company:savedEvidence.company,cycle:2024,amount:15000,role:'other_receipt',description:'LOAN',record_id:'N1',source_url:'https://docquery.fec.gov/pdf/111/one.pdf'}],
      large_count:1,large:[{company:savedEvidence.company,cycle:2024,amount:120000,entity:'IND',record_id:'L1',source_url:'https://docquery.fec.gov/pdf/444/four.pdf'}]}};
    let extraSnapshot=false;""")
s=s.replace("      return route.fulfill({json:{status:'ready'", """      if(panels.trends){panels.trends.columns=[{key:'cycle',label:'Cycle',type:'text'},{key:'amount_cents',label:'Amount',type:'money'}];panels.trends.rows=['2021-2022','2023-2024','2025-2026'].map((cycle,i)=>({cycle,funding_source:'employee_original',amount_cents:[80000,120000,145000][i]}));}
      if(panels.changes){panels.changes.cards=[{funding_source:'employee_original',baseline_cents:120000,current_cents:145000,reconciled:true}];panels.changes.columns=[{key:'component',label:'Component',type:'text'},{key:'change_cents',label:'Change',type:'money'}];panels.changes.rows=[['Continuing observed companies',15000],['Newly observed companies',18000],['No longer observed companies',-8000]].map(([component,change_cents])=>({component,change_cents,funding_source:'employee_original'}));}
      return route.fulfill({json:{status:'ready'""")
s=s.replace("        await page.screenshot({path:path.join(out,`${phase}-${tab}-${width}.png`),fullPage:true});", """        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,tab+' must not overflow at '+width);
        if(process.env.MENTAT_UI_SCREENSHOTS){
          await page.screenshot({path:path.join(out,`${phase}-${tab}-${width}.png`),fullPage:true});
          if(width===1168)await page.screenshot({path:path.join(out,`${phase}-${tab}-reference-size.png`),fullPage:false});
        }""")
s=s.replace("    if(!process.env.REMAINING_ONLY)await capture('loading');", """    await page.fill('#sector','Credit Unions');
    await page.locator('.company-name').fill(savedEvidence.company);
    await page.click('#add-company');
    await page.locator('.remove-company').last().focus();await page.keyboard.press('Enter');
    assert.equal(await page.evaluate(()=>document.activeElement.classList.contains('company-name')),true,'Removing a company restores focus to the surviving input');
    await page.click('#review-roster');await page.waitForSelector('#upload-review:not([hidden])');
    assert.equal(await page.locator('#start').isDisabled(),true,'Review never starts collection without a key');
    await capture('loading');""")
s=s.replace("    if(!process.env.REMAINING_ONLY)await capture('collection');", """    await capture('collection');
    await page.locator('#collection-coverage-details > summary').click();
    assert.match(await page.locator('#collection-coverage').innerText(),/Stale coverage/);
    await page.locator('#collection-coverage-details > summary').click();
    await page.locator('#collection-freshness-details > summary').click();
    assert.match(await page.locator('#report-freshness').innerText(),/verified/);
    await page.evaluate(()=>{const notice=document.getElementById('error');notice.classList.remove('error');notice.textContent='Run restored.';notice.hidden=false;});""")
s=s.replace("if(!process.env.REMAINING_ONLY)await capture('graph');", "assert.equal(await page.locator('#error').isHidden(),true,'Completed actions do not leak between tabs');await capture('graph');")
s=s.replace("    await capture('chart-studio');", """    await page.click('#studio-clear');
    await page.locator('#studio-dimensions .studio-pill').filter({hasText:'Company'}).first().click();
    await page.locator('#studio-measures .studio-pill').filter({hasText:'Amount'}).first().click();
    await page.waitForSelector('#studio-canvas svg');
    assert.equal(await page.locator('#studio-inspector').isVisible(),true,'1168px shows the Inspector as a third column');
    await capture('chart-studio');
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.locator('#studio-data-panel').isVisible(),false,'Mobile canvas is not pushed below the entire field list');
    await page.click('#studio-data-toggle');assert.equal(await page.locator('#studio-data-panel').isVisible(),true);
    await page.click('#studio-data-toggle');await page.click('#studio-scope-change');
    assert.equal(await page.locator('#studio-data-panel').isVisible(),true,'Change data reveals and focuses its source controls');
    assert.equal(await page.evaluate(()=>document.activeElement.parentElement.id),'studio-source-details');
    await page.click('#studio-data-toggle');
    await page.click('#studio-inspector-toggle');assert.equal(await page.locator('#studio-inspector').isVisible(),true);
    await page.click('#studio-inspector-close');assert.equal(await page.locator('#studio-inspector-toggle').evaluate(el=>el===document.activeElement),true);
    await page.setViewportSize({width:1168,height:880});""")
s=s.replace("await capture('cross-reference');", """await capture('cross-reference');
    const details=page.locator('.xref-adjustments'),summary=details.locator('summary');
    await summary.click();await summary.focus();
    assert.match(await details.innerText(),/-\\$7,500\\.00/);
    crossReference.report.generated_at='2026-09-11T00:00:00Z';
    await page.evaluate(()=>MentatCrossReference.refresh());
    await page.waitForFunction(()=>document.querySelector('.xref-scope').textContent.includes('2026-09-11'));
    assert.equal(await details.getAttribute('open'),'','Refreshing the same run preserves open evidence');
    assert.equal(await summary.evaluate(el=>el===document.activeElement),true,'Refreshing the same run preserves keyboard focus');
    const link=page.locator('#xref-results a').first();await link.focus();crossReference.report.generated_at='2026-09-12T00:00:00Z';
    await page.evaluate(()=>MentatCrossReference.refresh());
    assert.equal(await link.evaluate(el=>el===document.activeElement),true,'Filing links keep focus across a snapshot refresh');
    crossReference.run_id='different-run';crossReference.report.generated_at='2026-09-13T00:00:00Z';
    await page.evaluate(()=>MentatCrossReference.refresh());
    assert.equal(await details.getAttribute('open'),null,'A new run does not inherit old open evidence');
    assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);""")
s=s.replace("    console.log(JSON.stringify({phase", "    console.log('PASS six workspace layouts at 1168, 900 and 390px; roster focus, status isolation, coverage disclosures, Studio mobile panels, cross-reference refresh continuity, local requests only.');\n    console.log(JSON.stringify({phase")
Path('mentat/tests/test_workspace_polish_browser.cjs').write_text(s)
