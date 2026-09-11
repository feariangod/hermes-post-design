import { createHash } from 'node:crypto';
import { lstat, readFile, readdir, realpath } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as fontkit from 'fontkit';

const MAX_CANVAS_DIMENSION_PX = 20_000;
const MAX_CANVAS_AREA_PX = 100_000_000;
const MAX_PRINT_DIMENSION_MM = 2_000;
const POSTER_STATES = ['intake', 'route_selected', 'concept', 'visual_locked', 'publish', 'release'];
const MODE_MAX_STATE = { concept: 'visual_locked', publish: 'publish', release: 'release' };
const PUBLISH_QA_FIELDS = ['size', 'facts', 'identity', 'logo', 'qr', 'mobile', 'artifacts'];
const REQUIRED_FONT_FAMILIES = new Set(['Noto Sans SC', 'Noto Serif SC', 'Ma Shan Zheng']);
const ALWAYS_APPLICABLE_PUBLISH_FIELDS = new Set(['size', 'facts', 'mobile', 'artifacts']);
const FONT_LICENSE_POLICY = {
  'Ma Shan Zheng': {
    licenseFile: 'assets/licenses/MaShanZheng-OFL-1.1.txt',
    licenseSha256: '37784825d863bab31cdff1f4bfabae5b8d8e9913b91db2064a6b803b2edc92db',
    sourcePackage: '@fontsource/ma-shan-zheng@5.3.0',
  },
  'Noto Sans SC': {
    licenseFile: 'assets/licenses/NotoSansSC-OFL-1.1.txt',
    licenseSha256: '18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3',
    sourcePackage: '@fontsource-variable/noto-sans-sc@5.3.0',
  },
  'Noto Serif SC': {
    licenseFile: 'assets/licenses/NotoSerifSC-OFL-1.1.txt',
    licenseSha256: '18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3',
    sourcePackage: '@fontsource-variable/noto-serif-sc@5.3.0',
  },
};
const FONT_FAMILY_PREFIXES = {
  'Ma Shan Zheng': ['Ma Shan Zheng'],
  'Noto Sans SC': ['Noto Sans SC'],
  'Noto Serif SC': ['Noto Serif SC'],
};
const FONT_STYLE_SUFFIX = /^(?:Thin|ExtraLight|Light|Regular|Medium|SemiBold|Bold|ExtraBold|Black)(?:Italic)?$/i;
const LICENSE_RECORD_FIELDS = ['family', 'file', 'sha256', 'licenseFile', 'licenseSha256', 'licenseId', 'licenseName', 'licenseVersion', 'sourcePackage'];
const ASSET_RECORD_FIELDS = ['path', 'sha256', 'source', 'creator', 'license', 'authorization', 'attribution'];
const DUPLICATE_STAGE_FIELDS = ['status', 'mode', 'state', 'approvedCopy'];

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isPositiveInteger(value) {
  return Number.isInteger(value) && value > 0;
}

function isPositiveFinite(value) {
  return Number.isFinite(value) && value > 0;
}

export function isFinalStatus(value) {
  return typeof value === 'string' && value.trim() === 'final';
}

export function validatePosterState(value) {
  const issues = [];
  if (!isObject(value)) return ['poster state must be a JSON object'];
  if (value.version !== 1) issues.push('version must be 1');
  if (!Object.hasOwn(MODE_MAX_STATE, value.mode)) {
    issues.push('mode must be concept, publish, or release');
  }
  if (![...POSTER_STATES, 'needs_rebrief'].includes(value.state)) {
    issues.push('state must be intake, route_selected, concept, visual_locked, publish, release, or needs_rebrief');
  } else if (value.state !== 'needs_rebrief' && Object.hasOwn(MODE_MAX_STATE, value.mode)) {
    const maximum = POSTER_STATES.indexOf(MODE_MAX_STATE[value.mode]);
    if (POSTER_STATES.indexOf(value.state) > maximum) {
      issues.push(`mode ${value.mode} cannot reach state ${value.state}`);
    }
  }
  if (!Number.isInteger(value.conceptRevision) || value.conceptRevision < 0 || value.conceptRevision > 1) {
    issues.push('conceptRevision must be 0 or 1');
  }
  if (value.state === 'needs_rebrief' && value.conceptRevision !== 1) {
    issues.push('needs_rebrief requires conceptRevision 1 after the direction revision is exhausted');
  }
  if (value.direction !== null && (typeof value.direction !== 'string' || value.direction.trim() === '')) {
    issues.push('direction must be null or a non-empty string');
  }
  if (['concept', 'visual_locked', 'publish', 'release'].includes(value.state)
      && (typeof value.direction !== 'string' || value.direction.trim() === '')) {
    issues.push(`${value.state} state requires a selected direction`);
  }
  if (!Array.isArray(value.approvedCopy)
      || value.approvedCopy.some((entry) => typeof entry !== 'string' || entry.trim() === '')) {
    issues.push('approvedCopy must be an array of non-empty strings');
  } else if (value.state !== 'intake' && value.approvedCopy.length === 0) {
    issues.push('approvedCopy must contain at least one approved string after intake');
  }

  const provider = value.provider;
  if (!isObject(provider)) return [...issues, 'provider must be an object'];
  if (typeof provider.adapter !== 'string' || provider.adapter.trim() === '') issues.push('provider.adapter must be a non-empty string');
  if (typeof provider.external !== 'boolean') issues.push('provider.external must be boolean');
  if (typeof provider.billed !== 'boolean') issues.push('provider.billed must be boolean');
  for (const counter of ['authorizedCalls', 'usedCalls']) {
    if (!Number.isSafeInteger(provider[counter]) || provider[counter] < 0) {
      issues.push(`provider.${counter} must be a non-negative safe integer`);
    }
  }
  if (Number.isSafeInteger(provider.usedCalls) && Number.isSafeInteger(provider.authorizedCalls)
      && provider.usedCalls > provider.authorizedCalls) {
    issues.push('provider.usedCalls must not exceed authorizedCalls');
  }
  if ((provider.external === true || provider.billed === true)
      && (!Number.isInteger(provider.authorizedCalls) || provider.authorizedCalls < 1)) {
    issues.push('an external or billed provider requires at least one authorized call');
  }
  if (provider.adapter === 'deterministic-local' && (provider.external === true || provider.billed === true)) {
    issues.push('deterministic-local provider must not be external or billed');
  }
  return issues;
}

