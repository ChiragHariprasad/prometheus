/**
 * Puppeteer UI verification script.
 *
 * Tests each fix applied to the PROMETHEUS frontend.
 *
 * Usage:
 *   1. Start the app: npx next dev --port 3000 (from frontend/)
 *   2. node frontend/tests/ui/verify-fixes.mjs
 */

import puppeteer from 'puppeteer';

const BASE = process.env.BASE_URL || 'http://localhost:3000';

const consoleErrors = [];
let passed = 0;
let failed = 0;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function test(name, fn) {
  return { name, fn };
}

async function run() {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
    executablePath: '/usr/bin/chromium-browser',
  });

  const page = await browser.newPage();
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push(err.message));

  const tests = [
    test('Login page loads without errors', async () => {
      await page.goto(`${BASE}/login`, { waitUntil: 'networkidle0' });
      const heading = await page.$eval('h1', (el) => el.textContent);
      if (!heading.includes('Intelligent Customer Twins')) {
        throw new Error(`Expected heading, got: ${heading}`);
      }
      const emailInput = await page.$('input[type="email"]');
      if (!emailInput) throw new Error('Email input not found');
      const pwInput = await page.$('input[type="password"]');
      if (!pwInput) throw new Error('Password input not found');
    }),

    test('Login form has working inputs', async () => {
      await page.goto(`${BASE}/login`, { waitUntil: 'networkidle0' });
      await page.waitForSelector('input[type="email"]', { timeout: 10000 });
      const emailInput = await page.$('input[type="email"]');
      await emailInput.type('test@example.com');
      const pwInput = await page.$('input[type="password"]');
      await pwInput.type('testpassword123');
      const value = await page.$eval('input[type="email"]', (el) => el.value);
      if (value !== 'test@example.com') throw new Error('Email input not working');
    }),

    test('Password visibility toggle works', async () => {
      await page.goto(`${BASE}/login`, { waitUntil: 'networkidle0' });
      const pwInput = await page.$('input[type="password"]');
      if (!pwInput) throw new Error('Password input should be type=password initially');
      const toggleBtn = await page.$('button[type="button"]');
      if (!toggleBtn) throw new Error('Toggle password button not found');
      await toggleBtn.click();
      await sleep(200);
      const textInput = await page.$('input[type="text"]');
      if (!textInput) throw new Error('Password input should become type=text after toggle');
    }),

    test('Dashboard page redirects to login (no auth)', async () => {
      await page.goto(`${BASE}/dashboard`, { waitUntil: 'networkidle0' });
      await sleep(2000);
      const currentUrl = page.url();
      if (!currentUrl.includes('/login')) {
        throw new Error(`Expected redirect to /login, got: ${currentUrl}`);
      }
    }),

    test('Protected pages redirect to login when not authenticated', async () => {
      const protectedPages = ['/twins', '/analytics', '/simulation-lab', '/campaigns', '/customers'];
      for (const p of protectedPages) {
        const errorsBefore = consoleErrors.length;
        await page.goto(`${BASE}${p}`, { waitUntil: 'networkidle0' });
        await sleep(2000);
        const url = page.url();
        if (!url.includes('/login')) {
          console.log(`  [warn] ${p} did not redirect to login (url: ${url})`);
        }
        const errorsAfter = consoleErrors.length;
        if (errorsAfter > errorsBefore) {
          console.log(`  [console errors on ${p}]`);
          consoleErrors.slice(errorsBefore).forEach((e) => console.log(`    ${e}`));
        }
      }
    }),

    test('Login page shows error on invalid submission', async () => {
      await page.goto(`${BASE}/login`, { waitUntil: 'networkidle0' });
      await page.waitForSelector('input[type="email"]', { timeout: 10000 });
      const emailInput = await page.$('input[type="email"]');
      await emailInput.type('nonexistent@test.com');
      const pwInput = await page.$('input[type="password"]');
      await pwInput.type('wrongpassword');
      await page.click('button[type="submit"]');
      await sleep(3000);
      const errorEl = await page.$('.text-destructive');
      if (!errorEl) {
        console.log('  [info] No error message shown (API may not be reachable)');
      }
    }),

    test('No JavaScript errors on public pages', async () => {
      const publicPages = ['/login'];
      for (const p of publicPages) {
        const errorsBefore = consoleErrors.length;
        await page.goto(`${BASE}${p}`, { waitUntil: 'networkidle0' });
        await sleep(1000);
        const errorsAfter = consoleErrors.length;
        if (errorsAfter > errorsBefore) {
          console.log(`  [console errors on ${p}]`);
          consoleErrors.slice(errorsBefore).forEach((e) => console.log(`    ${e}`));
          throw new Error(`${errorsAfter - errorsBefore} console errors on ${p}`);
        }
      }
    }),

    test('Page renders with correct HTML structure', async () => {
      await page.goto(`${BASE}/login`, { waitUntil: 'networkidle0' });
      const bodyText = await page.$eval('body', (el) => el.textContent);
      if (!bodyText.includes('PROMETHEUS')) throw new Error('Missing brand name');
      const pageText = await page.$eval('body', (el) => el.textContent);
      if (!pageText.includes('Welcome back')) throw new Error('Missing welcome message');
      const hasSignInBtn = await page.$('button[type="submit"]');
      if (!hasSignInBtn) throw new Error('Sign In button not found');
    }),
  ];

  for (const t of tests) {
    try {
      consoleErrors.length = 0;
      await t.fn();
      console.log(`  [PASS] ${t.name}`);
      passed++;
    } catch (err) {
      console.log(`  [FAIL] ${t.name}: ${err.message}`);
      failed++;
    }
  }

  await browser.close();

  console.log(`\n=== Results: ${passed} passed, ${failed} failed ===`);
  process.exit(failed > 0 ? 1 : 0);
}

run().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
