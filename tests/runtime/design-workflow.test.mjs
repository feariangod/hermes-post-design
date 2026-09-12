import assert from 'node:assert/strict';
import { cp, mkdtemp, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import * as contract from '../../src/hermes_post_design/resources/skills/creative/poster-design/scripts/poster-contract.mjs';

function design(overrides = {}) {
  return {
    version: 1,
    objective: 'Encourage registration',
    audience: 'Local design students',
    viewingContext: 'Shared in a phone chat',
    firstGlance: 'One clear workshop title',
    action: 'Register using the supplied URL',
    informationDensity: 'medium',
    hierarchy: [{ copyIndex: 0, role: 'headline', priority: 1 }],
    brand: { preserve: ['Original mark'], avoid: ['Decorative badges'] },
    route: { kind: 'layered', reason: 'Original logo and editable date' },
    exploration: { approach: 'direct', maxStudies: 0, directionBudget: 3 },
    layers: [{ id: 'headline', role: 'headline', treatment: 'editable', source: null }],
    approval: { status: 'pending', evidence: null, locked: [], flexible: ['spacing', 'type-size'] },
    reviewContexts: ['Phone preview at 360px width'],
    deliverables: [{ id: 'primary', format: 'png', usage: 'Phone chat', config: 'poster.config.json' }],
    rebriefReason: null,
    ...overrides,
  };
}

function poster(overrides = {}) {
  return {
    version: 1, mode: 'publish', state: 'concept', conceptRevision: 0,
    direction: 'One title with a spacious photo composition',
    approvedCopy: ['Design workshop'],
    provider: { adapter: 'deterministic-local', external: false, billed: false, authorizedCalls: 0, usedCalls: 0 },
    design: design(),
    ...overrides,
  };
}

test('dense information recommends deterministic layout regardless of image availability', () => {
  assert.equal(contract.recommendProductionRoute?.(design({ informationDensity: 'high' })), 'deterministic');
});

test('original brand layers recommend a layered composition', () => {
  assert.equal(contract.recommendProductionRoute?.(design({
    informationDensity: 'low', layers: [{ role: 'product', treatment: 'original' }],
  })), 'layered');
});

test('visual-led work without exact asset layers can recommend an image-led route', () => {
  assert.equal(contract.recommendProductionRoute?.(design({ informationDensity: 'low', layers: [] })), 'image-led');
});

test('a recorded direction budget permits more than one concept revision', () => {
  assert.deepEqual(contract.validatePosterState(poster({ conceptRevision: 3 })), []);
});

test('exhausting a direction budget does not prevent local layout refinements', () => {
  assert.deepEqual(contract.validatePosterState(poster({
    state: 'publish', conceptRevision: 3,
    design: design({ approval: {
      status: 'confirmed', evidence: 'User approved the main subject and mood',
      locked: ['subject', 'mood', 'approvedCopy'], flexible: ['spacing', 'type-size'],
    } }),
  })), []);
});

test('new design projects cannot publish without a recorded concept approval', () => {
  const issues = contract.validatePosterState(poster({ state: 'publish' }));
  assert.ok(issues.some((issue) => /approval.*confirmed/.test(issue)), issues.join('\n'));
});

test('approval scope cannot mark the same property both locked and flexible', () => {
  const issues = contract.validatePosterState(poster({ design: design({ approval: {
    status: 'confirmed', evidence: 'Approved', locked: ['spacing'], flexible: ['spacing'],
  } }) }));
  assert.ok(issues.some((issue) => /locked.*flexible/.test(issue)), issues.join('\n'));
});

test('design agreement refuses hierarchy references to nonexistent approved copy', () => {
  const issues = contract.validatePosterState(poster({ design: design({
    hierarchy: [{ copyIndex: 7, role: 'headline', priority: 1 }],
  }) }));
  assert.ok(issues.some((issue) => /copyIndex/.test(issue)), issues.join('\n'));
});

test('advanced design work records the communication objective', () => {
  const issues = contract.validatePosterState(poster({ design: design({ objective: null }) }));
  assert.ok(issues.some((issue) => /objective/.test(issue)), issues.join('\n'));
});

test('changed requirements can trigger rebrief before a revision counter is exhausted', () => {
  assert.deepEqual(contract.validatePosterState(poster({
    state: 'needs_rebrief', conceptRevision: 0,
    design: design({ rebriefReason: 'The user changed the audience from students to trade buyers' }),
  })), []);
});

test('unrecorded budget expansion is rejected', () => {
  const issues = contract.validatePosterState(poster({ conceptRevision: 4 }));
  assert.ok(issues.some((issue) => /directionBudget/.test(issue)), issues.join('\n'));
});

test('legacy projects without a design agreement still validate', () => {
  const value = poster();
  delete value.design;
  assert.deepEqual(contract.validatePosterState(value), []);
});

test('legacy projects cannot silently gain an unbounded direction budget', () => {
  const value = poster({ conceptRevision: 2 });
  delete value.design;
  assert.ok(contract.validatePosterState(value).some((issue) => /conceptRevision/.test(issue)));
});

test('changing font role configuration invalidates the recorded source hashes', async (t) => {
  const project = await mkdtemp(path.join(os.tmpdir(), 'design-source-'));
  t.after(() => rm(project, { recursive: true, force: true }));
  await cp(new URL('../../src/hermes_post_design/resources/skills/creative/poster-design/templates/poster-starter/', import.meta.url), project, { recursive: true });
  await writeFile(path.join(project, 'font-license-manifest.json'), JSON.stringify({ version: 1, records: [] }));
  const before = await contract.collectProjectSourceHashes(project);
  await writeFile(path.join(project, 'font-config.json'), JSON.stringify({ version: 1, roles: { heading: 'Noto Serif SC', body: 'Noto Sans SC', numeral: 'Noto Sans SC' } }));
  const after = await contract.collectProjectSourceHashes(project);
  assert.equal(typeof before['font-config.json'], 'string');
  assert.notEqual(before['font-config.json'], after['font-config.json']);
});