export function validatePublishQa(value, applicability = {}) {
  const issues = [];
  if (!isObject(value)) return ['publish QA must be a JSON object'];
  if (value.version !== 1) issues.push('version must be 1');
  if (!['PENDING', 'PASS', 'FAIL'].includes(value.status)) issues.push('status must be PENDING, PASS, or FAIL');
  for (const field of PUBLISH_QA_FIELDS) {
    if (!['PENDING', 'PASS', 'FAIL', 'NOT_APPLICABLE'].includes(value[field])) {
      issues.push(`${field} must be PENDING, PASS, FAIL, or NOT_APPLICABLE`);
    }
    const applicable = ALWAYS_APPLICABLE_PUBLISH_FIELDS.has(field) || applicability[field] === true;
    if (value[field] === 'NOT_APPLICABLE' && applicable) {
      issues.push(`${field} must be PASS because it is applicable`);
    } else if (value.status === 'PASS' && applicable && value[field] !== 'PASS') {
      issues.push(`${field} must be PASS because it is applicable`);
    } else if (value.status === 'PASS' && !applicable && !['PASS', 'NOT_APPLICABLE'].includes(value[field])) {
      issues.push(`${field} must be PASS or NOT_APPLICABLE when status is PASS`);
    }
  }
  if (value.status === 'FAIL' && !PUBLISH_QA_FIELDS.some((field) => value[field] === 'FAIL')) {
    issues.push('status FAIL requires at least one failed field');
  }
  return issues;
}

export function validateConfig(config) {
  const issues = [];
  if (!isObject(config)) return ['config must be a JSON object'];
  if (typeof config.title !== 'string' || config.title.trim() === '') issues.push('title must be a non-empty string');
  const duplicateStageFields = DUPLICATE_STAGE_FIELDS.filter((field) => Object.hasOwn(config, field));
  if (duplicateStageFields.length) {
    issues.push(`poster.json is the sole stage authority; remove ${duplicateStageFields.join(', ')} from poster.config.json`);
  }

  const canvas = config.canvas;
  if (!isObject(canvas)) return [...issues, 'canvas must be an object'];

  let widthPx;
  let heightPx;
  if (canvas.type === 'digital') {
    if (!isPositiveInteger(canvas.width) || !isPositiveInteger(canvas.height)) {
      issues.push('digital canvas width and height must be positive integers');
    } else {
      widthPx = canvas.width;
      heightPx = canvas.height;
    }
  } else if (canvas.type === 'long-form') {
    if (!isPositiveInteger(canvas.width) || !isPositiveInteger(canvas.minHeight)) {
      issues.push('long-form canvas width and minHeight must be positive integers');
    } else {
      widthPx = canvas.width;
      heightPx = canvas.minHeight;
    }
  } else if (canvas.type === 'print') {
    if (!isPositiveFinite(canvas.widthMm) || !isPositiveFinite(canvas.heightMm)) {
      issues.push('print canvas widthMm and heightMm must be positive finite numbers');
    } else if (canvas.widthMm > MAX_PRINT_DIMENSION_MM || canvas.heightMm > MAX_PRINT_DIMENSION_MM) {
      issues.push(`print canvas dimensions must not exceed ${MAX_PRINT_DIMENSION_MM} mm`);
    } else {
      widthPx = Math.round(canvas.widthMm * 96 / 25.4);
      heightPx = Math.round(canvas.heightMm * 96 / 25.4);
    }
  } else {
    issues.push(`unsupported canvas type: ${String(canvas.type)}`);
  }

  if (widthPx && heightPx) {
    if (widthPx > MAX_CANVAS_DIMENSION_PX || heightPx > MAX_CANVAS_DIMENSION_PX) {
      issues.push(`canvas dimensions must not exceed ${MAX_CANVAS_DIMENSION_PX} px per side`);
    }
    if (widthPx * heightPx > MAX_CANVAS_AREA_PX) {
      issues.push(`canvas area must not exceed ${MAX_CANVAS_AREA_PX} pixels`);
    }
  }

  if (config.outputs !== undefined && !isObject(config.outputs)) issues.push('outputs must be an object when provided');
  return issues;
}

