import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { copyFile, mkdir, mkdtemp, readFile, rm, symlink, unlink, writeFile } from 'node:fs/promises';
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
const fontkit = requireFromSkill('fontkit');

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

const licenseSourceByFamily = {
  'Ma Shan Zheng': '@fontsource/ma-shan-zheng@5.3.0',
  'Noto Sans SC': '@fontsource-variable/noto-sans-sc@5.3.0',
  'Noto Serif SC': '@fontsource-variable/noto-serif-sc@5.3.0',
};
const licenseHashByFamily = {
  'Ma Shan Zheng': '37784825d863bab31cdff1f4bfabae5b8d8e9913b91db2064a6b803b2edc92db',
  'Noto Sans SC': '18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3',
  'Noto Serif SC': '18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3',
};

function licenseRecord(font) {
  return {
    family: font.family,
    file: font.file,
    sha256: font.sha256,
    licenseFile: font.licenseFile,
    licenseSha256: licenseHashByFamily[font.family],
    licenseId: 'OFL-1.1',
    licenseName: 'SIL Open Font License',
    licenseVersion: '1.1',
    sourcePackage: licenseSourceByFamily[font.family],
  };
}

async function ensureLicenseManifests(project) {
  const rootPath = path.join(project, 'font-license-manifest.json');
  let licenseManifest;
  try {
    licenseManifest = await readJson(rootPath);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    const manifest = await readJson(path.join(project, 'font-manifest.json'));
    licenseManifest = { version: 1, records: manifest.fonts.map(licenseRecord) };
    await mkdir(path.join(project, 'assets/licenses'), { recursive: true });
  }
  await writeJson(rootPath, licenseManifest);
  await writeJson(path.join(project, 'assets/licenses/font-license-manifest.json'), licenseManifest);
  return licenseManifest;
}

