import { lstat, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { createHash, randomUUID } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { chromium } from 'playwright';
import { resolveExecutable } from './browser-paths.mjs';
import { publishProjectFile } from './path-safety.mjs';
import { collectProjectSourceHashes, installProjectResourceBoundary, validateConfig, validateMeasuredCanvas, validateStaticHtml } from './poster-contract.mjs';

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

function canvasViewport(canvas) {
  if (canvas.type === 'digital') {
    return { width: canvas.width, height: canvas.height };
  }
  if (canvas.type === 'long-form') {
    return { width: canvas.width, height: canvas.minHeight };
  }
  if (canvas.type === 'print') {
    const pxPerMm = 96 / 25.4;
    return {
      width: Math.round(canvas.widthMm * pxPerMm),
      height: Math.round(canvas.heightMm * pxPerMm),
    };
  }
  throw new Error(`Unsupported canvas type: ${canvas.type}`);
}

async function waitForAssets(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    const images = [...document.images];
    await Promise.all(images.map((image) => {
      if (image.complete) return undefined;
      return new Promise((resolve, reject) => {
        image.addEventListener('load', resolve, { once: true });
        image.addEventListener('error', () => reject(new Error(`Image failed: ${image.currentSrc || image.src}`)), { once: true });
      });
    }));
  });
}