export function validateMeasuredCanvas(width, height) {
  const issues = [];
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    return ['measured canvas dimensions must be positive finite numbers'];
  }
  if (width > MAX_CANVAS_DIMENSION_PX || height > MAX_CANVAS_DIMENSION_PX) {
    issues.push(`measured canvas dimensions must not exceed ${MAX_CANVAS_DIMENSION_PX} px per side`);
  }
  if (width * height > MAX_CANVAS_AREA_PX) {
    issues.push(`measured canvas area must not exceed ${MAX_CANVAS_AREA_PX} pixels`);
  }
  return issues;
}

export function validateBrief(brief) {
  const issues = [];
  if (!isObject(brief)) return ['brief must be a JSON object'];
  const duplicateStageFields = DUPLICATE_STAGE_FIELDS.filter((field) => Object.hasOwn(brief, field));
  if (duplicateStageFields.length) {
    issues.push(`poster.json is the sole stage authority; remove ${duplicateStageFields.join(', ')} from brief.json`);
  }

  function validateEntries(entries, kind) {
    if (entries === undefined) return;
    if (!Array.isArray(entries)) {
      issues.push(`${kind} must be an array`);
      return;
    }
    const keys = new Set();
    for (const [index, entry] of entries.entries()) {
      if (!isObject(entry)) {
        issues.push(`${kind}[${index}] must be an object`);
        continue;
      }
      if (typeof entry.key !== 'string' || entry.key.length === 0) issues.push(`${kind}[${index}].key must be a non-empty string`);
      else if (keys.has(entry.key)) issues.push(`${kind} contains duplicate key '${entry.key}'`);
      else keys.add(entry.key);
      if (typeof entry.critical !== 'boolean') issues.push(`${kind}[${index}].critical must be boolean`);
      const payloadKey = kind === 'facts' ? 'value' : 'destination';
      if (typeof entry[payloadKey] !== 'string' || entry[payloadKey].trim() === '') {
        issues.push(`${kind}[${index}].${payloadKey} must be a non-empty string`);
      }
    }
  }

  validateEntries(brief.facts, 'facts');
  validateEntries(brief.qrCodes, 'qrCodes');
  return issues;
}