async function updateLicenseRecordHashes(project, manifest) {
  const licenseManifest = await ensureLicenseManifests(project);
  for (const font of manifest.fonts) {
    const record = licenseManifest.records.find((item) => item.file === font.file);
    if (record) record.sha256 = font.sha256;
  }
  await writeJson(path.join(project, 'font-license-manifest.json'), licenseManifest);
  await writeJson(path.join(project, 'assets/licenses/font-license-manifest.json'), licenseManifest);
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
    identity: 'NOT_APPLICABLE',
    logo: 'NOT_APPLICABLE',
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
  if (scenario === 'font-family-masquerade') {
    const sourceDirectory = path.join(skillRoot, 'node_modules/@fontsource-variable/noto-sans-sc/files');
    const sources = [
      'noto-sans-sc-latin-wght-normal.woff2',
      'noto-sans-sc-latin-ext-wght-normal.woff2',
      'noto-sans-sc-vietnamese-wght-normal.woff2',
      'noto-sans-sc-cyrillic-wght-normal.woff2',
      'noto-sans-sc-119-wght-normal.woff2',
      'noto-sans-sc-82-wght-normal.woff2',
    ];
    const manifest = await readJson(path.join(project, 'font-manifest.json'));
    let licenses = await readFile(path.join(project, 'licenses.md'), 'utf8');
    for (const [index, font] of manifest.fonts.entries()) {
      const previousHash = font.sha256;
      await copyFile(path.join(sourceDirectory, sources[index]), path.join(project, font.file));
      const parsed = fontkit.create(await readFile(path.join(project, font.file)));
      const sampleCodePoint = parsed.characterSet.find((codePoint) => String.fromCodePoint(codePoint).trim() !== '');
      font.samples = [String.fromCodePoint(sampleCodePoint)];
      font.sha256 = await sha256(path.join(project, font.file));
      licenses = licenses.replace(previousHash, font.sha256);
    }
    await writeJson(path.join(project, 'font-manifest.json'), manifest);
    await writeJson(path.join(project, 'assets/fonts/font-manifest.json'), manifest);
    await updateLicenseRecordHashes(project, manifest);
    await writeFile(path.join(project, 'licenses.md'), licenses);
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
    const licenseManifest = await ensureLicenseManifests(project);
    licenseManifest.records[0].file = 'assets/fonts/../licenses/MaShanZheng-OFL-1.1.txt';
    await writeJson(path.join(project, 'font-license-manifest.json'), licenseManifest);
    await writeJson(path.join(project, 'assets/licenses/font-license-manifest.json'), licenseManifest);
  }
  if (scenario === 'font-samples') {
    for (const relative of ['font-manifest.json', 'assets/fonts/font-manifest.json']) {
      const manifestPath = path.join(project, relative);
      const manifest = await readJson(manifestPath);
      manifest.fonts[0].samples = [];
      await writeJson(manifestPath, manifest);
    }
  }
  if (scenario === 'font-glyph') {
    for (const relative of ['font-manifest.json', 'assets/fonts/font-manifest.json']) {
      const manifestPath = path.join(project, relative);
      const manifest = await readJson(manifestPath);
      const latinFont = manifest.fonts.find((font) => font.file === 'assets/fonts/NotoSansSC-Latin.woff2');
      latinFont.samples = ['中'];
      await writeJson(manifestPath, manifest);
    }
  }
  if (scenario === 'font-license') {
    const manifest = await readJson(path.join(project, 'font-manifest.json'));
    await rm(path.join(project, manifest.fonts[0].licenseFile));
  }
  if (scenario === 'font-license-swap') {
    const licenseManifest = await ensureLicenseManifests(project);
    const first = licenseManifest.records.find((record) => record.family === 'Ma Shan Zheng');
    const second = licenseManifest.records.find((record) => record.family === 'Noto Serif SC');
    [first.licenseFile, second.licenseFile] = [second.licenseFile, first.licenseFile];
    await writeJson(path.join(project, 'font-license-manifest.json'), licenseManifest);
    await writeJson(path.join(project, 'assets/licenses/font-license-manifest.json'), licenseManifest);
  }
  if (scenario === 'font-license-coordinated-swap') {
    const maLicense = 'assets/licenses/MaShanZheng-OFL-1.1.txt';
    const serifLicense = 'assets/licenses/NotoSerifSC-OFL-1.1.txt';
    for (const relative of ['font-manifest.json', 'assets/fonts/font-manifest.json']) {
      const manifestPath = path.join(project, relative);
      const manifest = await readJson(manifestPath);
      for (const font of manifest.fonts) {
        if (font.family === 'Ma Shan Zheng') font.licenseFile = serifLicense;
        if (font.family === 'Noto Serif SC') font.licenseFile = maLicense;
      }
      await writeJson(manifestPath, manifest);
    }
    const licenseManifest = await ensureLicenseManifests(project);
    for (const record of licenseManifest.records) {
      if (record.family === 'Ma Shan Zheng') {
        record.licenseFile = serifLicense;
        if (Object.hasOwn(record, 'licenseSha256')) record.licenseSha256 = licenseHashByFamily['Noto Serif SC'];
      }
      if (record.family === 'Noto Serif SC') {
        record.licenseFile = maLicense;
        if (Object.hasOwn(record, 'licenseSha256')) record.licenseSha256 = licenseHashByFamily['Ma Shan Zheng'];
      }
    }
    await writeJson(path.join(project, 'font-license-manifest.json'), licenseManifest);
    await writeJson(path.join(project, 'assets/licenses/font-license-manifest.json'), licenseManifest);
    const licensesPath = path.join(project, 'licenses.md');
    const licenses = await readFile(licensesPath, 'utf8');
    await writeFile(licensesPath, licenses
      .replaceAll(maLicense, '__MA_LICENSE__')
      .replaceAll(serifLicense, maLicense)
      .replaceAll('__MA_LICENSE__', serifLicense)
      .replaceAll(licenseHashByFamily['Ma Shan Zheng'], '__MA_LICENSE_HASH__')
      .replaceAll(licenseHashByFamily['Noto Serif SC'], licenseHashByFamily['Ma Shan Zheng'])
      .replaceAll('__MA_LICENSE_HASH__', licenseHashByFamily['Noto Serif SC']));
  }
  if (scenario === 'font-license-content') {
    const manifest = await readJson(path.join(project, 'font-manifest.json'));
    const targetLicense = manifest.fonts.find((font) => font.family === 'Ma Shan Zheng').licenseFile;
    const targetPath = path.join(project, targetLicense);
    const oldHash = await sha256(targetPath);
    await writeFile(targetPath, 'arbitrary replacement license content\n');
    const replacementHash = await sha256(targetPath);
    const licenseManifest = await ensureLicenseManifests(project);
    for (const record of licenseManifest.records.filter((item) => item.licenseFile === targetLicense)) {
      if (Object.hasOwn(record, 'licenseSha256')) record.licenseSha256 = replacementHash;
    }
    await writeJson(path.join(project, 'font-license-manifest.json'), licenseManifest);
    await writeJson(path.join(project, 'assets/licenses/font-license-manifest.json'), licenseManifest);
    const licensesPath = path.join(project, 'licenses.md');
    await writeFile(licensesPath, (await readFile(licensesPath, 'utf8')).replaceAll(oldHash, replacementHash));
  }
  if (scenario === 'font-local-source') {
    const cssPath = path.join(project, 'styles.css');
    const css = await readFile(cssPath, 'utf8');
    await writeFile(cssPath, css.replace('src: url("assets/fonts/MaShanZheng-Chinese.woff2")', 'src: local("Arial"), url("assets/fonts/MaShanZheng-Chinese.woff2")'));
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
  if (scenario === 'publish-all-na') {
    const qaPath = path.join(project, 'publish-qa.json');
    const qa = await readJson(qaPath);
    for (const field of ['size', 'facts', 'identity', 'logo', 'qr', 'mobile', 'artifacts']) qa[field] = 'NOT_APPLICABLE';
    await writeJson(qaPath, qa);
  }
  if (scenario === 'publish-qr-na') {
    const briefPath = path.join(project, 'brief.json');
    const briefValue = await readJson(briefPath);
    briefValue.qrCodes = [{ key: 'optional-qr', destination: 'https://example.test/', critical: false }];
    await writeJson(briefPath, briefValue);
  }
  if (scenario === 'publish-identity-na') {
    await writeFile(htmlPath, (await readFile(htmlPath, 'utf8')).replace('</section>', '<span class="speaker-portrait">Approved identity</span></section>'));
  }
  if (scenario === 'publish-logo-asset-na') {
    await mkdir(path.join(project, 'assets/logos'), { recursive: true });
    await writeFile(path.join(project, 'assets/logos/brand.txt'), 'authorized logo fixture');
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

async function inspectRelease(context, scenario) {
  const project = await createReleaseProject(context, scenario);
  const inspection = run('node', [path.join(project, 'scripts/inspect-poster.mjs'), '--project', project, '--strict', '--final']);
  const report = await readJson(path.join(project, 'qa-report.json'));
  return { project, inspection, report };
}

async function assertReleaseBlocked(context, scenario, expectedCodes) {
  const { inspection, report } = await inspectRelease(context, scenario);
  assert.notEqual(inspection.status, 0, `inspect unexpectedly succeeded for ${scenario}\nstdout:\n${inspection.stdout}\nstderr:\n${inspection.stderr}`);
  assert.equal(report.status, 'FAIL');
  assert.equal(report.release.finalEligible, false);
  assert.deepEqual([...new Set(report.blockers.map(({ code }) => code))].sort(), [...expectedCodes].sort(), JSON.stringify(report.blockers, null, 2));
}

test('Release accepts the mechanically clean baseline fixture', async (context) => {
  const { inspection, report } = await inspectRelease(context, 'baseline');
  assert.equal(inspection.status, 0, `stdout:\n${inspection.stdout}\nstderr:\n${inspection.stderr}\n${JSON.stringify(report.blockers, null, 2)}`);
  assert.equal(report.status, 'PASS');
  assert.equal(report.release.finalEligible, true);
  assert.deepEqual(report.blockers, []);
});

for (const [scenario, expectedCodes] of [
  ['system-font-substitution', ['FONT_LOAD_FAILED', 'UNDECLARED_FONT']],
  ['font-family-masquerade', ['FONT_BINARY_FAMILY_MISMATCH']],
  ['font-local-source', ['FONT_SOURCE_INVALID']],
  ['font-hash', ['FONT_HASH_MISMATCH']],
  ['font-path', ['FONT_PATH_INVALID', 'UNDECLARED_FONT']],
  ['font-samples', ['FONT_MANIFEST_INVALID']],
  ['font-glyph', ['FONT_GLYPH_MISSING']],
  ['font-license', ['FONT_LICENSE_MISSING']],
  ['font-license-swap', ['FONT_LICENSE_BINDING_MISMATCH']],
  ['font-license-coordinated-swap', ['FONT_LICENSE_BINDING_MISMATCH']],
  ['font-license-content', ['FONT_LICENSE_BINDING_MISMATCH']],
  ['starter-copy', ['UNRESOLVED_PLACEHOLDER']],
  ['output-hash', ['OUTPUT_HASH_MISMATCH']],
  ['visual-review', ['VISUAL_REVIEW_STALE']],
  ['css-font-url', ['UNDECLARED_FONT']],
  ['invalid-transition', ['POSTER_STATE_INVALID', 'STATUS_NOT_FINAL']],
  ['provider-authorization', ['POSTER_STATE_INVALID']],
  ['publish-pending', ['PUBLISH_QA_INVALID']],
  ['publish-all-na', ['PUBLISH_QA_INVALID']],
  ['publish-qr-na', ['PUBLISH_QA_INVALID']],
  ['publish-identity-na', ['PUBLISH_QA_INVALID']],
  ['publish-logo-asset-na', ['PUBLISH_QA_INVALID']],
]) {
  test(`Release blocks ${scenario}`, async (context) => {
    await assertReleaseBlocked(context, scenario, expectedCodes);
  });
}
