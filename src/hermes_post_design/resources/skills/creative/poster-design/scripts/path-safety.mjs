import { lstat, mkdir, realpath, rename } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import path from 'node:path';

function isInside(root, candidate, platform = process.platform) {
  const normalize = (value) => platform === 'win32' ? path.resolve(value).toLowerCase() : path.resolve(value);
  const normalizedRoot = normalize(root);
  const normalizedCandidate = normalize(candidate);
  const relative = path.relative(normalizedRoot, normalizedCandidate);
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

function redirected(stats) {
  return stats.isSymbolicLink();
}

export async function resolveProjectRoot(project, options = {}) {
  const fs = options.fs ?? { lstat, realpath };
  const lexical = path.resolve(project);
  const stats = await fs.lstat(lexical);
  if (redirected(stats) || !stats.isDirectory()) {
    throw new Error(`Project root must be a real directory without redirects: ${lexical}`);
  }
  return fs.realpath(lexical);
}

export async function assertSafeDestinationPath(projectRoot, destination, options = {}) {
  const fs = options.fs ?? { lstat, realpath };
  const platform = options.platform ?? process.platform;
  const root = path.resolve(projectRoot);
  const target = path.resolve(destination);
  if (!isInside(root, target, platform)) {
    throw new Error(`Destination must stay inside the resolved project: ${target}`);
  }

  const relative = path.relative(root, target);
  const components = [root];
  let current = root;
  for (const part of relative.split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    components.push(current);
  }

  const rootReal = await fs.realpath(root);
  for (const [index, component] of components.entries()) {
    let stats;
    try {
      stats = await fs.lstat(component);
    } catch (error) {
      if (error.code === 'ENOENT') break;
      throw error;
    }
    if (redirected(stats)) {
      throw new Error(`Destination uses a symlink or reparse-point redirect: ${component}`);
    }
    const componentReal = await fs.realpath(component);
    if (!isInside(rootReal, componentReal, platform)) {
      throw new Error(`Destination component redirects outside the project: ${component}`);
    }
    const expected = platform === 'win32' ? path.resolve(component).toLowerCase() : path.resolve(component);
    const actual = platform === 'win32' ? path.resolve(componentReal).toLowerCase() : path.resolve(componentReal);
    if (expected !== actual) {
      throw new Error(`Destination component is a reparse-like redirect: ${component}`);
    }
    const isLeaf = index === components.length - 1;
    if (!isLeaf && !stats.isDirectory()) {
      throw new Error(`Destination parent is not a directory: ${component}`);
    }
  }
  return target;
}

export async function ensureSafeDirectory(projectRoot, directory, options = {}) {
  const fs = options.fs ?? { lstat, mkdir, realpath };
  const root = path.resolve(projectRoot);
  const target = await assertSafeDestinationPath(root, directory, options);
  const relative = path.relative(root, target);
  let current = root;
  for (const part of relative.split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    try {
      const stats = await fs.lstat(current);
      if (redirected(stats) || !stats.isDirectory()) {
        throw new Error(`Destination directory is redirected or invalid: ${current}`);
      }
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
      await fs.mkdir(current);
    }
    await assertSafeDestinationPath(root, current, options);
  }
  return target;
}

export async function publishProjectFile(projectRoot, destination, writer, options = {}) {
  const fs = options.fs ?? { lstat, mkdir, realpath, rename };
  const makeUuid = options.randomUUID ?? randomUUID;
  const fsOptions = { ...options, fs };
  const root = path.resolve(projectRoot);
  const target = await assertSafeDestinationPath(root, destination, fsOptions);
  await ensureSafeDirectory(root, path.dirname(target), fsOptions);
  await assertSafeDestinationPath(root, target, fsOptions);
  try {
    const existing = await fs.lstat(target);
    if (redirected(existing) || !existing.isFile()) {
      throw new Error(`Destination file is redirected or invalid: ${target}`);
    }
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }

  const temporary = path.join(path.dirname(target), `.${path.basename(target)}.${makeUuid()}.tmp`);
  await assertSafeDestinationPath(root, temporary, fsOptions);
  await writer(temporary);
  const temporaryStats = await fs.lstat(temporary);
  if (redirected(temporaryStats) || !temporaryStats.isFile()) {
    throw new Error(`Prepared output is not a regular in-project file: ${temporary}`);
  }
  const temporaryReal = await fs.realpath(temporary);
  if (!isInside(root, temporaryReal)) {
    throw new Error(`Prepared output escaped the project: ${temporary}`);
  }
  await assertSafeDestinationPath(root, path.dirname(target), fsOptions);
  await assertSafeDestinationPath(root, target, fsOptions);
  await fs.rename(temporary, target);
  return target;
}