export function validateStaticHtml(html) {
  const issues = [];
  const checks = [
    [/<script\b/i, 'script elements are not allowed'],
    [/\son[a-z]+\s*=/i, 'inline event handlers are not allowed'],
    [/(?:href|src)\s*=\s*["']?\s*javascript:/i, 'javascript: URLs are not allowed'],
    [/<(?:iframe|object|embed|base)\b/i, 'active or base-document elements are not allowed'],
  ];
  for (const [pattern, message] of checks) {
    if (pattern.test(html)) issues.push(message);
  }
  return issues;
}

function isInside(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

function fontFinding(code, message, evidence = {}) {
  return { code, message, evidence };
}

function binaryNamesMatchFamily(family, binaryNames) {
  const expected = family.replace(/[\s_-]+/g, '');
  return binaryNames.some((name) => {
    const normalized = name.replace(/[\s_-]+/g, '');
    if (normalized === expected) return true;
    return normalized.startsWith(expected) && FONT_STYLE_SUFFIX.test(normalized.slice(expected.length));
  });
}

function exactLicenseRecord(record, expected) {
  return isObject(record)
    && Object.keys(record).sort().join('\0') === [...LICENSE_RECORD_FIELDS].sort().join('\0')
    && LICENSE_RECORD_FIELDS.every((field) => record[field] === expected[field]);
}

function normalizeManifestPath(value, prefix) {
  if (typeof value !== 'string' || value.trim() === '' || value.includes('\\')) return null;
  const normalized = path.posix.normalize(value);
  if (normalized !== value || path.posix.isAbsolute(value) || normalized === '..' || normalized.startsWith('../')) return null;
  if (!normalized.startsWith(prefix) || normalized === prefix.slice(0, -1)) return null;
  return normalized;
}

function cssFontFaces(css) {
  const faces = [];
  const invalidSources = [];
  for (const match of css.matchAll(/@font-face\s*\{([\s\S]*?)\}/gi)) {
    const block = match[1];
    const familyMatch = block.match(/font-family\s*:\s*([^;]+);/i);
    const family = familyMatch?.[1]?.trim().replace(/^(?:"([\s\S]*)"|'([\s\S]*)')$/, '$1$2') ?? null;
    if (/\blocal\s*\(/i.test(block)) {
      invalidSources.push({ family, source: block.match(/src\s*:\s*([^;]+)/i)?.[1] ?? null });
    }
    for (const urlMatch of block.matchAll(/url\(\s*["']?([^"')]+)["']?\s*\)/gi)) {
      faces.push({ family, file: urlMatch[1], unicodeRange: block.match(/unicode-range\s*:\s*([^;]+);/i)?.[1]?.trim() ?? null });
    }
  }
  return { faces, invalidSources };
}

async function validateManifestFile(projectRealPath, relative, kind, missingCode, findings) {
  const sourcePath = path.join(projectRealPath, relative);
  try {
    const details = await lstat(sourcePath);
    if (details.isSymbolicLink() || !details.isFile()) {
      findings.push(fontFinding('FONT_PATH_INVALID', `${kind} must be a regular project file without symbolic links.`, { path: relative }));
      return null;
    }
    const resolved = await realpath(sourcePath);
    if (!isInside(projectRealPath, resolved)) {
      findings.push(fontFinding('FONT_PATH_INVALID', `${kind} must stay inside the project.`, { path: relative, resolved }));
      return null;
    }
    return sourcePath;
  } catch (error) {
    findings.push(fontFinding(missingCode, `${kind} is missing.`, { path: relative, error: error.code ?? error.message }));
    return null;
  }
}

export async function validateFontManifest(project, manifest) {
  const findings = [];
  if (!isObject(manifest)) return [fontFinding('FONT_MANIFEST_INVALID', 'Font manifest must be a JSON object.')];
  if (manifest.version !== 2) findings.push(fontFinding('FONT_MANIFEST_INVALID', 'Font manifest version must be 2.'));
  const fonts = Array.isArray(manifest.fonts) ? manifest.fonts : [];
  if (!Array.isArray(manifest.fonts)) {
    findings.push(fontFinding('FONT_MANIFEST_INVALID', 'Font manifest fonts must be an array.'));
  } else if (fonts.length === 0) {
    findings.push(fontFinding('FONT_LOAD_FAILED', 'Font manifest must declare at least one bundled font.'));
  }

  const projectRealPath = await realpath(project);
  let css = '';
  try {
    const styles = await readFile(path.join(projectRealPath, 'styles.css'), 'utf8');
    if (!/@import\s+url\(\s*["']font-faces\.css["']\s*\)\s*;/i.test(styles)) {
      findings.push(fontFinding('FONT_SOURCE_INVALID', 'styles.css must import the generated project-local font-faces.css.'));
    }
    css = await readFile(path.join(projectRealPath, 'font-faces.css'), 'utf8');
  } catch (error) {
    findings.push(fontFinding('SOURCE_MISSING', 'Font validation requires styles.css and font-faces.css.', { error: error.code ?? error.message }));
  }
  const { faces, invalidSources } = cssFontFaces(css);
  for (const source of invalidSources) {
    findings.push(fontFinding('FONT_SOURCE_INVALID', 'Bundled font declarations must not use local() sources.', source));
  }
  const declaredFiles = new Set();
  const families = new Set();
  const digestsByFamily = new Map();
  const actualFontDigests = new Map();
  const checkedLicenseFiles = new Map();

  for (const [index, font] of fonts.entries()) {
    if (!isObject(font)) {
      findings.push(fontFinding('FONT_MANIFEST_INVALID', 'Every font manifest entry must be an object.', { index }));
      continue;
    }
    const family = typeof font.family === 'string' ? font.family.trim() : '';
    if (!family) findings.push(fontFinding('FONT_MANIFEST_INVALID', 'Font family must be a non-empty string.', { index }));
    else families.add(family);
    if (!Array.isArray(font.samples) || font.samples.length === 0
        || font.samples.some((sample) => typeof sample !== 'string' || sample.trim() === '' || /\\u[0-9a-f]{4}/i.test(sample))) {
      findings.push(fontFinding('FONT_MANIFEST_INVALID', 'Font samples must contain explicit non-empty glyph strings.', { index, samples: font.samples ?? null }));
    }
    if (typeof font.unicodeRange !== 'string' || !/^U\+[0-9a-f?]+(?:-[0-9a-f]+)?(?:\s*,\s*U\+[0-9a-f?]+(?:-[0-9a-f]+)?)*$/i.test(font.unicodeRange)) {
      findings.push(fontFinding('FONT_MANIFEST_INVALID', 'Font unicodeRange must be an explicit CSS unicode-range declaration.', { index, unicodeRange: font.unicodeRange ?? null }));
    }

    const fontFile = normalizeManifestPath(font.file, 'assets/fonts/');
    if (!fontFile) {
      findings.push(fontFinding('FONT_PATH_INVALID', 'Font file path must be an exact normalized path under assets/fonts/.', { index, path: font.file ?? null }));
    } else {
      if (declaredFiles.has(fontFile)) {
        findings.push(fontFinding('FONT_MANIFEST_INVALID', 'Font file paths must be unique.', { index, path: fontFile }));
      }
      declaredFiles.add(fontFile);
      const sourcePath = await validateManifestFile(projectRealPath, fontFile, 'Declared font file', 'FONT_FILE_MISSING', findings);
      if (!/^[0-9a-f]{64}$/.test(font.sha256 ?? '')) {
        findings.push(fontFinding('FONT_MANIFEST_INVALID', 'Font SHA-256 must be a lowercase 64-character digest.', { index, path: fontFile, sha256: font.sha256 ?? null }));
      } else if (sourcePath) {
        const buffer = await readFile(sourcePath);
        const actual = createHash('sha256').update(buffer).digest('hex');
        actualFontDigests.set(fontFile, actual);
        if (actual !== font.sha256) {
          findings.push(fontFinding('FONT_HASH_MISMATCH', 'Font file SHA-256 does not match the manifest.', { path: fontFile, expected: font.sha256, actual }));
        }
        if (family) {
          const priorFamily = digestsByFamily.get(actual);
          if (priorFamily && priorFamily !== family) {
            findings.push(fontFinding('FONT_FAMILY_MISMATCH', 'One font file cannot substantiate multiple declared families.', { path: fontFile, family, conflictingFamily: priorFamily, sha256: actual }));
          } else {
            digestsByFamily.set(actual, family);
          }
        }
        try {
          const parsed = fontkit.create(buffer);
          const binaryNames = [parsed.familyName, parsed.fullName, parsed.postscriptName].filter(Boolean);
          const validFamilies = FONT_FAMILY_PREFIXES[family] ?? [];
          if (!validFamilies.some((validFamily) => binaryNamesMatchFamily(validFamily, binaryNames))) {
            findings.push(fontFinding('FONT_BINARY_FAMILY_MISMATCH', 'Font binary identity does not match the declared family.', {
              path: fontFile,
              declaredFamily: family,
              binaryNames,
            }));
          }
          const missingCodePoints = [...new Set((Array.isArray(font.samples) ? font.samples : [])
            .flatMap((sample) => [...sample])
            .filter((character) => character.trim() !== '')
            .map((character) => character.codePointAt(0))
            .filter((codePoint) => !parsed.hasGlyphForCodePoint(codePoint)))];
          if (missingCodePoints.length) {
            findings.push(fontFinding('FONT_GLYPH_MISSING', 'Font binary does not cover every declared glyph sample.', {
              path: fontFile,
              family,
              missingCodePoints,
            }));
          }
        } catch (error) {
          findings.push(fontFinding('FONT_BINARY_INVALID', 'Font binary could not be parsed.', { path: fontFile, error: error.message }));
        }
      }
      const matchingFaces = faces.filter((face) => face.file === fontFile);
      if (!matchingFaces.some((face) => face.family === family && face.unicodeRange === font.unicodeRange)) {
        findings.push(fontFinding('UNDECLARED_FONT', 'Manifest font is not bound to the same family, file, and unicode range in font-faces.css.', {
          path: fontFile,
          family,
          unicodeRange: font.unicodeRange ?? null,
          cssFaces: matchingFaces,
        }));
      }
    }

    const licenseFile = normalizeManifestPath(font.licenseFile, 'assets/licenses/');
    const licensePolicy = FONT_LICENSE_POLICY[family];
    if (!licenseFile) {
      findings.push(fontFinding('FONT_PATH_INVALID', 'Font license path must be an exact normalized path under assets/licenses/.', { index, path: font.licenseFile ?? null }));
    } else {
      if (!licensePolicy || licenseFile !== licensePolicy.licenseFile) {
        findings.push(fontFinding('FONT_LICENSE_BINDING_MISMATCH', 'Font license path is not allowed by the validator-owned family policy.', {
          family,
          actual: licenseFile,
          expected: licensePolicy?.licenseFile ?? null,
        }));
      }
      const licensePath = await validateManifestFile(projectRealPath, licenseFile, 'Declared font license file', 'FONT_LICENSE_MISSING', findings);
      if (licensePath && licensePolicy && !checkedLicenseFiles.has(licenseFile)) {
        const actualLicenseSha256 = createHash('sha256').update(await readFile(licensePath)).digest('hex');
        checkedLicenseFiles.set(licenseFile, actualLicenseSha256);
        if (actualLicenseSha256 !== licensePolicy.licenseSha256) {
          findings.push(fontFinding('FONT_LICENSE_BINDING_MISMATCH', 'Font license content does not match the validator-owned pinned license hash.', {
            family,
            path: licenseFile,
            actual: actualLicenseSha256,
            expected: licensePolicy.licenseSha256,
          }));
        }
      }
    }
  }

  for (const family of REQUIRED_FONT_FAMILIES) {
    if (!families.has(family)) findings.push(fontFinding('UNDECLARED_FONT', 'Required bundled font family is absent from the manifest.', { family }));
  }
  for (const face of faces) {
    if (!declaredFiles.has(face.file)) {
      findings.push(fontFinding('UNDECLARED_FONT', 'A CSS font URL is not declared by the font manifest.', face));
    }
  }

  try {
    const installedManifest = JSON.parse(await readFile(path.join(projectRealPath, 'assets/fonts/font-manifest.json'), 'utf8'));
    if (JSON.stringify(installedManifest) !== JSON.stringify(manifest)) {
      findings.push(fontFinding('FONT_MANIFEST_MISMATCH', 'Root and installed font manifests must match exactly.'));
    }
  } catch (error) {
    findings.push(fontFinding('FONT_MANIFEST_INVALID', 'Installed font manifest is missing or invalid.', { error: error.code ?? error.message }));
  }

  let licenseManifest;
  try {
    licenseManifest = JSON.parse(await readFile(path.join(projectRealPath, 'font-license-manifest.json'), 'utf8'));
    const installed = JSON.parse(await readFile(path.join(projectRealPath, 'assets/licenses/font-license-manifest.json'), 'utf8'));
    if (JSON.stringify(installed) !== JSON.stringify(licenseManifest)) {
      findings.push(fontFinding('FONT_LICENSE_BINDING_MISMATCH', 'Root and installed font license manifests must match exactly.'));
    }
  } catch (error) {
    findings.push(fontFinding('FONT_LICENSE_MISSING', 'Font license manifest is missing or invalid.', { error: error.code ?? error.message }));
  }
  if (licenseManifest) {
    const records = Array.isArray(licenseManifest.records) ? licenseManifest.records : [];
    if (licenseManifest.version !== 1 || records.length !== fonts.length) {
      findings.push(fontFinding('FONT_LICENSE_BINDING_MISMATCH', 'Font license manifest shape or record count is invalid.'));
    }
    for (const font of fonts.filter(isObject)) {
      const policy = FONT_LICENSE_POLICY[font.family];
      const expected = {
        family: font.family,
        file: font.file,
        sha256: actualFontDigests.get(font.file) ?? font.sha256,
        licenseFile: policy?.licenseFile ?? null,
        licenseSha256: policy?.licenseSha256 ?? null,
        licenseId: 'OFL-1.1',
        licenseName: 'SIL Open Font License',
        licenseVersion: '1.1',
        sourcePackage: policy?.sourcePackage ?? null,
      };
      const exactMatches = records.filter((record) => exactLicenseRecord(record, expected));
      if (exactMatches.length !== 1) {
        findings.push(fontFinding('FONT_LICENSE_BINDING_MISMATCH', 'Font entry must have one exact structured license record.', { expected, matches: exactMatches.length }));
      }
    }
  }
  await validateManifestFile(projectRealPath, 'licenses.md', 'Font license narrative', 'FONT_LICENSE_MISSING', findings);
  return findings;
}

function assetFinding(code, message, evidence = {}) {
  return { code, message, evidence };
}

async function collectNonFontAssets(projectRealPath) {
  const assets = [];
  async function walk(relativeDirectory) {
    const directory = path.join(projectRealPath, relativeDirectory);
    let entries;
    try {
      entries = await readdir(directory, { withFileTypes: true });
    } catch (error) {
      if (error.code === 'ENOENT') return;
      throw error;
    }
    for (const entry of entries) {
      const relative = path.join(relativeDirectory, entry.name);
      const normalized = relative.split(path.sep).join('/');
      if (relativeDirectory === 'assets' && ['fonts', 'licenses'].includes(entry.name)) continue;
      const details = await lstat(path.join(projectRealPath, relative));
      if (details.isSymbolicLink()) {
        throw new Error(`Asset path must not use symbolic links: ${normalized}`);
      }
      if (details.isDirectory()) await walk(relative);
      else if (details.isFile()) assets.push(normalized);
      else throw new Error(`Asset path must be a regular file or directory: ${normalized}`);
    }
  }
  await walk('assets');
  return assets.sort();
}

export async function validateAssetManifest(project, manifest) {
  const findings = [];
  if (!isObject(manifest) || manifest.version !== 1 || !Array.isArray(manifest.assets)) {
    return [assetFinding('ASSET_LICENSE_INVALID', 'Asset manifest must be a version 1 object with an assets array.')];
  }
  const projectRealPath = await realpath(project);
  let actualAssets = [];
  try {
    actualAssets = await collectNonFontAssets(projectRealPath);
  } catch (error) {
    findings.push(assetFinding('ASSET_LICENSE_INVALID', 'Non-font project assets could not be enumerated safely.', { error: error.message }));
  }
  const actualSet = new Set(actualAssets);
  const declared = new Map();
  for (const [index, record] of manifest.assets.entries()) {
    if (!isObject(record)
        || Object.keys(record).sort().join('\0') !== [...ASSET_RECORD_FIELDS].sort().join('\0')) {
      findings.push(assetFinding('ASSET_LICENSE_INVALID', 'Every asset record must contain exactly path, sha256, source, creator, license, authorization, and attribution.', { index }));
      continue;
    }
    const assetPath = normalizeManifestPath(record.path, 'assets/');
    if (!assetPath || assetPath.startsWith('assets/fonts/') || assetPath.startsWith('assets/licenses/')) {
      findings.push(assetFinding('ASSET_LICENSE_INVALID', 'Asset path must be a normalized non-font path under assets/.', { index, path: record.path }));
      continue;
    }
    if (declared.has(assetPath)) {
      findings.push(assetFinding('ASSET_LICENSE_INVALID', 'Asset paths must be unique.', { index, path: assetPath }));
      continue;
    }
    declared.set(assetPath, record);
    for (const field of ['source', 'creator', 'license', 'authorization', 'attribution']) {
      if (typeof record[field] !== 'string' || record[field].trim() === '') {
        findings.push(assetFinding('ASSET_LICENSE_INVALID', `Asset ${field} must be a non-empty string.`, { index, path: assetPath, field }));
      }
    }
    if (!/^[0-9a-f]{64}$/.test(record.sha256)) {
      findings.push(assetFinding('ASSET_LICENSE_INVALID', 'Asset sha256 must be a lowercase 64-character digest.', { index, path: assetPath }));
      continue;
    }
    if (!actualSet.has(assetPath)) {
      findings.push(assetFinding('ASSET_LICENSE_INVALID', 'Asset manifest references a missing non-font asset.', { index, path: assetPath }));
      continue;
    }
    const sourcePath = path.join(projectRealPath, assetPath);
    const resolved = await realpath(sourcePath);
    if (!isInside(projectRealPath, resolved)) {
      findings.push(assetFinding('ASSET_LICENSE_INVALID', 'Asset path resolves outside the project.', { index, path: assetPath, resolved }));
      continue;
    }
    const actual = await sha256(sourcePath);
    if (actual !== record.sha256) {
      findings.push(assetFinding('ASSET_HASH_MISMATCH', 'Asset SHA-256 does not match asset-manifest.json.', { path: assetPath, expected: record.sha256, actual }));
    }
  }
  for (const assetPath of actualAssets) {
    if (!declared.has(assetPath)) {
      findings.push(assetFinding('ASSET_LICENSE_MISSING', 'Every non-font Release asset requires one structured license and authorization record.', { path: assetPath }));
    }
  }
  return findings;
}

function selectedFontFamily(value) {
  return String(value ?? '').split(',')[0].trim().replace(/^['"]|['"]$/g, '');
}

function glyphBearingCodePoints(text) {
  return [...text].map((character) => character.codePointAt(0)).filter((codePoint) => {
    const character = String.fromCodePoint(codePoint);
    return character.trim() !== '' && ![0x200c, 0x200d, 0xfe0e, 0xfe0f].includes(codePoint);
  });
}

export async function validateRenderedGlyphCoverage(project, manifest, textRuns) {
  if (!isObject(manifest) || !Array.isArray(manifest.fonts)) {
    return [fontFinding('FONT_MANIFEST_INVALID', 'Rendered glyph validation requires a valid font manifest.')];
  }
  const projectRealPath = await realpath(project);
  const coverage = new Map();
  for (const font of manifest.fonts.filter(isObject)) {
    if (typeof font.family !== 'string' || typeof font.file !== 'string') continue;
    const fontFile = normalizeManifestPath(font.file, 'assets/fonts/');
    if (!fontFile) continue;
    try {
      const parsed = fontkit.create(await readFile(path.join(projectRealPath, fontFile)));
      const familyCoverage = coverage.get(font.family) ?? new Set();
      for (const codePoint of parsed.characterSet) familyCoverage.add(codePoint);
      coverage.set(font.family, familyCoverage);
    } catch {
      // Static font validation owns malformed binary reporting.
    }
  }
  const findings = [];
  for (const [index, run] of (Array.isArray(textRuns) ? textRuns : []).entries()) {
    if (!isObject(run) || typeof run.text !== 'string' || run.text.trim() === '') continue;
    const family = selectedFontFamily(run.fontFamily);
    const familyCoverage = coverage.get(family);
    if (!familyCoverage) {
      findings.push(fontFinding('UNDECLARED_FONT', 'Visible poster text selects a family absent from the bundled font manifest.', { index, family, text: run.text.slice(0, 160) }));
      continue;
    }
    const missingCodePoints = [...new Set(glyphBearingCodePoints(run.text).filter((codePoint) => !familyCoverage.has(codePoint)))];
    if (missingCodePoints.length) {
      findings.push(fontFinding('FONT_POSTER_GLYPH_MISSING', 'The selected bundled font family does not cover every actual visible poster character.', {
        index,
        family,
        text: run.text.slice(0, 160),
        missingCodePoints,
      }));
    }
  }
  return findings;
}

export async function derivePublishQaApplicability(project, brief, dom = {}) {
  const assetPaths = [];
  async function walk(relativeDirectory) {
    const directory = path.join(project, relativeDirectory);
    let entries;
    try {
      entries = await readdir(directory, { withFileTypes: true });
    } catch (error) {
      if (error.code === 'ENOENT' || error.code === 'ENOTDIR') return;
      throw error;
    }
    for (const entry of entries) {
      const relative = path.join(relativeDirectory, entry.name);
      if (entry.isDirectory()) await walk(relative);
      else if (entry.isFile()) assetPaths.push(relative.split(path.sep).join('/'));
    }
  }
  await walk('assets');
  const roles = new Set((Array.isArray(brief?.assets) ? brief.assets : [])
    .map((asset) => typeof asset?.role === 'string' ? asset.role.toLowerCase() : ''));
  const hasAsset = (pattern) => assetPaths.some((assetPath) => pattern.test(assetPath));
  return {
    size: true,
    facts: true,
    mobile: true,
    artifacts: true,
    identity: Number(dom.identityCount) > 0 || roles.has('identity') || roles.has('person') || hasAsset(/\/(?:identity|identities|people|portraits?)(?:\/|[._-])/i),
    logo: Number(dom.logoCount) > 0 || roles.has('logo') || roles.has('brand') || hasAsset(/\/(?:logos?|brandmarks?|marks?)(?:\/|[._-])/i),
    qr: Number(dom.qrCount) > 0 || (Array.isArray(brief?.qrCodes) && brief.qrCodes.length > 0) || roles.has('qr') || hasAsset(/\/(?:qr|qrcodes?)(?:\/|[._-])/i),
  };
}

export async function installProjectResourceBoundary(context, project) {
  const projectRealPath = await realpath(project);
  const blocked = [];
  await context.route('**/*', async (route) => {
    const url = route.request().url();
    if (/^(?:https?|wss?):/i.test(url)) {
      blocked.push({ code: 'EXTERNAL_RESOURCE_BLOCKED', url });
      await route.abort('blockedbyclient');
      return;
    }
    if (/^file:/i.test(url)) {
      const lexicalPath = path.resolve(fileURLToPath(url));
      let resolvedPath = lexicalPath;
      try {
        resolvedPath = await realpath(lexicalPath);
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
      }
      if (!isInside(projectRealPath, resolvedPath)) {
        blocked.push({ code: 'ASSET_OUTSIDE_PROJECT', url, resolvedPath });
        await route.abort('blockedbyclient');
        return;
      }
    }
    await route.continue();
  });
  return blocked;
}

async function sha256(filePath) {
  return createHash('sha256').update(await readFile(filePath)).digest('hex');
}

export async function collectProjectSourceHashes(project) {
  const files = [
    'asset-manifest.json',
    'brief.json',
    'font-faces.css',
    'font-license-manifest.json',
    'font-manifest.json',
    'licenses.md',
    'poster.config.json',
    'poster.html',
    'poster.json',
    'publish-qa.json',
    'styles.css',
  ];
  async function walk(relativeDirectory) {
    const directory = path.join(project, relativeDirectory);
    let entries;
    try {
      entries = await readdir(directory, { withFileTypes: true });
    } catch (error) {
      if (error.code === 'ENOENT') return;
      throw error;
    }
    for (const entry of entries) {
      const relative = path.join(relativeDirectory, entry.name);
      const details = await lstat(path.join(project, relative));
      if (details.isSymbolicLink()) throw new Error(`Project sources must not use symbolic links: ${relative}`);
      if (details.isDirectory()) await walk(relative);
      else if (details.isFile()) files.push(relative);
    }
  }
  await walk('assets');
  files.sort();
  return Object.fromEntries(await Promise.all(files.map(async (relative) => {
    const sourcePath = path.join(project, relative);
    const details = await lstat(sourcePath);
    if (details.isSymbolicLink() || !details.isFile()) throw new Error(`Project source must be a regular file without symbolic links: ${relative}`);
    return [relative.split(path.sep).join('/'), await sha256(sourcePath)];
  })));
}
