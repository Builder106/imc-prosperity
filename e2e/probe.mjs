// One-shot probe: verify the live app end-to-end and report real selectors + timing.
import { chromium } from '@playwright/test';

const log = (...a) => console.log(new Date().toISOString(), ...a);

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });

log('goto http://localhost:8501');
await page.goto('http://localhost:8501', { waitUntil: 'domcontentloaded' });

// Wait for the app title (RAG init happens at startup -> spinner first).
const t0 = Date.now();
await page.locator('.app-title', { hasText: 'IMC Prosperity Trading Assistant' })
  .waitFor({ state: 'visible', timeout: 360_000 });
log(`title visible after ${((Date.now() - t0) / 1000).toFixed(1)}s`);

// Inspect chat input candidates
for (const sel of ['textarea[data-testid="stChatInput"]', 'textarea[data-testid="stChatInputTextArea"]', '[data-testid="stChatInput"] textarea', '[data-testid="stChatInput"]']) {
  const n = await page.locator(sel).count();
  log(`selector ${sel} -> count ${n}`);
}
const ph = await page.locator('textarea').first().getAttribute('placeholder').catch(() => null);
log('first textarea placeholder:', ph);

// Sidebar example-prompt buttons
const btns = await page.locator('section[data-testid="stSidebar"] .stButton > button').allTextContents();
log('sidebar buttons:', JSON.stringify(btns));

// Submit a question via chat input
const input = page.locator('textarea[data-testid="stChatInputTextArea"]').first();
const inputAlt = page.locator('[data-testid="stChatInput"] textarea').first();
const box = (await input.count()) ? input : inputAlt;
log('using chat input, count =', await box.count());
await box.click();
await box.fill('What are the position limits for each product?');
await box.press('Enter');
log('question submitted');

// Wait for chat messages to appear
await page.locator('[data-testid="stChatMessage"]').first().waitFor({ state: 'visible', timeout: 30_000 });
log('user message count:', await page.locator('[data-testid="stChatMessage"]').count());

// Wait for assistant message (2 messages) and spinner detach
const t1 = Date.now();
await page.waitForFunction(
  () => document.querySelectorAll('[data-testid="stChatMessage"]').length >= 2,
  { timeout: 360_000 }
);
log(`assistant bubble appeared after ${((Date.now() - t1) / 1000).toFixed(1)}s`);

// Spinner status
const spinnerCount = await page.locator('[data-testid="stSpinner"]').count();
log('spinner count while answering:', spinnerCount);
await page.locator('[data-testid="stSpinner"]').first().waitFor({ state: 'detached', timeout: 360_000 }).catch(() => log('no spinner / already gone'));
log(`spinner detached after ${((Date.now() - t1) / 1000).toFixed(1)}s total`);

// Give Streamlit a moment to render the final markdown
await page.waitForTimeout(2000);
const assistant = page.locator('[data-testid="stChatMessage"]').nth(1);
const text = (await assistant.innerText()).slice(0, 600);
log('assistant text head:', JSON.stringify(text));

// Sources expander
const expanders = await page.locator('[data-testid="stExpander"]').allTextContents();
log('expanders:', JSON.stringify(expanders.map(e => e.slice(0, 80))));

await browser.close();
log('DONE');
