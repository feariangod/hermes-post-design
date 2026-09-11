import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const contract = await import(path.join(
  repositoryRoot,
  'src/hermes_post_design/resources/skills/creative/poster-design/scripts/poster-contract.mjs',
));
const validatePosterState = contract.validatePosterState ?? (() => []);
const validatePublishQa = contract.validatePublishQa ?? (() => []);

function posterState(overrides = {}) {
  return {
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
    ...overrides,
  };
}

function publishQa(overrides = {}) {
  return {
    version: 1,
    status: 'PENDING',
    size: 'PENDING',
    facts: 'PENDING',
    identity: 'PENDING',
    logo: 'PENDING',
    qr: 'PENDING',
    mobile: 'PENDING',
    artifacts: 'PENDING',
    ...overrides,
  };
}

test('poster state accepts the deterministic intake default', () => {
  assert.deepEqual(validatePosterState(posterState()), []);
});

test('poster state rejects a workflow state beyond the selected mode', () => {
  const issues = validatePosterState(posterState({
    mode: 'concept',
    state: 'publish',
    direction: 'locked direction',
  }));
  assert.ok(issues.some((issue) => /cannot reach state publish/i.test(issue)), issues.join('\n'));
});

test('poster state rejects needs_rebrief before the concept revision is exhausted', () => {
  const issues = validatePosterState(posterState({
    mode: 'concept',
    state: 'needs_rebrief',
    direction: 'rejected direction',
  }));
  assert.ok(issues.some((issue) => /needs_rebrief requires conceptRevision 1/i.test(issue)), issues.join('\n'));
});

test('poster state rejects used provider calls above the authorized budget', () => {
  const issues = validatePosterState(posterState({
    provider: {
      adapter: 'fake-image-adapter',
      external: true,
      billed: true,
      authorizedCalls: 1,
      usedCalls: 2,
    },
  }));
  assert.ok(issues.some((issue) => /usedCalls must not exceed authorizedCalls/i.test(issue)), issues.join('\n'));
});

for (const [providerKind, article] of [['external', 'an'], ['billed', 'a']]) {
  test(`poster state rejects ${article} ${providerKind} provider without an authorization budget`, () => {
    const issues = validatePosterState(posterState({
      provider: {
        adapter: 'fake-image-adapter',
        external: providerKind === 'external',
        billed: providerKind === 'billed',
        authorizedCalls: 0,
        usedCalls: 0,
      },
    }));
    assert.ok(issues.some((issue) => /requires at least one authorized call/i.test(issue)), issues.join('\n'));
  });
}

test('poster state accepts an authorized external provider within budget', () => {
  assert.deepEqual(validatePosterState(posterState({
    state: 'concept',
    direction: 'approved direction',
    approvedCopy: ['Approved headline'],
    provider: {
      adapter: 'fake-image-adapter',
      external: true,
      billed: true,
      authorizedCalls: 1,
      usedCalls: 1,
    },
  })), []);
});

test('publish QA accepts the explicit all-pending starter state', () => {
  assert.deepEqual(validatePublishQa(publishQa()), []);
});

test('publish QA rejects PASS while any required field remains PENDING', () => {
  const issues = validatePublishQa(publishQa({
    status: 'PASS',
    size: 'PASS',
    facts: 'PASS',
    identity: 'PASS',
    logo: 'PASS',
    qr: 'PASS',
    mobile: 'PASS',
  }));
  assert.ok(issues.some((issue) => /artifacts must be PASS or NOT_APPLICABLE/i.test(issue)), issues.join('\n'));
});

test('publish QA accepts PASS only after every field is resolved', () => {
  assert.deepEqual(validatePublishQa(publishQa({
    status: 'PASS',
    size: 'PASS',
    facts: 'PASS',
    identity: 'PASS',
    logo: 'PASS',
    qr: 'NOT_APPLICABLE',
    mobile: 'PASS',
    artifacts: 'PASS',
  })), []);
});
