import { access, lstat, readFile, readdir, rename, rm, stat, writeFile } from 'node:fs/promises';
import { createHash, randomUUID } from 'node:crypto';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright';
import jsQR from 'jsqr';
import { PDFDocument } from 'pdf-lib';
import { PNG } from 'pngjs';
import { collectProjectSourceHashes, installProjectResourceBoundary, isFinalStatus, validateBrief, validateConfig, validateStaticHtml } from './poster-contract.mjs';

function parseArgs(argv) {
  const flags = new Set();
  const values = {};
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item?.startsWith('--')) throw new Error(`Invalid argument: ${item}`);
    const key = item.slice(2);
    if (key === 'strict' || key === 'final') {
      flags.add(key);
      continue;
    }
    const value = argv[index + 1];
    if (value === undefined || value.startsWith('--')) throw new Error(`Missing value for --${key}`);
    values[key] = value;
    index += 1;
  }
  return { flags, values };
}

async function firstExisting(paths) {
  for (const candidate of paths) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      // Continue.
    }
  }
  return null;
}

async function resolveExecutable(choice) {
  if (choice && !['chrome', 'edge'].includes(choice)) {
    const absolute = path.resolve(choice);
    await access(absolute);
    return absolute;
  }
  const chrome = [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    `${process.env.LOCALAPPDATA ?? ''}/Google/Chrome/Application/chrome.exe`,
  ];
  const edge = [
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  ];
  return firstExisting(choice === 'edge' ? [...edge, ...chrome] : [...chrome, ...edge]);
}

function viewportFor(canvas) {
  if (canvas.type === 'digital') return { width: canvas.width, height: canvas.height };
  if (canvas.type === 'long-form') return { width: canvas.width, height: canvas.minHeight };
  if (canvas.type === 'print') {
    const pxPerMm = 96 / 25.4;
    return { width: Math.round(canvas.widthMm * pxPerMm), height: Math.round(canvas.heightMm * pxPerMm) };
  }
  throw new Error(`Unsupported canvas type: ${canvas.type}`);
}

function configuredCss(canvas) {
  if (canvas.type === 'print') {
    return `:root { --canvas-width: ${canvas.widthMm}mm; --canvas-height: ${canvas.heightMm}mm; --page-width: ${canvas.widthMm}mm; --page-height: ${canvas.heightMm}mm; }`;
  }
  const height = canvas.type === 'long-form' ? canvas.minHeight : canvas.height;
  return `:root { --canvas-width: ${canvas.width}px; --canvas-height: ${height}px; --page-width: ${canvas.width}px; --page-height: ${height}px; }`;
}

function finding(code, message, evidence = {}) {
  return { code, message, evidence };
}

function normalizeFact(value) {
  return String(value ?? '').normalize('NFC').replace(/\s+/g, ' ').trim();
}

function expectedOutputDimensions(canvas, png) {
  if (canvas.type === 'digital') {
    return {
      png: { width: canvas.width, height: canvas.height, exactHeight: true },
      pdf: { width: canvas.width * 72 / 96, height: canvas.height * 72 / 96 },
    };
  }
  if (canvas.type === 'long-form') {
    return {
      png: { width: canvas.width, height: canvas.minHeight, exactHeight: false },
      pdf: png ? { width: png.width * 72 / 96, height: png.height * 72 / 96 } : null,
    };
  }
  return {
    png: {
      width: Math.round(canvas.widthMm * 96 / 25.4),
      height: Math.round(canvas.heightMm * 96 / 25.4),
      exactHeight: true,
    },
    pdf: { width: canvas.widthMm * 72 / 25.4, height: canvas.heightMm * 72 / 25.4 },
  };
}

function pointSizeMatches(actual, expected, tolerance = 1) {
  return Math.abs(actual.width - expected.width) <= tolerance
    && Math.abs(actual.height - expected.height) <= tolerance;
}

function pngContentEvidence(png, maxSamples = 20_000) {
  const pixelCount = png.width * png.height;
  const step = Math.max(1, Math.floor(pixelCount / maxSamples));
  let samples = 0;
  let transparent = 0;
  let minLuma = 255;
  let maxLuma = 0;
  const colorBuckets = new Set();
  for (let pixel = 0; pixel < pixelCount; pixel += step) {
    const offset = pixel * 4;
    const red = png.data[offset];
    const green = png.data[offset + 1];
    const blue = png.data[offset + 2];
    const alpha = png.data[offset + 3];
    samples += 1;
    if (alpha === 0) transparent += 1;
    const luma = Math.round((red * 299 + green * 587 + blue * 114) / 1000);
    minLuma = Math.min(minLuma, luma);
    maxLuma = Math.max(maxLuma, luma);
    colorBuckets.add(`${red >> 4}-${green >> 4}-${blue >> 4}-${alpha >> 4}`);
  }
  return {
    samples,
    transparentRatio: samples ? transparent / samples : 1,
    lumaRange: maxLuma - minLuma,
    colorBuckets: colorBuckets.size,
  };
}

