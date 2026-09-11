import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { mkdtemp, readFile, rm, symlink, unlink, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const skillRoot = path.join(repositoryRoot, 'src/hermes_post_design/resources/skills/creative/poster-design');
const initPoster = path.join(skillRoot, 'scripts/init-poster.mjs');
const requireFromSkill = createRequire(path.join(skillRoot, 'package.json'));
const { PNG } = requireFromSkill('pngjs');
const { PDFDocument, rgb } = requireFromSkill('pdf-lib');

function run(command, args, options = {}) {
  return spawnSync(command, args, {
    cwd: options.cwd ?? repositoryRoot,
    encoding: 'utf8',
    env: { ...process.env, ...options.env },
  });
}

function requireSuccess(result, command, args) {
  assert.equal(result.status, 0, `${command} ${args.join(' ')}\nstdout:\n${result.stdout}\nstderr:\n${result.stderr}`);
}

async function readJson(filePath) {
  return JSON.parse(await readFile(filePath, 'utf8'));
}

async function writeJson(filePath, value) {
  await writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

async function sha256(filePath) {
  return createHash('sha256').update(await readFile(filePath)).digest('hex');
}

async function writeOutputs(project) {
  const png = new PNG({ width: 1080, height: 1440 });
  for (let y = 0; y < png.height; y += 1) {
    for (let x = 0; x < png.width; x += 1) {
      const offset = (y * png.width + x) * 4;
      const accent = x > 160 && x < 920 && y > 220 && y < 1220;
      png.data[offset] = accent ? 34 : 245;
      png.data[offset + 1] = accent ? 76 : 242;
      png.data[offset + 2] = accent ? 60 : 232;
      png.data[offset + 3] = 255;
    }
  }
  await writeFile(path.join(project, 'poster.png'), PNG.sync.write(png));

  const mobile = new PNG({ width: 360, height: 480 });
  for (let y = 0; y < mobile.height; y += 1) {
    for (let x = 0; x < mobile.width; x += 1) {
      const offset = (y * mobile.width + x) * 4;
      const accent = x > 54 && x < 306 && y > 74 && y < 407;
      mobile.data[offset] = accent ? 34 : 245;
      mobile.data[offset + 1] = accent ? 76 : 242;
      mobile.data[offset + 2] = accent ? 60 : 232;
      mobile.data[offset + 3] = 255;
    }
  }
  await writeFile(path.join(project, 'poster-mobile.png'), PNG.sync.write(mobile));

  const pdf = await PDFDocument.create();
  const page = pdf.addPage([810, 1080]);
  page.drawRectangle({ x: 80, y: 100, width: 650, height: 880, color: rgb(0.13, 0.3, 0.24) });
  await writeFile(path.join(project, 'poster.pdf'), await pdf.save());
}

async function writeCurrentEvidence(project) {
  const contractUrl = `${pathToFileURL(path.join(project, 'scripts/poster-contract.mjs')).href}?fixture=${Date.now()}-${Math.random()}`;
  const { collectProjectSourceHashes } = await import(contractUrl);
  const outputHashes = {
    'poster.png': await sha256(path.join(project, 'poster.png')),
    'poster-mobile.png': await sha256(path.join(project, 'poster-mobile.png')),
    'poster.pdf': await sha256(path.join(project, 'poster.pdf')),
  };
  await writeJson(path.join(project, 'render-result.json'), {
    version: 2,
    success: true,
    project,
    png: path.join(project, 'poster.png'),
    mobile: path.join(project, 'poster-mobile.png'),
    pdf: path.join(project, 'poster.pdf'),
    viewport: { width: 1080, height: 1440 },
    sourceHashes: await collectProjectSourceHashes(project),
    outputHashes,
  });
  await writeJson(path.join(project, 'visual-review.json'), {
    version: 1,
    reviewedAt: '2026-09-11T12:00:00.000Z',
    reviewer: 'release-negative-fixture',
    status: 'PASS',
    outputs: {
      png: { file: 'poster.png', sha256: outputHashes['poster.png'] },
      mobile: { file: 'poster-mobile.png', sha256: outputHashes['poster-mobile.png'] },
    },
    checks: {
      hierarchy: 'PASS',
      composition: 'PASS',
      typography: 'PASS',
      coherence: 'PASS',
      artifacts: 'PASS',
      mobile: 'PASS',
    },
    notes: '',
  });
  await writeFile(path.join(project, 'qa-report.md'), [
    '# Poster QA Report',
    '',
    '- Visual QA: PASS',
    `- Target PNG SHA-256: ${outputHashes['poster.png']}`,
    `- Mobile PNG SHA-256: ${outputHashes['poster-mobile.png']}`,
    '',
  ].join('\n'));
}

async function createReleaseProject(context, scenario) {
  const temporaryRoot = await mkdtemp(path.join(skillRoot, '.release-negative-'));
  context.after(() => rm(temporaryRoot, { recursive: true, force: true }));
  const project = path.join(temporaryRoot, `${scenario}-poster`);
  requireSuccess(run('node', [initPoster, '--output', project, '--title', 'Release poster', '--type', 'digital']), 'node', [initPoster]);

  await symlink(path.join(skillRoot, 'node_modules'), path.join(project, 'node_modules'), 'dir');
  requireSuccess(run('node', [path.join(project, 'scripts/prepare-project.mjs'), '--project', project]), 'node', ['scripts/prepare-project.mjs']);
  await unlink(path.join(project, 'node_modules'));

  const configPath = path.join(project, 'poster.config.json');
  const config = await readJson(configPath);
  config.status = 'final';
  config.mode = 'release';
  config.state = 'release';
  await writeJson(configPath, config);

  const briefPath = path.join(project, 'brief.json');
  const brief = await readJson(briefPath);
  brief.status = 'final';
  brief.mode = 'release';
  brief.state = 'release';
  await writeJson(briefPath, brief);

  await writeJson(path.join(project, 'poster.json'), {
    version: 1,
    mode: 'release',
    state: 'release',
    conceptRevision: 0,
    direction: 'approved release direction',
    approvedCopy: ['Release poster'],
    provider: {
      adapter: 'deterministic-local',
      external: false,
      billed: false,
      authorizedCalls: 0,
      usedCalls: 0,
    },
  });
  await writeJson(path.join(project, 'publish-qa.json'), {
    version: 1,
    status: 'PASS',
    size: 'PASS',
    facts: 'PASS',
    identity: 'PASS',
    logo: 'PASS',
    qr: 'NOT_APPLICABLE',
    mobile: 'PASS',
    artifacts: 'PASS',
  });

  const htmlPath = path.join(project, 'poster.html');
  let html = (await readFile(htmlPath, 'utf8')).replace('data-poster-status="preview"', 'data-poster-status="final"');
  if (scenario !== 'starter-copy') {
    html = html
      .replace('<p class="eyebrow" data-placeholder="starter-preview">PREVIEW</p>', '<p class="eyebrow">RELEASE</p>')
      .replace('<p data-placeholder="starter-copy">Replace this starter content after the brief is approved.</p>', '<p>Approved release content.</p>');
  } else {
    html = html.replaceAll(/\sdata-placeholder="[^"]+"/g, '');
  }
  await writeFile(htmlPath, html);

  if (scenario === 'system-font-substitution') {
    const cssPath = path.join(project, 'styles.css');
    const css = await readFile(cssPath, 'utf8');
    await writeFile(cssPath, css.replaceAll(/@font-face\s*\{[^}]+\}\s*/gs, '').replaceAll(/"(?:Noto Sans SC|Noto Serif SC|Ma Shan Zheng)"/g, 'Arial'));
  }
  if (scenario === 'font-hash') {
    for (const relative of ['font-manifest.json', 'assets/fonts/font-manifest.json']) {
      const manifestPath = path.join(project, relative);
      const manifest = await readJson(manifestPath);
      manifest.fonts[0].sha256 = '0'.repeat(64);
      await writeJson(manifestPath, manifest);
    }
  }
  if (scenario === 'font-path') {
    for (const relative of ['font-manifest.json', 'assets/fonts/font-manifest.json']) {
      const manifestPath = path.join(project, relative);
      const manifest = await readJson(manifestPath);
      manifest.fonts[0].file = 'assets/fonts/../licenses/MaShanZheng-OFL-1.1.txt';
      await writeJson(manifestPath, manifest);
    }
  }
  if (scenario === 'font-samples') {
    for (const relative of ['font-manifest.json', 'assets/fonts/font-manifest.json']) {
      const manifestPath = path.join(project, relative);
      const manifest = await readJson(manifestPath);
      manifest.fonts[0].samples = [];
      await writeJson(manifestPath, manifest);
    }
  }
  if (scenario === 'font-license') {
    const manifest = await readJson(path.join(project, 'font-manifest.json'));
    await rm(path.join(project, manifest.fonts[0].licenseFile));
  }
  if (scenario === 'css-font-url') {
    await writeFile(path.join(project, 'styles.css'), `${await readFile(path.join(project, 'styles.css'), 'utf8')}\n@font-face { font-family: "Undeclared Font"; src: url("assets/fonts/undeclared.woff2") format("woff2"); }\n`);
  }
  if (scenario === 'invalid-transition') {
    const posterPath = path.join(project, 'poster.json');
    const poster = await readJson(posterPath);
    poster.mode = 'concept';
    poster.state = 'publish';
    await writeJson(posterPath, poster);
  }
  if (scenario === 'provider-authorization') {
    const posterPath = path.join(project, 'poster.json');
    const poster = await readJson(posterPath);
    poster.provider = {
      adapter: 'fake-image-adapter',
      external: true,
      billed: true,
      authorizedCalls: 0,
      usedCalls: 0,
    };
    await writeJson(posterPath, poster);
  }
  if (scenario === 'publish-pending') {
    const qaPath = path.join(project, 'publish-qa.json');
    const qa = await readJson(qaPath);
    qa.artifacts = 'PENDING';
    await writeJson(qaPath, qa);
  }

  await writeOutputs(project);
  await writeCurrentEvidence(project);

  if (scenario === 'output-hash') {
    const renderResultPath = path.join(project, 'render-result.json');
    const renderResult = await readJson(renderResultPath);
    renderResult.outputHashes['poster.png'] = '0'.repeat(64);
    await writeJson(renderResultPath, renderResult);
  }
  if (scenario === 'visual-review') {
    const reviewPath = path.join(project, 'visual-review.json');
    const review = await readJson(reviewPath);
    review.outputs.png.sha256 = '0'.repeat(64);
    await writeJson(reviewPath, review);
  }
  return project;
}

async function assertReleaseBlocked(context, scenario, expectedCode) {
  const project = await createReleaseProject(context, scenario);
  const inspection = run('node', [path.join(project, 'scripts/inspect-poster.mjs'), '--project', project, '--strict', '--final']);
  assert.notEqual(inspection.status, 0, `inspect unexpectedly succeeded for ${scenario}\nstdout:\n${inspection.stdout}\nstderr:\n${inspection.stderr}`);
  const report = await readJson(path.join(project, 'qa-report.json'));
  assert.equal(report.status, 'FAIL');
  assert.equal(report.release.finalEligible, false);
  assert.ok(report.blockers.some(({ code }) => code === expectedCode), JSON.stringify(report.blockers, null, 2));
}

for (const [scenario, expectedCode] of [
  ['system-font-substitution', 'UNDECLARED_FONT'],
  ['font-hash', 'FONT_HASH_MISMATCH'],
  ['font-path', 'FONT_PATH_INVALID'],
  ['font-samples', 'FONT_MANIFEST_INVALID'],
  ['font-license', 'FONT_LICENSE_MISSING'],
  ['starter-copy', 'UNRESOLVED_PLACEHOLDER'],
  ['output-hash', 'OUTPUT_HASH_MISMATCH'],
  ['visual-review', 'VISUAL_REVIEW_STALE'],
  ['css-font-url', 'UNDECLARED_FONT'],
  ['invalid-transition', 'POSTER_STATE_INVALID'],
  ['provider-authorization', 'POSTER_STATE_INVALID'],
  ['publish-pending', 'PUBLISH_QA_INVALID'],
]) {
  test(`Release blocks ${scenario}`, async (context) => {
    await assertReleaseBlocked(context, scenario, expectedCode);
  });
}
