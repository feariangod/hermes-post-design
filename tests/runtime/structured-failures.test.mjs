import assert from 'node:assert/strict';
import { chmod, mkdtemp, readFile, rm, symlink, unlink, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const skillRoot = path.join(repositoryRoot, 'src/hermes_post_design/resources/skills/creative/poster-design');
const initPoster = path.join(skillRoot, 'scripts/init-poster.mjs');

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

function assertStrictFailure(project, inspection, expectedBlocker) {
  assert.notEqual(inspection.status, 0, `inspect unexpectedly succeeded\nstdout:\n${inspection.stdout}\nstderr:\n${inspection.stderr}`);
  return readFile(path.join(project, 'qa-report.json'), 'utf8').then((contents) => {
    const report = JSON.parse(contents);
    assert.equal(report.status, 'FAIL');
    assert.equal(report.release.finalEligible, false);
    assert.ok(report.blockers.some((blocker) => blocker.code === expectedBlocker), JSON.stringify(report.blockers, null, 2));
  });
}

async function createMockedProject(context, scenario) {
  const temporaryRoot = await mkdtemp(path.join(skillRoot, '.structured-failure-'));
  context.after(() => rm(temporaryRoot, { recursive: true, force: true }));
  const project = path.join(temporaryRoot, `${scenario}-poster`);
  requireSuccess(run('node', [initPoster, '--output', project, '--title', 'Mock poster', '--type', 'digital']), 'node', [initPoster]);

  const inspectorPath = path.join(project, 'scripts/inspect-poster.mjs');
  const inspector = await readFile(inspectorPath, 'utf8');
  const productionImport = "import { chromium } from 'playwright';";
  assert.ok(inspector.includes(productionImport), 'generated inspector must import Playwright through its normal module specifier');
  await writeFile(inspectorPath, inspector.replace(productionImport, "import { chromium } from './mock-playwright.mjs';"));
  await writeFile(path.join(project, 'scripts/mock-playwright.mjs'), mockedPlaywrightSource(scenario));

  if (scenario === 'output-inspection') {
    await writeFile(path.join(project, 'assets'), 'fixture makes sourceDetails fail with ENOTDIR');
  }
  return project;
}

function mockedPlaywrightSource(scenario) {
  return `const scenario = ${JSON.stringify(scenario)};
let evaluateCalls = 0;

const page = {
  async goto() {
    if (scenario === 'navigation') throw new Error('mock navigation failure');
  },
  async addStyleTag() {},
  async evaluate() {
    evaluateCalls += 1;
    if (scenario === 'font-evaluation' && evaluateCalls === 1) throw new Error('mock font evaluation failure');
    if (scenario === 'page-evaluation' && evaluateCalls === 2) throw new Error('mock page evaluation failure');
    if (evaluateCalls === 1) return undefined;
    if (evaluateCalls === 2) {
      return {
        posterStatus: 'preview',
        posterCount: 1,
        poster: { clientWidth: 1080, clientHeight: 1440, scrollWidth: 1080, scrollHeight: 1440 },
        placeholders: [],
        overflows: [],
        undersizedText: [],
        undersizedMobileText: [],
        images: [],
        fonts: [],
        facts: [{ key: 'title', value: 'Mock poster', visible: true }],
        qrCodes: [],
      };
    }
    if (scenario === 'missing-font') return false;
    return true;
  },
};

export const chromium = {
  async launch() {
    if (scenario === 'browser-launch') throw new Error('mock browser launch failure');
    return {
      async newContext() {
        return {
          async route() {},
          async newPage() { return page; },
        };
      },
      async close() {},
    };
  },
};
`;
}

test('inspect --strict writes a failed QA report when a required bundled font is missing', async (context) => {
  const project = await createMockedProject(context, 'missing-font');
  const inspection = run('node', [path.join(project, 'scripts/inspect-poster.mjs'), '--project', project, '--strict']);
  await assertStrictFailure(project, inspection, 'FONT_LOAD_FAILED');
});

test('inspect --strict writes a failed QA report when an explicit browser cannot be resolved', async (context) => {
  const temporaryRoot = await mkdtemp(path.join(skillRoot, '.structured-failure-'));
  context.after(() => rm(temporaryRoot, { recursive: true, force: true }));
  const project = path.join(temporaryRoot, 'missing-browser-poster');

  requireSuccess(run('node', [initPoster, '--output', project, '--title', 'Missing browser', '--type', 'digital']), 'node', [initPoster]);

  const inspection = run('node', [
    path.join(project, 'scripts/inspect-poster.mjs'),
    '--project', project,
    '--strict',
    '--browser', path.join(project, 'browser-does-not-exist'),
  ]);
  await assertStrictFailure(project, inspection, 'BROWSER_RESOLUTION_FAILED');
});

test('inspect --strict structures a font manifest file-read failure', { skip: process.platform === 'win32' }, async (context) => {
  const temporaryRoot = await mkdtemp(path.join(skillRoot, '.structured-failure-'));
  context.after(() => rm(temporaryRoot, { recursive: true, force: true }));
  const project = path.join(temporaryRoot, 'font-validation-poster');
  requireSuccess(run('node', [initPoster, '--output', project, '--title', 'Font validation', '--type', 'digital']), 'node', [initPoster]);
  await symlink(path.join(skillRoot, 'node_modules'), path.join(project, 'node_modules'), 'dir');
  requireSuccess(run('node', [path.join(project, 'scripts/prepare-project.mjs'), '--project', project]), 'node', ['scripts/prepare-project.mjs']);
  await unlink(path.join(project, 'node_modules'));
  const manifest = JSON.parse(await readFile(path.join(project, 'font-manifest.json'), 'utf8'));
  const protectedFont = path.join(project, manifest.fonts[0].file);
  await chmod(protectedFont, 0o000);
  context.after(() => chmod(protectedFont, 0o644).catch(() => {}));

  const inspection = run('node', [path.join(project, 'scripts/inspect-poster.mjs'), '--project', project, '--strict']);
  await assertStrictFailure(project, inspection, 'FONT_VALIDATION_FAILED');
});

for (const [scenario, expectedBlocker] of [
  ['browser-launch', 'BROWSER_LAUNCH_FAILED'],
  ['navigation', 'NAVIGATION_FAILED'],
  ['font-evaluation', 'FONT_LOAD_FAILED'],
  ['page-evaluation', 'PAGE_EVALUATION_FAILED'],
  ['output-inspection', 'OUTPUT_INSPECTION_FAILED'],
]) {
  test(`inspect --strict preserves a structured failure for ${scenario}`, async (context) => {
    const project = await createMockedProject(context, scenario);
    const inspection = run('node', [path.join(project, 'scripts/inspect-poster.mjs'), '--project', project, '--strict']);
    await assertStrictFailure(project, inspection, expectedBlocker);
  });
}