function configuredCss(config) {
  const canvas = config.canvas;
  if (canvas.type === 'print') {
    return `:root { --canvas-width: ${canvas.widthMm}mm; --canvas-height: ${canvas.heightMm}mm; --page-width: ${canvas.widthMm}mm; --page-height: ${canvas.heightMm}mm; }`;
  }
  const height = canvas.type === 'long-form' ? canvas.minHeight : canvas.height;
  return `:root { --canvas-width: ${canvas.width}px; --canvas-height: ${height}px; --page-width: ${canvas.width}px; --page-height: ${height}px; }`;
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

function temporaryOutputPath(project, outputPath) {
  const extension = path.extname(outputPath);
  const stem = path.basename(outputPath, extension);
  return path.join(project, `.${stem}.${randomUUID()}.tmp${extension}`);
}

async function publishOutput(project, temporaryPath, outputPath) {
  await publishProjectFile(project, outputPath, (publicationPath) => rename(temporaryPath, publicationPath));
}

async function sha256(filePath) {
  return createHash('sha256').update(await readFile(filePath)).digest('hex');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.project) throw new Error('--project is required');

  const project = path.resolve(args.project);
  const sourceHashes = await collectProjectSourceHashes(project);
  const config = JSON.parse(await readFile(path.join(project, 'poster.config.json'), 'utf8'));
  const configIssues = validateConfig(config);
  if (configIssues.length) throw new Error(`Invalid poster.config.json: ${configIssues.join('; ')}`);
  const htmlPath = path.join(project, 'poster.html');
  const htmlIssues = validateStaticHtml(await readFile(htmlPath, 'utf8'));
  if (htmlIssues.length) throw new Error(`Poster HTML must be static: ${htmlIssues.join('; ')}`);
  const pngPath = await projectOutputPath(project, config.outputs?.png, 'poster.png');
  const mobilePath = await projectOutputPath(project, config.outputs?.mobile, 'poster-mobile.png');
  const pdfPath = await projectOutputPath(project, config.outputs?.pdf, 'poster.pdf');
  const resultPath = await projectOutputPath(project, 'render-result.json', 'render-result.json');
  if (new Set([pngPath, mobilePath, pdfPath, resultPath]).size !== 4) {
    throw new Error('PNG, mobile PNG, PDF, and render result output paths must be unique.');
  }
  const viewport = canvasViewport(config.canvas);
  const temporaryPaths = {
    png: temporaryOutputPath(project, pngPath),
    mobile: temporaryOutputPath(project, mobilePath),
    pdf: temporaryOutputPath(project, pdfPath),
    result: temporaryOutputPath(project, resultPath),
  };
  const executablePath = await resolveExecutable(args.browser);
  const launchOptions = { headless: true };
  if (executablePath) launchOptions.executablePath = executablePath;

  let browser;
  try {
    browser = await chromium.launch(launchOptions);
  } catch (error) {
    throw new Error(`Chromium launch failed. Install a local Chrome/Edge or run 'npx playwright install chromium'. ${error.message}`);
  }

  try {
    const context = await browser.newContext({ viewport, deviceScaleFactor: 1, serviceWorkers: 'block' });
    const blockedResources = await installProjectResourceBoundary(context, project);
    const page = await context.newPage();
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'load' });
    if (blockedResources.length) {
      throw new Error(`Poster resources must stay inside the project and offline: ${JSON.stringify(blockedResources)}`);
    }
    await page.addStyleTag({ content: configuredCss(config) });
    await waitForAssets(page);

    const poster = page.locator('#poster');
    const posterCount = await poster.count();
    if (posterCount !== 1) throw new Error(`Expected exactly one #poster element, found ${posterCount}`);

    const posterDimensions = await poster.evaluate((element) => ({
      width: Math.ceil(Math.max(element.scrollWidth, element.getBoundingClientRect().width)),
      height: Math.ceil(Math.max(element.scrollHeight, element.getBoundingClientRect().height)),
    }));
    const measuredIssues = validateMeasuredCanvas(posterDimensions.width, posterDimensions.height);
    if (measuredIssues.length) throw new Error(`Invalid measured canvas: ${measuredIssues.join('; ')}`);

    const screenshotOptions = { path: temporaryPaths.png, animations: 'disabled' };
    if (config.canvas.type === 'long-form') screenshotOptions.fullPage = true;
    else screenshotOptions.clip = { x: 0, y: 0, width: viewport.width, height: viewport.height };
    await page.screenshot(screenshotOptions);

    const mobileWidth = 360;
    const mobileScale = mobileWidth / posterDimensions.width;
    const mobileHeight = Math.round(posterDimensions.height * mobileScale);
    await page.setViewportSize({ width: mobileWidth, height: mobileHeight });
    await poster.evaluate((element, scale) => {
      document.documentElement.style.width = `${Math.ceil(element.scrollWidth * scale)}px`;
      document.documentElement.style.height = `${Math.ceil(element.scrollHeight * scale)}px`;
      document.body.style.width = document.documentElement.style.width;
      document.body.style.height = document.documentElement.style.height;
      document.body.style.overflow = 'hidden';
      element.style.transform = `scale(${scale})`;
      element.style.transformOrigin = 'top left';
    }, mobileScale);
    await page.screenshot({
      path: temporaryPaths.mobile,
      animations: 'disabled',
      clip: { x: 0, y: 0, width: mobileWidth, height: mobileHeight },
    });

    await poster.evaluate((element) => {
      document.documentElement.style.width = '';
      document.documentElement.style.height = '';
      document.body.style.width = '';
      document.body.style.height = '';
      document.body.style.overflow = '';
      element.style.transform = '';
      element.style.transformOrigin = '';
    });
    await page.setViewportSize(viewport);
    const pageSize = config.canvas.type === 'print'
      ? { width: `${config.canvas.widthMm}mm`, height: `${config.canvas.heightMm}mm` }
      : { width: `${posterDimensions.width}px`, height: `${posterDimensions.height}px` };
    await page.addStyleTag({ content: `@page { size: ${pageSize.width} ${pageSize.height}; margin: 0; }` });
    await page.emulateMedia({ media: 'print' });
    const pdfOptions = {
      path: temporaryPaths.pdf,
      printBackground: true,
      margin: { top: '0', right: '0', bottom: '0', left: '0' },
      preferCSSPageSize: true,
    };
    await page.pdf(pdfOptions);

    const finalSourceHashes = await collectProjectSourceHashes(project);
    if (JSON.stringify(finalSourceHashes) !== JSON.stringify(sourceHashes)) {
      throw new Error('Project sources changed during rendering; outputs were not published as current.');
    }
    const result = {
      version: 2,
      success: true,
      project,
      png: pngPath,
      mobile: mobilePath,
      pdf: pdfPath,
      viewport,
      sourceHashes,
      outputHashes: {
        [path.basename(pngPath)]: await sha256(temporaryPaths.png),
        [path.basename(mobilePath)]: await sha256(temporaryPaths.mobile),
        [path.basename(pdfPath)]: await sha256(temporaryPaths.pdf),
      },
    };
    await publishOutput(project, temporaryPaths.png, pngPath);
    await publishOutput(project, temporaryPaths.mobile, mobilePath);
    await publishOutput(project, temporaryPaths.pdf, pdfPath);
    await writeFile(temporaryPaths.result, `${JSON.stringify(result, null, 2)}\n`);
    await publishOutput(project, temporaryPaths.result, resultPath);
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } finally {
    await browser.close();
    await Promise.all(Object.values(temporaryPaths).map((temporaryPath) => rm(temporaryPath, { force: true })));
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
