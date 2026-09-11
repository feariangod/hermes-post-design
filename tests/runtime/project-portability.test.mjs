import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
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

function installedBrowser() {
  const candidates = [
    process.env.POSTER_TEST_BROWSER,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  ].filter(Boolean);
  return candidates.find(existsSync);
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

  run('npm', ['ci'], { cwd: project });
  run('npm', ['run', 'prepare'], { cwd: project });
  await access(path.join(project, 'node_modules/playwright/package.json'));

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

  const css = await readFile(path.join(project, 'styles.css'), 'utf8');
  for (const font of manifest.fonts) {
    assert.match(css, new RegExp(font.file.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }

  const browser = installedBrowser();
  assert.ok(browser, 'Set POSTER_TEST_BROWSER or install Chrome/Edge for the portability render fixture.');
  const renderOutput = run('npm', ['run', 'render', '--', '--browser', browser], { cwd: project });
  assert.doesNotMatch(renderOutput, /ERR_MODULE_NOT_FOUND/);
});
