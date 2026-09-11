import assert from 'node:assert/strict';
import test from 'node:test';

import { browserCandidates, resolveExecutable } from '../../src/hermes_post_design/resources/skills/creative/poster-design/scripts/browser-paths.mjs';

test('browserCandidates includes normal Chrome and Edge locations on macOS and Linux', () => {
  const macos = browserCandidates('darwin', {});
  assert.ok(macos.chrome.includes('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'));
  assert.ok(macos.edge.includes('/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'));

  const linux = browserCandidates('linux', {});
  assert.ok(linux.chrome.includes('/usr/bin/google-chrome'));
  assert.ok(linux.chrome.includes('/usr/bin/google-chrome-stable'));
  assert.ok(linux.chrome.includes('/usr/bin/chromium'));
  assert.ok(linux.chrome.includes('/usr/bin/chromium-browser'));
});

test('browserCandidates uses injected Program Files and LOCALAPPDATA on Windows', () => {
  const windows = browserCandidates('win32', {
    ProgramFiles: 'D:\\Program Files',
    'ProgramFiles(x86)': 'D:\\Program Files (x86)',
    LOCALAPPDATA: 'D:\\Users\\poster\\AppData\\Local',
  });

  assert.ok(windows.chrome.includes('D:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'));
  assert.ok(windows.chrome.includes('D:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'));
  assert.ok(windows.chrome.includes('D:\\Users\\poster\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe'));
  assert.ok(windows.edge.includes('D:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe'));
  assert.ok(windows.edge.includes('D:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'));
  assert.ok(windows.edge.includes('D:\\Users\\poster\\AppData\\Local\\Microsoft\\Edge\\Application\\msedge.exe'));
});

test('resolveExecutable prefers the requested browser through an injected access check', async () => {
  const checked = [];
  const executable = await resolveExecutable('edge', {
    platform: 'darwin',
    env: {},
    access: async (candidate) => {
      checked.push(candidate);
      if (candidate !== '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge') {
        throw Object.assign(new Error('not found'), { code: 'ENOENT' });
      }
    },
  });

  assert.equal(executable, '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge');
  assert.deepEqual(checked, ['/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge']);
});
