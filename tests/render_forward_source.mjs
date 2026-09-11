import { createRequire } from 'node:module';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const skillRoot = path.join(repositoryRoot, 'src/hermes_post_design/resources/skills/creative/poster-design');
const requireFromSkill = createRequire(path.join(skillRoot, 'package.json'));
const { chromium } = requireFromSkill('playwright');
const { resolveExecutable } = await import(pathToFileURL(path.join(skillRoot, 'scripts/browser-paths.mjs')).href);

function parseArgs(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    if (!key?.startsWith('--') || argv[index + 1] === undefined) {
      throw new Error(`Invalid argument near ${key ?? '<end>'}`);
    }
    values[key.slice(2)] = argv[index + 1];
  }
  const width = Number(values.width);
  const height = Number(values.height);
  if (!values.source || !values.output || !Number.isInteger(width) || !Number.isInteger(height)) {
    throw new Error('--source, --output, --width, and --height are required');
  }
  return { source: path.resolve(values.source), output: path.resolve(values.output), width, height };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const executablePath = await resolveExecutable();
  const launchOptions = { headless: true };
  if (executablePath) launchOptions.executablePath = executablePath;
  const browser = await chromium.launch(launchOptions);
  try {
    const context = await browser.newContext({
      viewport: { width: args.width, height: args.height },
      deviceScaleFactor: 1,
      serviceWorkers: 'block',
    });
    await context.route('**/*', async (route) => {
      if (/^(?:https?|wss?):/i.test(route.request().url())) {
        await route.abort('blockedbyclient');
        return;
      }
      await route.continue();
    });
    const page = await context.newPage();
    await page.goto(pathToFileURL(args.source).href, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({
      path: args.output,
      animations: 'disabled',
      omitBackground: true,
      clip: { x: 0, y: 0, width: args.width, height: args.height },
    });
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