async function sourceDetails(project, blockers) {
  const files = [
    path.join(project, 'poster.html'),
    path.join(project, 'styles.css'),
    path.join(project, 'brief.json'),
    path.join(project, 'poster.config.json'),
  ];

  async function walk(directory) {
    let entries;
    try {
      entries = await readdir(directory, { withFileTypes: true });
    } catch (error) {
      if (error.code === 'ENOENT') return;
      throw error;
    }
    for (const entry of entries) {
      const entryPath = path.join(directory, entry.name);
      if (entry.isDirectory()) await walk(entryPath);
      else if (entry.isFile()) files.push(entryPath);
    }
  }

  await walk(path.join(project, 'assets'));
  const details = [];
  for (const sourcePath of files) {
    try {
      const sourceStat = await stat(sourcePath);
      if (!sourceStat.isFile()) {
        blockers.push(finding('SOURCE_INVALID', 'Project source is not a regular file.', { path: sourcePath }));
        continue;
      }
      details.push({ path: sourcePath, modifiedMs: sourceStat.mtimeMs });
    } catch (error) {
      blockers.push(finding('SOURCE_MISSING', 'Required project source is missing.', {
        path: sourcePath,
        error: error.code ?? error.message,
      }));
    }
  }
  return details;
}

async function projectOutputPath(project, configured, fallback) {
  const value = configured ?? fallback;
  if (typeof value !== 'string' || value.trim() === '' || path.isAbsolute(value)) {
    throw new Error(`Output path must be a relative file inside the project directory: ${String(value)}`);
  }
  if (value !== path.basename(value) || value.includes('/') || value.includes('\\')) {
    throw new Error(`Output path must be a direct file in the project directory: ${value}`);
  }
  const outputPath = path.resolve(project, value);
  const relative = path.relative(project, outputPath);
  if (!relative || relative === '..' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    throw new Error(`Output path must stay inside the project directory: ${value}`);
  }
  let current = project;
  for (const segment of relative.split(path.sep)) {
    current = path.join(current, segment);
    try {
      if ((await lstat(current)).isSymbolicLink()) {
        throw new Error(`Output path must not use symbolic links: ${value}`);
      }
    } catch (error) {
      if (error.code === 'ENOENT') break;
      throw error;
    }
  }
  return outputPath;
}

