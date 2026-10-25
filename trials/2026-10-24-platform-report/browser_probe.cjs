const { chromium } = require('/home/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const page=await browser.newPage({viewport:{width:1440,height:1050}});
 page.on('pageerror',e=>process.stderr.write('PAGEERROR '+e.message+'\n'));
 await page.goto('http://127.0.0.1:8188/',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.app?.graph && window.app?.loadApiJson, {timeout:60000});
 const fs=require('fs');const graph=JSON.parse(fs.readFileSync('trials/2026-10-24-ubuntu-followup/qwen-ubuntu-blue.api.json','utf8'));
 const result=await page.evaluate(async graph=>{
  await window.app.loadApiJson(graph,'probe');
  const prompt=await window.app.graphToPrompt();
  return {serialized:window.app.graph.serialize(),prompt, nodeCount:window.app.graph._nodes.length};
 },graph);
 fs.writeFileSync('trials/2026-10-24-platform-report/browser-probe.json',JSON.stringify(result,null,2));
 await page.screenshot({path:'trials/2026-10-24-platform-report/workflow-probe.png',fullPage:false});
 console.log(JSON.stringify({nodeCount:result.nodeCount,serializedKeys:Object.keys(result.serialized),promptKeys:Object.keys(result.prompt)}));
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});
