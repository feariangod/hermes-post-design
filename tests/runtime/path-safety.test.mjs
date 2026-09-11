import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, rm, symlink, unlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

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

async function createProject(context, name) {
  const temporaryRoot = await mkdtemp(path.join(os.tmpdir(), 'poster-path-safety-'));
  context.after(() => rm(temporaryRoot, { recursive: true, force: true }));
  const project = path.join(temporaryRoot, name);
  const initialized = run('node', [initPoster, '--output', project, '--title', 'Safe poster', '--type', 'digital']);
  assert.equal(initialized.status, 0, initialized.stderr);
  await symlink(path.join(skillRoot, 'node_modules'), path.join(project, 'node_modules'), 'dir');
  return { project, temporaryRoot };
}

test('prepare rejects an assets parent symlink without writing outside the project', async (context) => {
  const { project, temporaryRoot } = await createProject(context, 'parent-link');
  const outside = path.join(temporaryRoot, 'outside');
  await mkdir(outside);
  await rm(path.join(project, 'assets'), { recursive: true, force: true });
  await symlink(outside, path.join(project, 'assets'), 'dir');

  const prepared = run('node', [path.join(project, 'scripts/prepare-project.mjs'), '--project', project]);

  assert.notEqual(prepared.status, 0, prepared.stdout + prepared.stderr);
  assert.deepEqual(await import('node:fs/promises').then(({ readdir }) => readdir(outside)), []);
});

test('prepare rejects a symlinked manifest target without overwriting its referent', async (context) => {
  const { project, temporaryRoot } = await createProject(context, 'target-link');
  const outside = path.join(temporaryRoot, 'outside.json');
  await writeFile(outside, '{"keep": true}\n');
  await unlink(path.join(project, 'font-manifest.json'));
  await symlink(outside, path.join(project, 'font-manifest.json'));

  const prepared = run('node', [path.join(project, 'scripts/prepare-project.mjs'), '--project', project]);

  assert.notEqual(prepared.status, 0, prepared.stdout + prepared.stderr);
  assert.equal(await readFile(outside, 'utf8'), '{"keep": true}\n');
});

test('portable destination checks reject an injected Windows reparse-like redirect', async () => {
  const safetyUrl = pathToFileURL(path.join(skillRoot, 'scripts/path-safety.mjs')).href;
  const { assertSafeDestinationPath } = await import(safetyUrl);
  const root = path.resolve('/virtual/project');
  const destination = path.join(root, 'assets', 'fonts', 'font.woff2');
  const existing = new Set([root, path.join(root, 'assets')]);
  const missing = Object.assign(new Error('missing'), { code: 'ENOENT' });
  const fs = {
    async lstat(candidate) {
      if (!existing.has(candidate)) throw missing;
      return {
        isSymbolicLink: () => false,
        isDirectory: () => true,
        isFile: () => false,
      };
    },
    async realpath(candidate) {
      if (candidate === path.join(root, 'assets')) return path.resolve('/virtual/redirected-assets');
      return candidate;
    },
  };

  await assert.rejects(
    assertSafeDestinationPath(root, destination, { fs, platform: 'win32' }),
    /redirect|reparse|project/i,
  );
});
