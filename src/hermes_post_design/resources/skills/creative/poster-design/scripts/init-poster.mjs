import { cp, mkdir, mkdtemp, readFile, rename, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(scriptDir, '..');
const starterDir = path.join(skillRoot, 'templates', 'poster-starter');
const runtimeNames = ['browser-paths.mjs', 'path-safety.mjs', 'poster-contract.mjs', 'prepare-project.mjs', 'render-poster.mjs', 'inspect-poster.mjs', 'record-visual-review.mjs'];

function parseArgs(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    if (!key?.startsWith('--') || argv[index + 1] === undefined) {
      throw new Error(`Invalid argument near ${key ?? '<end>'}`);
    }
    values[key.slice(2)] = argv[index + 1];
  }
  return values;
}

function positiveInteger(value, label) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${label} must be a positive integer`);
  }
  return parsed;
}

function canvasFor(args) {
  switch (args.type) {
    case 'digital':
      return {
        type: 'digital',
        width: positiveInteger(args.width ?? '1080', 'width'),
        height: positiveInteger(args.height ?? '1440', 'height'),
      };
    case 'long-form':
      return {
        type: 'long-form',
        width: positiveInteger(args.width ?? '1080', 'width'),
        minHeight: positiveInteger(args.height ?? '1920', 'height'),
      };
    case 'a1-landscape':
      return { type: 'print', preset: 'A1', orientation: 'landscape', widthMm: 841, heightMm: 594 };
    case 'a1-portrait':
      return { type: 'print', preset: 'A1', orientation: 'portrait', widthMm: 594, heightMm: 841 };
    case 'a0-landscape':
      return { type: 'print', preset: 'A0', orientation: 'landscape', widthMm: 1189, heightMm: 841 };
    case 'a0-portrait':
      return { type: 'print', preset: 'A0', orientation: 'portrait', widthMm: 841, heightMm: 1189 };
    default:
      throw new Error(`Unsupported poster type: ${args.type ?? '<missing>'}`);
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.output || !args.title || !args.type) {
    throw new Error('--output, --title, and --type are required');
  }

  const output = path.resolve(args.output);
  const canvas = canvasFor(args);
  const parent = path.dirname(output);
  await mkdir(parent, { recursive: true });
  let staging;
  try {
    staging = await mkdtemp(path.join(parent, `.${path.basename(output)}.tmp-`));
    await cp(starterDir, staging, { recursive: true, force: false, errorOnExist: false });
    for (const runtimeName of runtimeNames) {
      await cp(path.join(scriptDir, runtimeName), path.join(staging, 'scripts', runtimeName), { force: true });
    }

    const configPath = path.join(staging, 'poster.config.json');
    const config = JSON.parse(await readFile(configPath, 'utf8'));
    config.title = args.title;
    config.canvas = canvas;
    await writeFile(configPath, `${JSON.stringify(config, null, 2)}\n`);

    const briefPath = path.join(staging, 'brief.json');
    const brief = JSON.parse(await readFile(briefPath, 'utf8'));
    brief.facts = [{ key: 'title', value: args.title, critical: true }];
    await writeFile(briefPath, `${JSON.stringify(brief, null, 2)}\n`);

    const htmlPath = path.join(staging, 'poster.html');
    const html = (await readFile(htmlPath, 'utf8'))
      .replace('<title>Poster</title>', `<title>${escapeHtml(args.title)}</title>`)
      .replace('Poster title', escapeHtml(args.title));
    await writeFile(htmlPath, html);

    try {
      await rename(staging, output);
    } catch (error) {
      if (['EEXIST', 'ENOTEMPTY', 'EPERM'].includes(error.code)) {
        throw new Error(`Refusing to use an existing output path: ${output}`);
      }
      throw error;
    }
    staging = null;
  } finally {
    if (staging) await rm(staging, { recursive: true, force: true });
  }

  process.stdout.write(`${JSON.stringify({ success: true, output, canvas })}\n`);
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
