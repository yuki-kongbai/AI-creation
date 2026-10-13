const { chromium } = require('playwright-core');
(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    headless: true,
  });
  const page = await browser.newPage({ viewport: { width: 354, height: 537 }, deviceScaleFactor: 2 });
  await page.setContent(`
    <html><body style="margin:0;background:#05070e;font-family:Consolas,monospace;color:#8fa6d8">
    <div style="padding:14px;font-size:13px;line-height:1.65">
      <div style="color:#e2e8f0">world.execute(me);</div>
      <div style="color:#5b6b8a">── dsh web ──────────────</div>
      <div style="margin-top:10px;color:#7aa2f7">$ dsh plugin add dsh-whale-widget</div>
      <div style="color:#4ade80">v mounted (12ms)</div>
      <div style="color:#ffb05c">balance  Y 41.28   -0.03</div>
    </div></body></html>`);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: 'probe.png' });
  await browser.close();
  console.log('截图完成');
})().catch(e => { console.error('失败:', e.message); process.exit(1); });
