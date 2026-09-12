import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
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
  const sourceText = await readFile(args.source, 'utf8');
  const activeContent = [
    [/<script\b/i, 'SVG script elements are not allowed'],
    [/\son[a-z]+\s*=/i, 'SVG event handlers are not allowed'],
    [/<foreignObject\b/i, 'SVG foreignObject content is not allowed'],
    [/\bjavascript\s*:/i, 'javascript: references are not allowed'],
  ];
  for (const [pattern, message] of activeContent) {
    if (pattern.test(sourceText)) throw new Error(message);
  }
  for (const match of sourceText.matchAll(/\b(?:href|xlink:href)\s*=\s*(["'])(.*?)\1/gi)) {
    const reference = match[2].trim();
    if (reference.startsWith('#') || /^data:image\/(?:avif|gif|jpeg|png|webp);base64,/i.test(reference)) continue;
    throw new Error(`SVG must be self-contained; external reference is not allowed: ${reference}`);
  }
  const executablePath = await resolveExecutable();
  const launchOptions = { headless: true };
  if (executablePath) launchOptions.executablePath = executablePath;
  const browser = await chromium.launch(launchOptions);
  try {
    const context = await browser.newContext({
      viewport: { width: args.width, height: args.height },
      deviceScaleFactor: 1,
      serviceWorkers: 'block',
      javaScriptEnabled: false,
    });
    const sourceUrl = pathToFileURL(args.source).href;
    const blocked = [];
    await context.route('**/*', async (route) => {
      const requestUrl = route.request().url();
      if (requestUrl !== sourceUrl) {
        blocked.push(requestUrl);
        await route.abort('blockedbyclient');
        return;
      }
      await route.continue();
    });
    const page = await context.newPage();
    await page.goto(sourceUrl, { waitUntil: 'load' });
    if (blocked.length) throw new Error(`SVG requested disallowed resources: ${blocked.join(', ')}`);
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
