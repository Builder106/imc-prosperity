// Probe 2: confirm full RAG answer path, real spinner selector, timing.
import { chromium } from '@playwright/test';

const log = (...a) => console.log(new Date().toISOString(), ...a);

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });

await page.goto('http://localhost:8501', { waitUntil: 'domcontentloaded' });
const t0 = Date.now();

// Chat input only exists once RAG init is done — wait for it directly.
const input = page.locator('[data-testid="stChatInput"] textarea');
await input.waitFor({ state: 'visible', timeout: 360_000 });
log(`chat input visible after ${((Date.now() - t0) / 1000).toFixed(1)}s (RAG init done)`);

await input.click();
await input.fill('What are the position limits for each product?');
await input.press('Enter');
const t1 = Date.now();
log('question submitted');

// Both bubbles appear immediately; assistant bubble holds an inline spinner.
await page.waitForFunction(
  () => document.querySelectorAll('[data-testid="stChatMessage"]').length >= 2,
  { timeout: 60_000 }
);

// Probe spinner selectors while it should be running
await page.waitForTimeout(3000);
for (const sel of ['[data-testid="stSpinner"]', '.stSpinner', '[data-testid="stStatusWidget"]']) {
  log(`spinner candidate ${sel} -> count ${await page.locator(sel).count()}`);
}
const spinnerText = page.getByText('Retrieving context and generating an answer');
log('spinner-by-text count:', await spinnerText.count());

// Wait for the spinner text to go away = answer rendered
await spinnerText.first().waitFor({ state: 'detached', timeout: 360_000 }).catch(e => log('spinner detach err', e.message));
log(`answer rendered ${((Date.now() - t1) / 1000).toFixed(1)}s after submit`);

await page.waitForTimeout(2000);
const assistant = page.locator('[data-testid="stChatMessage"]').nth(1);
const text = await assistant.innerText();
log('assistant text length:', text.length);
log('assistant text head:', JSON.stringify(text.slice(0, 500)));

// Sources expander inside the assistant message
const exp = assistant.locator('[data-testid="stExpander"]');
log('expander in assistant msg count:', await exp.count());
if (await exp.count()) log('expander label:', JSON.stringify((await exp.first().innerText()).slice(0, 120)));

await browser.close();
log('DONE');
