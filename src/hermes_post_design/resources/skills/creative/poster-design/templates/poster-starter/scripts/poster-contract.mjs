import { createHash } from 'node:crypto';
import { lstat, readFile, readdir, realpath } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const MAX_CANVAS_DIMENSION_PX = 20_000;
const MAX_CANVAS_AREA_PX = 100_000_000;
const MAX_PRINT_DIMENSION_MM = 2_000;

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