async function inspectOutputs(project, config, blockers, outputPaths) {
  const evidence = { png: null, pngContent: null, mobile: null, pdf: null };
  const { pngPath, mobilePath, pdfPath } = outputPaths;
  let png;

  for (const [kind, outputPath] of [['PNG', pngPath], ['mobile PNG', mobilePath], ['PDF', pdfPath]]) {
    try {
      const details = await stat(outputPath);
      if (!details.isFile() || details.size === 0) {
        blockers.push(finding('OUTPUT_EMPTY', `${kind} output is empty or is not a file.`, { path: outputPath, bytes: details.size }));
      }
    } catch (error) {
      blockers.push(finding('OUTPUT_MISSING', `${kind} output is missing.`, { path: outputPath, error: error.code ?? error.message }));
    }
  }

  const sources = await sourceDetails(project, blockers);
  try {
    const renderResult = JSON.parse(await readFile(path.join(project, 'render-result.json'), 'utf8'));
    const sourceHashes = await collectProjectSourceHashes(project);
    if (renderResult.version !== 2 || JSON.stringify(renderResult.sourceHashes) !== JSON.stringify(sourceHashes)) {
      blockers.push(finding('SOURCE_HASH_MISMATCH', 'Project sources differ from the content-addressed render manifest.', {
        expected: renderResult.sourceHashes ?? null,
        actual: sourceHashes,
      }));
    }
    for (const outputPath of Object.values(outputPaths)) {
      const file = path.basename(outputPath);
      const actual = await sha256File(outputPath);
      if (renderResult.outputHashes?.[file] !== actual) {
        blockers.push(finding('OUTPUT_HASH_MISMATCH', 'Rendered output differs from the render manifest.', {
          path: outputPath,
          expected: renderResult.outputHashes?.[file] ?? null,
          actual,
        }));
      }
    }
  } catch (error) {
    blockers.push(finding('RENDER_MANIFEST_INVALID', 'render-result.json is missing, invalid, or incomplete.', {
      path: path.join(project, 'render-result.json'),
      error: error.code ?? error.message,
    }));
  }
  const newestSource = sources.reduce((latest, item) => !latest || item.modifiedMs > latest.modifiedMs ? item : latest, null);
  for (const [kind, outputPath] of [['PNG', pngPath], ['mobile PNG', mobilePath], ['PDF', pdfPath]]) {
    if (!newestSource || blockers.some((item) => item.evidence?.path === outputPath)) continue;
    const outputModifiedMs = (await stat(outputPath)).mtimeMs;
    if (outputModifiedMs + 1 < newestSource.modifiedMs) {
      blockers.push(finding('OUTPUT_STALE', `${kind} output is older than a project source file.`, {
        path: outputPath,
        outputModifiedMs,
        newestSource,
      }));
    }
  }

  if (!blockers.some((item) => item.evidence?.path === pngPath && ['OUTPUT_MISSING', 'OUTPUT_EMPTY'].includes(item.code))) {
    try {
      png = PNG.sync.read(await readFile(pngPath));
      const content = pngContentEvidence(png);
      evidence.png = { width: png.width, height: png.height };
      evidence.pngContent = content;
      if (content.transparentRatio > 0.99 || (content.colorBuckets <= 2 && content.lumaRange <= 3)) {
        blockers.push(finding('OUTPUT_BLANK', 'Primary PNG is blank or nearly uniform.', { path: pngPath, content }));
      }
    } catch (error) {
      blockers.push(finding('OUTPUT_INVALID', 'PNG output could not be decoded.', { path: pngPath, error: error.message }));
    }
  }

  const expected = expectedOutputDimensions(config.canvas, png);
  if (png) {
    const heightMatches = expected.png.exactHeight
      ? png.height === expected.png.height
      : png.height >= expected.png.height;
    if (png.width !== expected.png.width || !heightMatches) {
      blockers.push(finding('PNG_SIZE_MISMATCH', 'PNG dimensions do not match the configured canvas.', {
        actual: evidence.png,
        expected: { width: expected.png.width, height: expected.png.height, heightRule: expected.png.exactHeight ? 'exact' : 'minimum' },
      }));
    }
  }

  if (!blockers.some((item) => item.evidence?.path === mobilePath && ['OUTPUT_MISSING', 'OUTPUT_EMPTY'].includes(item.code))) {
    try {
      const mobile = PNG.sync.read(await readFile(mobilePath));
      evidence.mobile = { width: mobile.width, height: mobile.height };
      const expectedHeight = png ? Math.round(png.height * 360 / png.width) : null;
      const heightDrift = expectedHeight === null ? 0 : Math.abs(mobile.height - expectedHeight);
      if (mobile.width !== 360 || heightDrift > 1) {
        blockers.push(finding('MOBILE_SIZE_MISMATCH', 'Mobile review image dimensions do not match the primary PNG aspect ratio.', {
          actual: evidence.mobile,
          expected: { width: 360, height: expectedHeight, heightTolerance: 1 },
        }));
      }
    } catch (error) {
      blockers.push(finding('OUTPUT_INVALID', 'Mobile review PNG could not be decoded.', { path: mobilePath, error: error.message }));
    }
  }

  if (!blockers.some((item) => item.evidence?.path === pdfPath && ['OUTPUT_MISSING', 'OUTPUT_EMPTY'].includes(item.code))) {
    try {
      const pdf = await PDFDocument.load(await readFile(pdfPath));
      const pageCount = pdf.getPageCount();
      const firstPage = pageCount ? pdf.getPage(0).getSize() : null;
      evidence.pdf = { pageCount, widthPoints: firstPage?.width ?? null, heightPoints: firstPage?.height ?? null };
      if (pageCount !== 1) {
        blockers.push(finding('PDF_PAGE_COUNT', 'PDF output must contain exactly one page.', { actual: pageCount, expected: 1 }));
      } else if (expected.pdf && !pointSizeMatches(firstPage, expected.pdf)) {
        blockers.push(finding('PDF_SIZE_MISMATCH', 'PDF page dimensions do not match the configured canvas.', {
          actual: firstPage,
          expected: expected.pdf,
          tolerancePoints: 1,
        }));
      }
    } catch (error) {
      blockers.push(finding('OUTPUT_INVALID', 'PDF output could not be decoded.', { path: pdfPath, error: error.message }));
    }
  }

  return evidence;
}

