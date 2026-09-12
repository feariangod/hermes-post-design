import { access as filesystemAccess } from 'node:fs/promises';
import path from 'node:path';

function unique(paths) {
  return [...new Set(paths.filter(Boolean))];
}

function windowsPaths(environment, segments) {
  const roots = unique([
    environment.ProgramFiles,
    environment.PROGRAMFILES,
    'C:\\Program Files',
    environment['ProgramFiles(x86)'],
    environment.PROGRAMFILES_X86,
    'C:\\Program Files (x86)',
    environment.LOCALAPPDATA,
  ]);
  return roots.map((root) => path.win32.join(root, ...segments));
}

export function browserCandidates(platform = process.platform, environment = process.env) {
  if (platform === 'darwin') {
    return {
      chrome: ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'],
      edge: ['/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'],
    };
  }
  if (platform === 'linux') {
    return {
      chrome: ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser'],
      edge: ['/usr/bin/microsoft-edge', '/usr/bin/microsoft-edge-stable'],
    };
  }
  if (platform === 'win32') {
    return {
      chrome: windowsPaths(environment, ['Google', 'Chrome', 'Application', 'chrome.exe']),
      edge: windowsPaths(environment, ['Microsoft', 'Edge', 'Application', 'msedge.exe']),
    };
  }
  return { chrome: [], edge: [] };
}

async function firstExisting(candidates, access) {
  for (const candidate of candidates) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      // Try the next normal browser installation location.
    }
  }
  return null;
}

export async function resolveExecutable(choice, options = {}) {
  const platform = options.platform ?? process.platform;
  const environment = options.env ?? process.env;
  const access = options.access ?? filesystemAccess;
  const pathApi = platform === 'win32' ? path.win32 : path;

  if (choice && !['chrome', 'edge'].includes(choice)) {
    const executable = pathApi.resolve(options.cwd ?? process.cwd(), choice);
    await access(executable);
    return executable;
  }

  const candidates = browserCandidates(platform, environment);
  const preferred = choice === 'edge'
    ? [...candidates.edge, ...candidates.chrome]
    : [...candidates.chrome, ...candidates.edge];
  return firstExisting(preferred, access);
}
