const fs = require('fs');
const {chromium} = require('playwright');
(async () => {
  const catalog = JSON.parse(fs.readFileSync('workflows/catalog.json'));
  const job = catalog.workflows.find(j => j.id === 'linux-coverage-turbo-un-t2i-stage-nobacking--sample');
  const ui = JSON.parse(fs.readFileSync(job.ui));
  const browser = await chromium.launch({executablePath:'/usr/bin/google-chrome',args:['--no-sandbox','--disable-dev-shm-usage']});
  try {
    const page = await browser.newPage({viewport:{width:1600,height:1100}});
    await page.goto('http://127.0.0.1:8188/', {waitUntil:'domcontentloaded'});
    await page.waitForFunction(() => window.app?.loadGraphData);
    await page.evaluate(async ui => {await app.loadGraphData(ui,true,true)}, ui);
    const exported = await page.evaluate(async () => (await app.graphToPrompt()).output);
    const expected = JSON.parse(fs.readFileSync(job.api));
    for (const [id,node] of Object.entries(expected)) {
      if (exported[id]?.class_type !== node.class_type) throw Error('Changed class '+id);
      for (const [name,value] of Object.entries(node.inputs))
        if (JSON.stringify(value)!==JSON.stringify(exported[id].inputs[name])) throw Error('Changed input '+id+'.'+name);
    }
    await page.screenshot({path:'trials/2026-10-24-linux-coverage/installed-qwen-workflow.png'});
    const queued = await page.evaluate(async () => {
      const queue = await (await fetch('/queue')).json();
      if (queue.queue_running.length || queue.queue_pending.length) throw Error('Queue not empty');
      for(const node of app.graph._nodes) if(node.type==='SaveImage') node.widgets.find(w=>w.name==='filename_prefix').value='linux-coverage-webui-turbo-sample';
      return (await app.graphToPrompt()).output;
    });
    fs.writeFileSync('trials/2026-10-24-linux-coverage/webui-enqueued.api.json',JSON.stringify(queued,null,2));
    const responsePromise = page.waitForResponse(r => r.url().endsWith('/prompt') && r.request().method()==='POST');
    const queueResult = await page.evaluate(async () => app.queuePrompt(0,1));
    const response = await responsePromise;
    const receipt = {status:response.status(),response:await response.json(),queueResult,
      source:job.ui,source_inputs_preserved:true,only_execution_change:'SaveImage filename_prefix for separate new evidence'};
    fs.writeFileSync('trials/2026-10-24-linux-coverage/webui-queue-receipt.json',JSON.stringify(receipt,null,2));
    console.log(JSON.stringify(receipt));
  } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
