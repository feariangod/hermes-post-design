import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, unlink } from 'node:fs/promises';
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

test('inspect --strict writes a failed QA report when a required bundled font is missing', async (context) => {
  const temporaryRoot = await mkdtemp(path.join(skillRoot, '.structured-failure-'));
  context.after(() => rm(temporaryRoot, { recursive: true, force: true }));
  const project = path.join(temporaryRoot, 'missing-font-poster');

  requireSuccess(run('node', [initPoster, '--output', project, '--title', 'Missing font', '--type', 'digital']), 'node', [initPoster]);
  requireSuccess(run('npm', ['ci', '--ignore-scripts', '--offline'], { cwd: project }), 'npm', ['ci', '--ignore-scripts', '--offline']);
  requireSuccess(run('node', [path.join(project, 'scripts/prepare-project.mjs'), '--project', project]), 'node', ['prepare-project.mjs']);
  await unlink(path.join(project, 'assets/fonts/NotoSansSC-ChineseSubset.woff2'));

  const inspection = run('node', [path.join(project, 'scripts/inspect-poster.mjs'), '--project', project, '--strict']);
  assert.notEqual(inspection.status, 0, `inspect unexpectedly succeeded\nstdout:\n${inspection.stdout}\nstderr:\n${inspection.stderr}`);

  const report = JSON.parse(await readFile(path.join(project, 'qa-report.json'), 'utf8'));
  assert.equal(report.status, 'FAIL');
  assert.equal(report.release.finalEligible, false);
  assert.ok(report.blockers.some((blocker) => blocker.code === 'FONT_LOAD_FAILED'), JSON.stringify(report.blockers, null, 2));
});

test('inspect --strict writes a failed QA report when an explicit browser cannot be resolved', async (context) => {
  const temporaryRoot = await mkdtemp(path.join(skillRoot, '.structured-failure-'));
  context.after(() => rm(temporaryRoot, { recursive: true, force: true }));
  const project = path.join(temporaryRoot, 'missing-browser-poster');

  requireSuccess(run('node', [initPoster, '--output', project, '--title', 'Missing browser', '--type', 'digital']), 'node', [initPoster]);
  requireSuccess(run('npm', ['ci', '--ignore-scripts', '--offline'], { cwd: project }), 'npm', ['ci', '--ignore-scripts', '--offline']);

  const inspection = run('node', [
    path.join(project, 'scripts/inspect-poster.mjs'),
    '--project', project,
    '--strict',
    '--browser', path.join(project, 'browser-does-not-exist'),
  ]);
  assert.notEqual(inspection.status, 0, `inspect unexpectedly succeeded\nstdout:\n${inspection.stdout}\nstderr:\n${inspection.stderr}`);

  const report = JSON.parse(await readFile(path.join(project, 'qa-report.json'), 'utf8'));
  assert.equal(report.status, 'FAIL');
  assert.equal(report.release.finalEligible, false);
  assert.ok(report.blockers.some((blocker) => blocker.code === 'BROWSER_RESOLUTION_FAILED'), JSON.stringify(report.blockers, null, 2));
});
