import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { access, mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const skillRoot = path.join(repositoryRoot, 'src/hermes_post_design/resources/skills/creative/poster-design');
const initPoster = path.join(skillRoot, 'scripts/init-poster.mjs');

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd ?? repositoryRoot,
    encoding: 'utf8',
    env: { ...process.env, ...options.env },
  });
  assert.equal(result.status, 0, `${command} ${args.join(' ')}\nstdout:\n${result.stdout}\nstderr:\n${result.stderr}`);
  return result.stdout;
}

async function sha256(filePath) {
  return createHash('sha256').update(await readFile(filePath)).digest('hex');
}

test('initialized poster project keeps contracts, dependencies, fonts, and licenses local', async (context) => {
  const temporaryRoot = await mkdtemp(path.join(os.tmpdir(), 'poster-portability-'));
  context.after(() => rm(temporaryRoot, { recursive: true, force: true }));
  const project = path.join(temporaryRoot, 'portable-poster');

  run('node', [initPoster, '--output', project, '--title', 'Portable poster', '--type', 'digital']);

  for (const relativePath of ['poster.json', 'publish-qa.json', 'package.json', 'package-lock.json', 'font-manifest.json']) {
    await access(path.join(project, relativePath));
  }

  const poster = JSON.parse(await readFile(path.join(project, 'poster.json'), 'utf8'));
  assert.deepEqual(poster, {
    version: 1,
    mode: 'publish',
    state: 'intake',
    conceptRevision: 0,
    direction: null,
    approvedCopy: [],
    provider: {
      adapter: 'deterministic-local',
      external: false,
      billed: false,
      authorizedCalls: 0,
      usedCalls: 0,
    },
  });

  const publishQa = JSON.parse(await readFile(path.join(project, 'publish-qa.json'), 'utf8'));
  assert.deepEqual(publishQa, {
    version: 1,
    status: 'PENDING',
    size: 'PENDING',
    facts: 'PENDING',
    identity: 'PENDING',
    logo: 'PENDING',
    qr: 'PENDING',
    mobile: 'PENDING',
    artifacts: 'PENDING',
  });
  const starterHtml = await readFile(path.join(project, 'poster.html'), 'utf8');
  assert.match(starterHtml, /data-placeholder="starter-preview"[^>]*>PREVIEW</);
  assert.match(starterHtml, /data-placeholder="starter-copy"[^>]*>Replace this starter content after the brief is approved\.</);

  run('npm', ['ci'], { cwd: project });
  run('npm', ['run', 'prepare'], { cwd: project });
  await access(path.join(project, 'node_modules/playwright/package.json'));
  await access(path.join(project, 'node_modules/fontkit/package.json'));

  const manifest = JSON.parse(await readFile(path.join(project, 'assets/fonts/font-manifest.json'), 'utf8'));
  assert.deepEqual(JSON.parse(await readFile(path.join(project, 'font-manifest.json'), 'utf8')), manifest);
  assert.ok(Array.isArray(manifest.fonts));
  assert.ok(manifest.fonts.length > 0);
  assert.deepEqual(
    manifest.fonts.filter((font) => font.file.includes('Chinese')).map((font) => font.samples),
    [['中文海报'], ['中'], ['中']],
  );
  for (const font of manifest.fonts) {
    assert.deepEqual(Object.keys(font).sort(), ['family', 'file', 'licenseFile', 'samples', 'sha256']);
    assert.equal(typeof font.family, 'string');
    assert.equal(typeof font.file, 'string');
    assert.equal(typeof font.sha256, 'string');
    assert.equal(typeof font.licenseFile, 'string');
    assert.ok(Array.isArray(font.samples));
    assert.doesNotMatch(font.samples.join(''), /\\u[0-9a-f]{4}/i);
    const fontPath = path.join(project, font.file);
    const licensePath = path.join(project, font.licenseFile);
    await access(fontPath);
    await access(licensePath);
    assert.equal(await sha256(fontPath), font.sha256);
  }

  const licenseManifest = JSON.parse(await readFile(path.join(project, 'font-license-manifest.json'), 'utf8'));
  assert.deepEqual(
    JSON.parse(await readFile(path.join(project, 'assets/licenses/font-license-manifest.json'), 'utf8')),
    licenseManifest,
  );
  assert.equal(licenseManifest.version, 1);
  assert.deepEqual(
    licenseManifest.records,
    manifest.fonts.map((font) => ({
      family: font.family,
      file: font.file,
      sha256: font.sha256,
      licenseFile: font.licenseFile,
      licenseId: 'OFL-1.1',
      licenseName: 'SIL Open Font License',
      licenseVersion: '1.1',
      sourcePackage: {
        'Ma Shan Zheng': '@fontsource/ma-shan-zheng@5.3.0',
        'Noto Sans SC': '@fontsource-variable/noto-sans-sc@5.3.0',
        'Noto Serif SC': '@fontsource-variable/noto-serif-sc@5.3.0',
      }[font.family],
    })),
  );

  const css = await readFile(path.join(project, 'styles.css'), 'utf8');
  for (const font of manifest.fonts) {
    assert.match(css, new RegExp(font.file.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  const cssFontUrls = [...css.matchAll(/url\(["']?([^"')]+\.(?:woff2?|ttf|otf))["']?\)/gi)]
    .map((match) => match[1]);
  assert.deepEqual(new Set(cssFontUrls), new Set(manifest.fonts.map((font) => font.file)));

  const renderOutput = run('npm', ['run', 'render'], { cwd: project });
  assert.doesNotMatch(renderOutput, /ERR_MODULE_NOT_FOUND/);
});