async function readRequiredJson(project, relative, blockers) {
  const sourcePath = path.join(project, relative);
  try {
    const details = await lstat(sourcePath);
    if (details.isSymbolicLink() || !details.isFile()) throw new Error('source must be a regular file without symbolic links');
    return JSON.parse(await readFile(sourcePath, 'utf8'));
  } catch (error) {
    const invalid = error instanceof SyntaxError || error.message?.includes('regular file without symbolic links');
    blockers.push(finding(invalid ? 'SOURCE_INVALID' : 'SOURCE_MISSING',
      invalid ? 'Required JSON source is invalid.' : 'Required project source is missing.',
      { path: sourcePath, error: error.code ?? error.message }));
    return null;
  }
}

async function requiredFileExists(project, relative, blockers) {
  const sourcePath = path.join(project, relative);
  try {
    const details = await lstat(sourcePath);
    if (details.isSymbolicLink() || !details.isFile()) throw new Error('source must be a regular file without symbolic links');
    return true;
  } catch (error) {
    const invalid = error.message?.includes('regular file without symbolic links');
    blockers.push(finding(invalid ? 'SOURCE_INVALID' : 'SOURCE_MISSING', invalid ? 'Required project source is invalid.' : 'Required project source is missing.', {
      path: sourcePath,
      error: error.code ?? error.message,
    }));
    return false;
  }
}

async function sha256File(filePath) {
  return createHash('sha256').update(await readFile(filePath)).digest('hex');
}

async function inspectVisualReview(project, outputPaths, blockers) {
  const reviewPath = path.join(project, 'visual-review.json');
  let review;
  try {
    review = JSON.parse(await readFile(reviewPath, 'utf8'));
  } catch (error) {
    blockers.push(finding(error.code === 'ENOENT' ? 'VISUAL_REVIEW_MISSING' : 'VISUAL_REVIEW_INVALID',
      error.code === 'ENOENT' ? 'Final QA requires visual-review.json.' : 'visual-review.json is invalid.',
      { path: reviewPath, error: error.code ?? error.message }));
    return null;
  }

  const requiredChecks = ['hierarchy', 'composition', 'typography', 'coherence', 'artifacts', 'mobile'];
  const issues = [];
  if (review.version !== 1) issues.push('version must be 1');
  if (review.status !== 'PASS') issues.push('status must be PASS');
  if (typeof review.reviewer !== 'string' || review.reviewer.trim() === '') issues.push('reviewer is required');
  if (Number.isNaN(Date.parse(review.reviewedAt))) issues.push('reviewedAt must be an ISO date');
  for (const check of requiredChecks) {
    if (review.checks?.[check] !== 'PASS') issues.push(`checks.${check} must be PASS`);
  }
  if (issues.length) {
    blockers.push(finding('VISUAL_REVIEW_FAILED', 'Visual review has missing or failed checks.', { path: reviewPath, issues }));
    return review;
  }

  const expected = {
    png: { path: outputPaths.pngPath, file: path.basename(outputPaths.pngPath) },
    mobile: { path: outputPaths.mobilePath, file: path.basename(outputPaths.mobilePath) },
  };
  const stale = [];
  for (const [kind, output] of Object.entries(expected)) {
    let digest;
    try {
      digest = await sha256File(output.path);
    } catch (error) {
      stale.push({ kind, error: error.code ?? error.message });
      continue;
    }
    if (review.outputs?.[kind]?.file !== output.file || review.outputs?.[kind]?.sha256 !== digest) {
      stale.push({ kind, expectedFile: output.file, expectedSha256: digest, actual: review.outputs?.[kind] ?? null });
    }
  }
  if (stale.length) blockers.push(finding('VISUAL_REVIEW_STALE', 'Visual review does not match the current rendered outputs.', { path: reviewPath, items: stale }));
  return review;
}

async function inspectQaNarrative(project, outputPaths, blockers) {
  const reportPath = path.join(project, 'qa-report.md');
  let markdown;
  try {
    markdown = await readFile(reportPath, 'utf8');
  } catch (error) {
    blockers.push(finding('SOURCE_MISSING', 'Final QA requires qa-report.md.', { path: reportPath, error: error.code ?? error.message }));
    return;
  }
  const expectedHashes = await Promise.all([sha256File(outputPaths.pngPath), sha256File(outputPaths.mobilePath)]);
  const missingHashes = expectedHashes.filter((digest) => !markdown.includes(digest));
  if (missingHashes.length || !/Visual QA:\s*PASS/i.test(markdown)) {
    blockers.push(finding('QA_NARRATIVE_STALE', 'qa-report.md must record visual PASS and the current target/mobile SHA-256 hashes.', {
      path: reportPath,
      missingHashes,
    }));
  }
}

