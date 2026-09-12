import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { copyFile, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const fixture = path.join(repositoryRoot, 'tests/fixtures/fake-image-adapter.mjs');
const contract = await import(path.join(
  repositoryRoot,
  'src/hermes_post_design/resources/skills/creative/poster-design/scripts/poster-contract.mjs',
));

async function sha256(filePath) {
  return createHash('sha256').update(await readFile(filePath)).digest('hex');
}

function invoke(args, secret) {
  return spawnSync(process.execPath, [fixture, ...args], {
    cwd: repositoryRoot,
    encoding: 'utf8',
    env: { ...process.env, FAKE_IMAGE_ADAPTER_CREDENTIAL: secret },
  });
}

test('authorized fake adapter hands off an artifact without network or credential leakage', async (context) => {
  const temporaryRoot = await mkdtemp(path.join(os.tmpdir(), 'poster-fake-adapter-'));
  context.after(() => rm(temporaryRoot, { recursive: true, force: true }));
  const secret = 'FAKE_ADAPTER_SECRET_MUST_NOT_PERSIST';
  const source = await readFile(fixture, 'utf8');
  assert.doesNotMatch(source, /node:(?:http|https|http2|net|tls|dns|dgram)/);
  assert.doesNotMatch(source, /\bfetch\s*\(/);

  const adapterArtifact = path.join(temporaryRoot, 'adapter-output.png');
  const result = invoke([
    '--output', adapterArtifact,
    '--authorized-calls', '1',
  ], secret);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.deepEqual(payload.provider, {
    adapter: 'fake-image-adapter',
    external: true,
    billed: true,
    authorizedCalls: 1,
    usedCalls: 1,
  });
  assert.equal(await sha256(adapterArtifact), payload.artifact.sha256);

  const project = path.join(temporaryRoot, 'project');
  const handedOffArtifact = path.join(project, 'assets/generated/concept.png');
  await mkdir(path.dirname(handedOffArtifact), { recursive: true });
  await copyFile(payload.artifact.path, handedOffArtifact);
  assert.equal(await sha256(handedOffArtifact), payload.artifact.sha256);

  const poster = {
    version: 1,
    mode: 'concept',
    state: 'concept',
    conceptRevision: 0,
    direction: 'authorized fake adapter fixture',
    approvedCopy: ['Approved fixture copy'],
    provider: payload.provider,
  };
  assert.deepEqual(contract.validatePosterState(poster), []);
  await writeFile(path.join(project, 'poster.json'), `${JSON.stringify(poster, null, 2)}\n`);
  const stateText = await readFile(path.join(project, 'poster.json'), 'utf8');
  assert.doesNotMatch(stateText, new RegExp(secret));
  assert.doesNotMatch(JSON.stringify(payload), new RegExp(secret));

  const failure = invoke([
    '--output', path.join(temporaryRoot, 'unused.png'),
    '--authorized-calls', '1',
    '--fail', 'true',
  ], secret);
  assert.equal(failure.status, 1);
  assert.deepEqual(JSON.parse(failure.stderr), {
    success: false,
    error: { type: 'adapter_error', message: 'Fake image adapter failed' },
  });
  assert.doesNotMatch(failure.stderr, new RegExp(secret));
});
