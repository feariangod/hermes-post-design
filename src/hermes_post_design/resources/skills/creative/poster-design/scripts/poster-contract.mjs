import { createHash } from 'node:crypto';
import { lstat, readFile, readdir, realpath } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const MAX_CANVAS_DIMENSION_PX = 20_000;
const MAX_CANVAS_AREA_PX = 100_000_000;
const MAX_PRINT_DIMENSION_MM = 2_000;
const POSTER_STATES = ['intake', 'route_selected', 'concept', 'visual_locked', 'publish', 'release'];
const MODE_MAX_STATE = { concept: 'visual_locked', publish: 'publish', release: 'release' };
const PUBLISH_QA_FIELDS = ['size', 'facts', 'identity', 'logo', 'qr', 'mobile', 'artifacts'];
const REQUIRED_FONT_FAMILIES = new Set(['Noto Sans SC', 'Noto Serif SC', 'Ma Shan Zheng']);

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
  }

  const provider = value.provider;
  if (!isObject(provider)) return [...issues, 'provider must be an object'];
  if (typeof provider.adapter !== 'string' || provider.adapter.trim() === '') issues.push('provider.adapter must be a non-empty string');
  if (typeof provider.external !== 'boolean') issues.push('provider.external must be boolean');
  if (typeof provider.billed !== 'boolean') issues.push('provider.billed must be boolean');
  for (const counter of ['authorizedCalls', 'usedCalls']) {
    if (!Number.isInteger(provider[counter]) || provider[counter] < 0) {
      issues.push(`provider.${counter} must be a non-negative integer`);
    }
  }
  if (Number.isInteger(provider.usedCalls) && Number.isInteger(provider.authorizedCalls)
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

export function validatePublishQa(value) {
  const issues = [];
  if (!isObject(value)) return ['publish QA must be a JSON object'];
  if (value.version !== 1) issues.push('version must be 1');
  if (!['PENDING', 'PASS', 'FAIL'].includes(value.status)) issues.push('status must be PENDING, PASS, or FAIL');
  for (const field of PUBLISH_QA_FIELDS) {
    if (!['PENDING', 'PASS', 'FAIL', 'NOT_APPLICABLE'].includes(value[field])) {
      issues.push(`${field} must be PENDING, PASS, FAIL, or NOT_APPLICABLE`);
    }
    if (value.status === 'PASS' && !['PASS', 'NOT_APPLICABLE'].includes(value[field])) {
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
  if (!['preview', 'final'].includes(config.status)) {
    issues.push('status must be preview or final');
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
  if (!['preview', 'final'].includes(brief.status)) issues.push('status must be preview or final');

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

function normalizeManifestPath(value, prefix) {
  if (typeof value !== 'string' || value.trim() === '' || value.includes('\\')) return null;
  const normalized = path.posix.normalize(value);
  if (normalized !== value || path.posix.isAbsolute(value) || normalized === '..' || normalized.startsWith('../')) return null;
  if (!normalized.startsWith(prefix) || normalized === prefix.slice(0, -1)) return null;
  return normalized;
}

function cssFontFaces(css) {
  const faces = [];
  for (const match of css.matchAll(/@font-face\s*\{([\s\S]*?)\}/gi)) {
    const block = match[1];
    const familyMatch = block.match(/font-family\s*:\s*([^;]+);/i);
    const family = familyMatch?.[1]?.trim().replace(/^(?:"([\s\S]*)"|'([\s\S]*)')$/, '$1$2') ?? null;
    for (const urlMatch of block.matchAll(/url\(\s*["']?([^"')]+)["']?\s*\)/gi)) {
      faces.push({ family, file: urlMatch[1] });
    }
  }
  return faces;
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
  if (manifest.version !== 1) findings.push(fontFinding('FONT_MANIFEST_INVALID', 'Font manifest version must be 1.'));
  const fonts = Array.isArray(manifest.fonts) ? manifest.fonts : [];
  if (!Array.isArray(manifest.fonts)) {
    findings.push(fontFinding('FONT_MANIFEST_INVALID', 'Font manifest fonts must be an array.'));
  } else if (fonts.length === 0) {
    findings.push(fontFinding('FONT_LOAD_FAILED', 'Font manifest must declare at least one bundled font.'));
  }

  const projectRealPath = await realpath(project);
  let css = '';
  try {
    css = await readFile(path.join(projectRealPath, 'styles.css'), 'utf8');
  } catch (error) {
    findings.push(fontFinding('SOURCE_MISSING', 'Font validation requires styles.css.', { error: error.code ?? error.message }));
  }
  const faces = cssFontFaces(css);
  const declaredFiles = new Set();
  const families = new Set();
  const digestsByFamily = new Map();

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
        const actual = await sha256(sourcePath);
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
      }
      const matchingFaces = faces.filter((face) => face.file === fontFile);
      if (!matchingFaces.some((face) => face.family === family)) {
        findings.push(fontFinding('UNDECLARED_FONT', 'Manifest font is not bound to the same family and file in styles.css.', { path: fontFile, family, cssFamilies: matchingFaces.map((face) => face.family) }));
      }
    }

    const licenseFile = normalizeManifestPath(font.licenseFile, 'assets/licenses/');
    if (!licenseFile) {
      findings.push(fontFinding('FONT_PATH_INVALID', 'Font license path must be an exact normalized path under assets/licenses/.', { index, path: font.licenseFile ?? null }));
    } else {
      await validateManifestFile(projectRealPath, licenseFile, 'Declared font license file', 'FONT_LICENSE_MISSING', findings);
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

  try {
    const licenses = await readFile(path.join(projectRealPath, 'licenses.md'), 'utf8');
    for (const font of fonts.filter(isObject)) {
      const missing = [font.family, font.file, font.sha256, font.licenseFile]
        .filter((value) => typeof value === 'string' && !licenses.includes(value));
      if (missing.length) {
        findings.push(fontFinding('FONT_LICENSE_DECLARATION_MISSING', 'licenses.md is not bound to the current font declaration.', { path: font.file ?? null, missing }));
      }
    }
  } catch (error) {
    findings.push(fontFinding('FONT_LICENSE_MISSING', 'Font license narrative is missing.', { path: 'licenses.md', error: error.code ?? error.message }));
  }
  return findings;
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
  const files = ['brief.json', 'poster.config.json', 'poster.html', 'styles.css'];
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
