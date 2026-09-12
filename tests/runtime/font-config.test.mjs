import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { cp, link, mkdir, mkdtemp, readFile, readdir, rm, symlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { validateFontManifest, validateAssetManifest } from '../../src/hermes_post_design/resources/skills/creative/poster-design/scripts/poster-contract.mjs';

const skill = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../src/hermes_post_design/resources/skills/creative/poster-design');
const digest = (value) => createHash('sha256').update(value).digest('hex');
const roles = (family) => ({ heading: family, body: family, numeral: family });
async function fixture(t, config) {
  const project = await mkdtemp(path.join(os.tmpdir(), 'font-config-'));
  t.after(() => rm(project, { recursive: true, force: true }));
  await symlink(path.join(skill, 'node_modules'), path.join(project, 'node_modules'));
  await writeFile(path.join(project, 'styles.css'), '@import url("font-faces.css");');
  if (config) await writeFile(path.join(project, 'font-config.json'), JSON.stringify(config));
  return project;
}
function prepare(project) {
  return spawnSync(process.execPath, [path.join(skill, 'scripts/prepare-project.mjs'), '--project', project], { encoding: 'utf8' });
}
async function findings(project) {
  return validateFontManifest(project, JSON.parse(await readFile(path.join(project, 'font-manifest.json'))));
}
test('selected single bundled family prepares and validates without other families', async (t) => {
  const project = await fixture(t, { version: 1, roles: roles('Noto Sans SC') });
  await rm(path.join(project, 'node_modules'));
  await mkdir(path.join(project, 'node_modules/@fontsource-variable'), { recursive: true });
  await symlink(path.join(skill, 'node_modules/@fontsource-variable/noto-sans-sc'), path.join(project, 'node_modules/@fontsource-variable/noto-sans-sc'));
  const result = prepare(project);
  assert.equal(result.status, 0, result.stderr);
  const manifest = JSON.parse(await readFile(path.join(project, 'font-manifest.json')));
  assert.deepEqual([...new Set(manifest.fonts.map((font) => font.family))], ['Noto Sans SC']);
  assert.deepEqual(await findings(project), []);
  assert.match(await readFile(path.join(project, 'font-faces.css'), 'utf8'), /--font-heading: "Noto Sans SC"/);
});
test('missing config preserves the three-family legacy preparation and validation', async (t) => {
  const project = await fixture(t);
  const result = prepare(project);
  assert.equal(result.status, 0, result.stderr);
  const manifest = JSON.parse(await readFile(path.join(project, 'font-manifest.json')));
  assert.deepEqual(new Set(manifest.fonts.map((font) => font.family)), new Set(['Noto Sans SC', 'Noto Serif SC', 'Ma Shan Zheng']));
  assert.deepEqual(await findings(project), []);
});

test('swapping roles within the same family set requires font preparation again', async (t) => {
  const config = { version: 1, roles: { heading: 'Noto Serif SC', body: 'Noto Sans SC', numeral: 'Noto Sans SC' } };
  const project = await fixture(t, config);
  assert.equal(prepare(project).status, 0);
  [config.roles.heading, config.roles.body] = [config.roles.body, config.roles.heading];
  await writeFile(path.join(project, 'font-config.json'), JSON.stringify(config));
  assert.ok((await findings(project)).some((entry) => entry.code === 'FONT_CONFIG_INVALID'));
  assert.equal(prepare(project).status, 0);
  assert.deepEqual(await findings(project), []);
  const css = await readFile(path.join(project, 'font-faces.css'), 'utf8');
  assert.match(css, /--font-heading: "Noto Sans SC"/);
  assert.match(css, /--font-body: "Noto Serif SC"/);
});

async function customFixture(t) {
  const project = await fixture(t);
  await mkdir(path.join(project, 'assets/fonts'), { recursive: true });
  await mkdir(path.join(project, 'assets/licenses'), { recursive: true });
  // The real family is deliberately declared under a brand alias. The approved
  // binary digest, rather than an editable family-name assertion, establishes it.
  const css = await readFile(path.join(skill, 'node_modules/@fontsource/ma-shan-zheng/400.css'), 'utf8');
  const source = css.match(/url\(([^)]+\.woff2)\)/)[1];
  const file = 'assets/fonts/brand.woff2';
  const licenseFile = 'assets/licenses/brand.txt';
  await cp(path.resolve(skill, 'node_modules/@fontsource/ma-shan-zheng', source), path.join(project, file));
  await cp(path.join(skill, 'node_modules/@fontsource/ma-shan-zheng/LICENSE'), path.join(project, licenseFile));
  await writeFile(path.join(project, 'authorization.txt'), 'Test fixture: authorized project use of supplied OFL font.');
  const sha256 = digest(await readFile(path.join(project, file)));
  const licenseSha256 = digest(await readFile(path.join(project, licenseFile)));
  const font = { family: 'Brand Display', file, sha256, licenseFile, licenseSha256, licenseId: 'OFL-1.1', licenseName: 'SIL Open Font License', licenseVersion: '1.1', source: 'https://github.com/google/fonts/tree/main/ofl/mashanzheng', authorization: { approved: true, fontSha256: sha256, licenseSha256, evidenceFile: 'authorization.txt', evidenceSha256: digest(await readFile(path.join(project, 'authorization.txt'))) } };
  const config = { version: 1, roles: roles(font.family), customFonts: [font] };
  await writeFile(path.join(project, 'font-config.json'), JSON.stringify(config));
  return { project, config };
}
test('custom font with digest-bound source, license and approval prepares and validates', async (t) => {
  const { project } = await customFixture(t);
  const result = prepare(project);
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(await findings(project), []);
  await writeFile(path.join(project, 'assets/fonts/brand.woff2'), 'substituted');
  assert.ok((await findings(project)).some((entry) => entry.code === 'FONT_CONFIG_INVALID'));
});
for (const mutation of ['authorization', 'approved-digest', 'traversal', 'symlink', 'license', 'source', 'malformed']) {
  test(`custom font rejects ${mutation}`, async (t) => {
    const { project, config } = await customFixture(t);
    const font = config.customFonts[0];
    if (mutation === 'authorization') delete font.authorization;
    if (mutation === 'approved-digest') font.authorization.fontSha256 = '0'.repeat(64);
    if (mutation === 'traversal') font.file = 'assets/fonts/../fonts/brand.woff2';
    if (mutation === 'source') font.source = 'unknown';
    if (mutation === 'license') await writeFile(path.join(project, font.licenseFile), 'substituted');
    if (mutation === 'symlink') {
      await symlink(path.join(project, 'authorization.txt'), path.join(project, 'redirect.txt'));
      font.authorization.evidenceFile = 'redirect.txt';
    }
    if (mutation === 'malformed') {
      await writeFile(path.join(project, font.file), 'not a font');
      font.sha256 = digest('not a font');
      font.authorization.fontSha256 = font.sha256;
    }
    await writeFile(path.join(project, 'font-config.json'), JSON.stringify(config));
    assert.notEqual(prepare(project).status, 0);
  });
}
test('changing authorization evidence invalidates an already prepared project', async (t) => {
  const { project } = await customFixture(t);
  assert.equal(prepare(project).status, 0);
  await writeFile(path.join(project, 'authorization.txt'), 'changed approval');
  assert.ok((await findings(project)).some((entry) => entry.code === 'FONT_CONFIG_INVALID'));
});
test('verified extensionless custom license and asset-local approval are excluded exactly', async (t) => {
  const { project, config } = await customFixture(t);
  const font = config.customFonts[0];
  await cp(path.join(project, font.licenseFile), path.join(project, 'assets/licenses/LICENSE'));
  font.licenseFile = 'assets/licenses/LICENSE';
  await cp(path.join(project, 'authorization.txt'), path.join(project, 'assets/approval.pdf'));
  font.authorization.evidenceFile = 'assets/approval.pdf';
  await writeFile(path.join(project, 'font-config.json'), JSON.stringify(config));
  assert.equal(prepare(project).status, 0);
  assert.deepEqual(await findings(project), []);
  assert.deepEqual(await validateAssetManifest(project, { version: 1, assets: [] }), []);
  await writeFile(path.join(project, 'assets/unrelated.pdf'), 'unlicensed asset');
  const unlicensed = await validateAssetManifest(project, { version: 1, assets: [] });
  assert.ok(unlicensed.some((entry) => entry.code === 'ASSET_LICENSE_MISSING' && entry.evidence.path === 'assets/unrelated.pdf'));
  await writeFile(path.join(project, 'assets/approval.pdf'), 'tampered approval');
  assert.ok((await validateAssetManifest(project, { version: 1, assets: [] })).some((entry) => entry.code === 'ASSET_LICENSE_INVALID'));
});
for (const target of ['licenses.md', 'font-faces.css', 'font-manifest.json', 'font-license-manifest.json', 'assets/fonts/font-manifest.json', 'assets/licenses/font-license-manifest.json']) {
  test(`prepare preserves approval colliding with generated ${target}`, async (t) => {
    const { project, config } = await customFixture(t);
    await cp(path.join(project, 'authorization.txt'), path.join(project, target));
    config.customFonts[0].authorization.evidenceFile = target;
    await writeFile(path.join(project, 'font-config.json'), JSON.stringify(config));
    const before = await readFile(path.join(project, target));
    const entries = await readdir(project);
    const result = prepare(project);
    assert.notEqual(result.status, 0, result.stdout);
    assert.match(result.stderr, /collid/i);
    assert.deepEqual(await readFile(path.join(project, target)), before);
    assert.deepEqual(await readdir(project), entries);
  });
}
test('prepare rejects a generated destination alias to input evidence before writes', async (t) => {
  const { project } = await customFixture(t);
  await link(path.join(project, 'authorization.txt'), path.join(project, 'licenses.md'));
  const before = await readFile(path.join(project, 'authorization.txt'));
  const result = prepare(project);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /collid/i);
  assert.deepEqual(await readFile(path.join(project, 'authorization.txt')), before);
  assert.deepEqual(await readFile(path.join(project, 'licenses.md')), before);
});
for (const kind of ['font', 'license']) {
  test(`prepare preserves custom ${kind} input colliding with an output`, async (t) => {
    const { project, config } = await customFixture(t);
    const font = config.customFonts[0];
    let target;
    let field;
    if (kind === 'font') {
      const css = await readFile(path.join(skill, 'node_modules/@fontsource/ma-shan-zheng/400.css'), 'utf8');
      target = `assets/fonts/ma-shan-zheng/${path.basename(css.match(/url\(([^)]+\.woff2)\)/)[1])}`;
      await mkdir(path.dirname(path.join(project, target)), { recursive: true });
      config.roles.body = 'Ma Shan Zheng';
      field = 'file';
    } else {
      target = 'assets/licenses/font-license-manifest.json';
      field = 'licenseFile';
    }
    await cp(path.join(project, font[field]), path.join(project, target));
    font[field] = target;
    await writeFile(path.join(project, 'font-config.json'), JSON.stringify(config));
    const before = await readFile(path.join(project, target));
    const result = prepare(project);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /collid/i);
    assert.deepEqual(await readFile(path.join(project, target)), before);
  });
}
test('legacy asset enumeration still rejects unlicensed files hidden in font directories', async (t) => {
  const project = await fixture(t);
  await mkdir(path.join(project, 'assets/fonts'), { recursive: true });
  await writeFile(path.join(project, 'assets/fonts/hero.png'), 'unlicensed image');
  const actual = await validateAssetManifest(project, { version: 1, assets: [] });
  assert.ok(actual.some((entry) => entry.code === 'ASSET_LICENSE_MISSING' && entry.evidence.path === 'assets/fonts/hero.png'));
  await symlink(path.join(project, 'assets/fonts/hero.png'), path.join(project, 'assets/redirect.png'));
  assert.ok((await validateAssetManifest(project, { version: 1, assets: [] })).some((entry) => entry.code === 'ASSET_LICENSE_INVALID'));
});