async function writeStartupFailure(reportPath, project, strict, finalRequested, blockers) {
  const report = {
    version: 1,
    project,
    strict,
    generatedAt: new Date().toISOString(),
    status: 'FAIL',
    blockers,
    warnings: [],
    release: { finalRequested, finalEligible: false },
    evidence: { viewport: null, dom: null, facts: [], qrCodes: [], fonts: null, outputs: null },
  };
  await writeReport(reportPath, report);
}

async function writeReport(reportPath, report) {
  const temporaryPath = path.join(path.dirname(reportPath), `.qa-report.${randomUUID()}.tmp.json`);
  try {
    await writeFile(temporaryPath, `${JSON.stringify(report, null, 2)}\n`);
    await rm(reportPath, { force: true });
    await rename(temporaryPath, reportPath);
  } finally {
    await rm(temporaryPath, { force: true });
  }
}

async function main() {
  const { flags, values } = parseArgs(process.argv.slice(2));
  if (!values.project) throw new Error('--project is required');
  const project = path.resolve(values.project);
  const reportPath = await projectOutputPath(project, 'qa-report.json', 'qa-report.json');
  const strict = flags.has('strict') || flags.has('final');
  const finalRequested = flags.has('final');
  const blockers = [];
  const warnings = [];
  const config = await readRequiredJson(project, 'poster.config.json', blockers);
  const brief = await readRequiredJson(project, 'brief.json', blockers);
  const htmlExists = await requiredFileExists(project, 'poster.html', blockers);
  if (config) {
    const issues = validateConfig(config);
    if (issues.length) blockers.push(finding('CONFIG_INVALID', 'poster.config.json violates the project contract.', { issues }));
  }
  if (brief) {
    const issues = validateBrief(brief);
    if (issues.length) blockers.push(finding('BRIEF_INVALID', 'brief.json violates the factual contract.', { issues }));
  }
  if (htmlExists) {
    const issues = validateStaticHtml(await readFile(path.join(project, 'poster.html'), 'utf8'));
    if (issues.length) blockers.push(finding('ACTIVE_CONTENT', 'Poster HTML must be static and non-executable.', { issues }));
  }
  if (!config || !brief || !htmlExists || blockers.length) {
    await writeStartupFailure(reportPath, project, strict, finalRequested, blockers);
    process.stdout.write(`${JSON.stringify({ status: 'FAIL', blockers: blockers.length, warnings: 0 })}\n`);
    if (strict) process.exitCode = 1;
    return;
  }
  const outputPaths = {
    pngPath: await projectOutputPath(project, config.outputs?.png, 'poster.png'),
    mobilePath: await projectOutputPath(project, config.outputs?.mobile, 'poster-mobile.png'),
    pdfPath: await projectOutputPath(project, config.outputs?.pdf, 'poster.pdf'),
  };
  if (new Set([...Object.values(outputPaths), reportPath]).size !== 4) {
    throw new Error('PNG, mobile PNG, PDF, and QA report output paths must be unique.');
  }
  const viewport = viewportFor(config.canvas);
  const executablePath = await resolveExecutable(values.browser);
  const launchOptions = { headless: true };
  if (executablePath) launchOptions.executablePath = executablePath;

  let browser;
  try {
    browser = await chromium.launch(launchOptions);
    const context = await browser.newContext({ viewport, deviceScaleFactor: 1, serviceWorkers: 'block' });
    const blockedResources = await installProjectResourceBoundary(context, project);
    const page = await context.newPage();
    await page.goto(pathToFileURL(path.join(project, 'poster.html')).href, { waitUntil: 'load' });
    for (const blocked of blockedResources) {
      blockers.push(finding(blocked.code, 'Poster resource was blocked by the project containment boundary.', blocked));
    }
    await page.addStyleTag({ content: configuredCss(config.canvas) });
    await page.evaluate(() => document.fonts.ready);

    const result = await page.evaluate(() => {
      const poster = document.querySelector('#poster');
      const asciiPlaceholderPattern = /\b(TODO|TBD|PLACEHOLDER|LOREM IPSUM)\b/i;
      const chinesePlaceholderPattern = /(二维码占位|待补|待定)/;
      const nodes = [...document.querySelectorAll('body *')];
      const placeholders = [];
      const overflows = [];
      const undersizedText = [];
      const undersizedMobileText = [];
      const fonts = new Set();
      const posterWidth = poster?.getBoundingClientRect().width || 0;
      const mobileScale = posterWidth > 0 ? 360 / posterWidth : 0;

      for (const element of nodes) {
        const text = element.children.length === 0 ? element.textContent?.trim() ?? '' : '';
        if (text && (asciiPlaceholderPattern.test(text) || chinesePlaceholderPattern.test(text))) {
          placeholders.push({ tag: element.tagName, text: text.slice(0, 160) });
        }
        const style = getComputedStyle(element);
        if (style.display !== 'none' && style.visibility !== 'hidden') {
          const horizontalOverflow = element.scrollWidth > element.clientWidth + 1;
          const fontSize = Number.parseFloat(style.fontSize) || 0;
          const verticalTolerance = Math.max(2, fontSize * 0.2);
          const verticalOverflow = element.scrollHeight > element.clientHeight + verticalTolerance;
          if (horizontalOverflow || verticalOverflow) {
            overflows.push({
              tag: element.tagName,
              id: element.id,
              className: typeof element.className === 'string' ? element.className : '',
              clientWidth: element.clientWidth,
              scrollWidth: element.scrollWidth,
              clientHeight: element.clientHeight,
              scrollHeight: element.scrollHeight,
            });
          }
          if (text) fonts.add(style.fontFamily);
          if (text) {
            const thresholdRoot = element.closest('[data-min-font-pt]');
            const minimumPoints = Number.parseFloat(thresholdRoot?.dataset.minFontPt ?? '');
            const actualPoints = fontSize * 0.75;
            if (Number.isFinite(minimumPoints) && actualPoints + 0.1 < minimumPoints) {
              undersizedText.push({
                tag: element.tagName,
                text: text.slice(0, 160),
                actualPoints,
                minimumPoints,
              });
            }
            const minimumMobilePixels = Number.parseFloat(element.dataset.mobileMinPx ?? '');
            const mobilePixels = fontSize * mobileScale;
            if (Number.isFinite(minimumMobilePixels) && mobilePixels + 0.1 < minimumMobilePixels) {
              undersizedMobileText.push({
                tag: element.tagName,
                text: text.slice(0, 160),
                mobilePixels,
                minimumMobilePixels,
              });
            }
          }
        }
      }

      const images = [...document.images].map((image) => ({
        src: image.currentSrc || image.src,
        alt: image.alt,
        complete: image.complete,
        naturalWidth: image.naturalWidth,
        naturalHeight: image.naturalHeight,
        displayWidth: image.getBoundingClientRect().width,
        displayHeight: image.getBoundingClientRect().height,
      }));
      const visibility = (element) => {
        const box = element.getBoundingClientRect();
        let current = element;
        let ancestorsVisible = true;
        while (current && current.nodeType === Node.ELEMENT_NODE) {
          const style = getComputedStyle(current);
          if (style.display === 'none' || style.visibility === 'hidden' || Number.parseFloat(style.opacity) <= 0.01) {
            ancestorsVisible = false;
            break;
          }
          current = current.parentElement;
        }
        return ancestorsVisible
          && box.width > 0
          && box.height > 0
          && box.right > 0
          && box.bottom > 0
          && box.left < (poster?.getBoundingClientRect().right ?? window.innerWidth)
          && box.top < (poster?.getBoundingClientRect().bottom ?? document.documentElement.scrollHeight);
      };
      const facts = [...document.querySelectorAll('[data-fact]')].map((element) => ({
        key: element.dataset.fact,
        value: element.textContent?.trim() ?? '',
        visible: visibility(element),
      }));
      const qrCodes = [...document.querySelectorAll('img[data-qr]')].map((image, index) => ({
        index,
        key: image.dataset.qr,
        src: image.currentSrc || image.src,
        width: image.getBoundingClientRect().width,
        height: image.getBoundingClientRect().height,
        visible: visibility(image),
      }));
      return {
        posterStatus: poster?.dataset.posterStatus ?? null,
        posterCount: document.querySelectorAll('#poster').length,
        poster: poster ? {
          clientWidth: poster.clientWidth,
          clientHeight: poster.clientHeight,
          scrollWidth: poster.scrollWidth,
          scrollHeight: poster.scrollHeight,
        } : null,
        placeholders,
        overflows,
        undersizedText,
        undersizedMobileText,
        images,
        fonts: [...fonts],
        facts,
        qrCodes,
      };
    });

    const requiredFonts = [
      { family: 'Noto Sans SC', sample: '海报 Poster 2026' },
      { family: 'Noto Serif SC', sample: '科研 商业 会议' },
      { family: 'Ma Shan Zheng', sample: '国风书法 AI' },
    ];
    const loadedFonts = [];
    const failedFonts = [];
    for (const font of requiredFonts) {
      const loaded = await page.evaluate(async ({ family, sample }) => {
        await document.fonts.load(`32px "${family}"`, sample);
        return document.fonts.check(`32px "${family}"`, sample);
      }, font);
      (loaded ? loadedFonts : failedFonts).push(font.family);
    }
    if (strict && failedFonts.length) {
      blockers.push(finding('FONT_LOAD_FAILED', 'One or more required bundled fonts failed to load.', { failedFonts }));
    }

    if (result.posterCount !== 1) blockers.push(finding('POSTER_ROOT', 'Expected exactly one #poster root.', { count: result.posterCount }));
    if (result.placeholders.length) blockers.push(finding('UNRESOLVED_PLACEHOLDER', 'Unresolved placeholder text remains.', { items: result.placeholders }));
    if (result.overflows.length) blockers.push(finding('ELEMENT_OVERFLOW', 'One or more elements overflow their boxes.', { items: result.overflows.slice(0, 50) }));
    if (result.undersizedText.length) blockers.push(finding('MIN_FONT_SIZE', 'One or more text elements are below their declared minimum print size.', { items: result.undersizedText.slice(0, 50) }));
    if (result.undersizedMobileText.length) blockers.push(finding('MOBILE_CRITICAL_SIZE', 'One or more mobile-critical text elements are below their declared 360px review size.', { items: result.undersizedMobileText.slice(0, 50) }));

    const brokenImages = result.images.filter((image) => !image.complete || image.naturalWidth === 0 || image.naturalHeight === 0);
    if (brokenImages.length) blockers.push(finding('BROKEN_IMAGE', 'One or more images failed to decode.', { items: brokenImages }));
    const distorted = result.images.filter((image) => image.naturalWidth > 0 && image.displayWidth > 0 && Math.abs((image.naturalWidth / image.naturalHeight) - (image.displayWidth / image.displayHeight)) > 0.03);
    if (distorted.length) warnings.push(finding('IMAGE_ASPECT_DRIFT', 'Displayed image aspect ratio differs from its source.', { items: distorted }));

    if (strict) {
      const forbiddenGeneric = result.fonts.filter((font) => /(^|,\s*)(fantasy|cursive|system-ui|ui-serif|ui-sans-serif)(,|$)/i.test(font));
      if (forbiddenGeneric.length) blockers.push(finding('UNDECLARED_FONT', 'A non-bundled generic or fallback font is in use.', { fonts: forbiddenGeneric }));
    }

    const factEvidence = [];
    const expectedFactKeys = new Set((brief.facts ?? []).map((item) => item.key));
    const undeclaredFacts = result.facts.filter((item) => !expectedFactKeys.has(item.key));
    if (undeclaredFacts.length) blockers.push(finding('FACT_UNDECLARED', 'Poster contains fact bindings not declared in brief.json.', { items: undeclaredFacts }));
    for (const expected of brief.facts ?? []) {
      const matches = result.facts.filter((actual) => actual.key === expected.key);
      const actualValues = matches.map((item) => item.value);
      factEvidence.push({ key: expected.key, expected: expected.value, actual: actualValues });
      if (matches.length !== 1 && expected.critical) {
        blockers.push(finding('FACT_CARDINALITY', `Critical fact '${expected.key}' must appear exactly once.`, { expected, actualValues }));
      } else if (matches.length > 1) {
        blockers.push(finding('FACT_CARDINALITY', `Fact '${expected.key}' must not be duplicated.`, { expected, actualValues }));
      } else if (matches.length === 0) {
        warnings.push(finding('OPTIONAL_FACT_MISSING', `Optional fact '${expected.key}' is not displayed.`, { expected }));
      } else if (!matches[0].visible) {
        blockers.push(finding('FACT_NOT_VISIBLE', `Fact '${expected.key}' is present but not visibly rendered.`, { expected, actual: matches[0] }));
      } else if (matches.length && normalizeFact(matches[0].value) !== normalizeFact(expected.value)) {
        blockers.push(finding('FACT_MISMATCH', `Displayed fact '${expected.key}' differs from the approved brief.`, { expected: expected.value, actual: matches[0].value }));
      }
    }

    const qrEvidence = [];
    const expectedQrKeys = new Set((brief.qrCodes ?? []).map((item) => item.key));
    const undeclaredQrCodes = result.qrCodes.filter((item) => !expectedQrKeys.has(item.key));
    if (undeclaredQrCodes.length) blockers.push(finding('QR_UNDECLARED', 'Poster contains QR bindings not declared in brief.json.', { items: undeclaredQrCodes }));
    for (const expected of brief.qrCodes ?? []) {
      const matches = result.qrCodes.filter((item) => item.key === expected.key);
      if (matches.length !== 1 && expected.critical) {
        blockers.push(finding('QR_CARDINALITY', `Critical QR '${expected.key}' must appear exactly once.`, { expected, matches }));
        continue;
      }
      if (matches.length > 1) {
        blockers.push(finding('QR_CARDINALITY', `QR '${expected.key}' must not be duplicated.`, { expected, matches }));
        continue;
      }
      if (matches.length === 0) {
        warnings.push(finding('OPTIONAL_QR_MISSING', `Optional QR '${expected.key}' is not displayed.`, { expected }));
        continue;
      }
      if (!matches[0].visible) {
        blockers.push(finding('QR_NOT_VISIBLE', `QR '${expected.key}' is present but not visibly rendered.`, { expected, actual: matches[0] }));
        continue;
      }
      const locator = page.locator('img[data-qr]').nth(matches[0].index);
      const buffer = await locator.screenshot({ animations: 'disabled' });
      const png = PNG.sync.read(buffer);
      const decoded = jsQR(new Uint8ClampedArray(png.data), png.width, png.height, { inversionAttempts: 'attemptBoth' });
      const evidence = { key: expected.key, expected: expected.destination, decoded: decoded?.data ?? null, width: png.width, height: png.height };
      const posterWidth = result.poster?.clientWidth || viewport.width;
      evidence.mobileWidth = matches[0].width * 360 / posterWidth;
      evidence.mobileHeight = matches[0].height * 360 / posterWidth;
      qrEvidence.push(evidence);
      if (!decoded?.data) {
        blockers.push(finding('QR_DECODE_FAILED', `QR '${expected.key}' could not be decoded locally.`, evidence));
      } else if (decoded.data !== expected.destination) {
        blockers.push(finding('QR_PAYLOAD_MISMATCH', `QR '${expected.key}' does not match the approved destination.`, evidence));
      }
      if (png.width < 160 || png.height < 160) {
        blockers.push(finding('QR_TOO_SMALL', `QR '${expected.key}' is below the 160px review threshold.`, evidence));
      }
      if (evidence.mobileWidth < 64 || evidence.mobileHeight < 64) {
        blockers.push(finding('QR_MOBILE_TOO_SMALL', `QR '${expected.key}' is below the 64px mobile review threshold.`, evidence));
      }
    }

    const outputEvidence = strict
      ? await inspectOutputs(project, config, blockers, outputPaths)
      : null;

    let visualReviewEvidence = null;
    if (finalRequested) {
      const declaredStatuses = { config: config.status, brief: brief.status, poster: result.posterStatus };
      const nonFinal = Object.entries(declaredStatuses).filter(([, value]) => !isFinalStatus(value));
      if (nonFinal.length) {
        blockers.push(finding('STATUS_NOT_FINAL', 'Final QA requires final status in config, brief, and poster DOM.', { declaredStatuses, nonFinal }));
      }
      visualReviewEvidence = await inspectVisualReview(project, outputPaths, blockers);
      await inspectQaNarrative(project, outputPaths, blockers);
    }

    const report = {
      version: 1,
      project,
      strict,
      generatedAt: new Date().toISOString(),
      status: blockers.length ? 'FAIL' : 'PASS',
      blockers,
      warnings,
      release: { finalRequested, finalEligible: finalRequested && blockers.length === 0 },
      evidence: {
        viewport,
        dom: result,
        facts: factEvidence,
        qrCodes: qrEvidence,
        fonts: { required: requiredFonts.map((font) => font.family), loaded: loadedFonts, failed: failedFonts },
        outputs: outputEvidence,
        visualReview: visualReviewEvidence,
      },
    };
    await writeReport(reportPath, report);
    process.stdout.write(`${JSON.stringify({ status: report.status, blockers: blockers.length, warnings: warnings.length })}\n`);
    if (strict && blockers.length) process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
