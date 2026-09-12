import { createHash } from 'node:crypto';
import { lstat, readFile } from 'node:fs/promises';
import path from 'node:path';
import * as fontkit from 'fontkit';
import { assertSafeDestinationPath } from './path-safety.mjs';

export const BUNDLED_FAMILIES = ['Ma Shan Zheng', 'Noto Sans SC', 'Noto Serif SC'];
const digest = (buffer) => createHash('sha256').update(buffer).digest('hex');
const hashPattern = /^[0-9a-f]{64}$/;
const object = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

async function verifiedFile(project, relative, expected, prefix = '') {
  if (typeof relative !== 'string' || !relative.startsWith(prefix)
      || !/^[A-Za-z0-9_./ -]+$/.test(relative) || relative.startsWith('/')
      || relative.split('/').some((part) => !part || part === '.' || part === '..')) {
    throw new Error('Font evidence requires a normalized project-local path');
  }
  const file = path.join(project, relative);
  await assertSafeDestinationPath(project, file);
  if (!(await lstat(file)).isFile()) throw new Error('Font evidence must be a regular file');
  const buffer = await readFile(file);
  if (!hashPattern.test(expected ?? '') || digest(buffer) !== expected) {
    throw new Error(`Font evidence digest mismatch: ${relative}`);
  }
  if (!buffer.length) throw new Error(`Font evidence is empty: ${relative}`);
  return buffer;
}

export async function loadFontConfig(project) {
  const configPath = path.join(project, 'font-config.json');
  let config;
  try {
    await assertSafeDestinationPath(project, configPath);
    const stat = await lstat(configPath);
    if (!stat.isFile()) throw new Error('font-config.json must be a regular file');
    config = JSON.parse(await readFile(configPath, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT') return { roles: null, families: [...BUNDLED_FAMILIES], customFonts: [] };
    throw error;
  }
  if (!object(config) || config.version !== 1 || !object(config.roles)
      || Object.keys(config.roles).sort().join(',') !== 'body,heading,numeral'
      || (config.customFonts !== undefined && !Array.isArray(config.customFonts))) {
    throw new Error('font-config.json requires version 1 and heading/body/numeral roles');
  }
  const customFonts = config.customFonts ?? [];
  const names = new Set(BUNDLED_FAMILIES);
  const files = new Set();
  for (const font of customFonts) {
    if (!object(font) || typeof font.family !== 'string' || !/^[\p{L}\p{N}][\p{L}\p{N} _-]*$/u.test(font.family)
        || names.has(font.family) || files.has(font.file)) throw new Error('Custom font families and files must be unique; bundled names cannot be overridden');
    names.add(font.family);
    files.add(font.file);
    const authorization = font.authorization;
    if (!object(authorization) || authorization.approved !== true
        || authorization.fontSha256 !== font.sha256 || authorization.licenseSha256 !== font.licenseSha256) {
      throw new Error('Custom fonts require explicit approval bound to both font and license digests');
    }
    for (const key of ['licenseId', 'licenseName', 'licenseVersion']) {
      if (typeof font[key] !== 'string' || !font[key].trim() || /^(unknown|pending|tbd)$/i.test(font[key])) throw new Error(`Custom font requires ${key}`);
    }
    // Provenance can be a publisher URL or a named local delivery, never a bare claim.
    if (typeof font.source !== 'string' || !/^(https?:\/\/[^\s/]+\/\S+|project:[^\r\n]{8,})$/.test(font.source)) {
      throw new Error('Custom font source must be a concrete URL or project: delivery reference');
    }
    if (!/\.(woff2?|ttf|otf)$/i.test(font.file ?? '')) throw new Error('Custom font must be WOFF2, WOFF, TTF or OTF');
    const buffer = await verifiedFile(project, font.file, font.sha256, 'assets/fonts/');
    await verifiedFile(project, font.licenseFile, font.licenseSha256, 'assets/licenses/');
    if ([font.file, font.licenseFile, 'font-config.json'].includes(authorization.evidenceFile)) {
      throw new Error('Authorization evidence must be a separate project file');
    }
    await verifiedFile(project, authorization.evidenceFile, authorization.evidenceSha256);
    const parsed = fontkit.create(buffer);
    if (!Array.isArray(parsed.characterSet) || !parsed.characterSet.length) throw new Error('Custom font binary has no glyphs');
  }
  const families = [...new Set(Object.values(config.roles))];
  if (families.some((family) => typeof family !== 'string' || !names.has(family))) throw new Error('Every font role must select a bundled or evidenced custom family');
  if (customFonts.some((font) => !families.includes(font.family))) throw new Error('Custom fonts must be selected by at least one role');
  return { roles: config.roles, families, customFonts };
}

export function customLicensePolicy(font) {
  return { licenseFile: font.licenseFile, licenseSha256: font.licenseSha256, licenseId: font.licenseId,
    licenseName: font.licenseName, licenseVersion: font.licenseVersion, sourcePackage: font.source };
}
