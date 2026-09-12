#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const PNG_1X1 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAF/gL+Avz4WQAAAABJRU5ErkJggg==',
  'base64',
);

function parseArgs(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith('--') || value === undefined) throw new Error('invalid fake adapter arguments');
    values[key.slice(2)] = value;
  }
  return values;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const authorizedCalls = Number(args['authorized-calls']);
  if (!Number.isSafeInteger(authorizedCalls) || authorizedCalls < 1) {
    throw new Error('fake adapter requires one authorized call');
  }
  if (!process.env.FAKE_IMAGE_ADAPTER_CREDENTIAL) {
    throw new Error('fake adapter credential is missing');
  }
  if (args.fail === 'true') throw new Error('fake adapter failed after authorization');
  if (!args.output) throw new Error('fake adapter output is required');

  const artifact = path.resolve(args.output);
  await mkdir(path.dirname(artifact), { recursive: true });
  await writeFile(artifact, PNG_1X1);
  process.stdout.write(`${JSON.stringify({
    success: true,
    provider: {
      adapter: 'fake-image-adapter',
      external: true,
      billed: true,
      authorizedCalls,
      usedCalls: 1,
    },
    artifact: {
      path: artifact,
      sha256: createHash('sha256').update(PNG_1X1).digest('hex'),
    },
  })}\n`);
}

main().catch(() => {
  process.stderr.write(`${JSON.stringify({
    success: false,
    error: { type: 'adapter_error', message: 'Fake image adapter failed' },
  })}\n`);
  process.exitCode = 1;
});
