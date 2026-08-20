import { createHash, randomUUID } from 'node:crypto';
import { readFile, rename, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';

const checkNames = ['hierarchy', 'composition', 'typography', 'coherence', 'artifacts', 'mobile'];

function parseArgs(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith('--') || value === undefined) throw new Error(`Invalid argument near ${key ?? '<end>'}`);
    values[key.slice(2)] = value;
  }
  return values;
}

async function sha256(filePath) {
  return createHash('sha256').update(await readFile(filePath)).digest('hex');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.project || !args.reviewer) throw new Error('--project and --reviewer are required');
  const checks = Object.fromEntries(checkNames.map((name) => [name, args[name]]));
  const invalid = checkNames.filter((name) => checks[name] !== 'PASS');
  if (invalid.length) throw new Error(`Every visual check must be PASS: ${invalid.join(', ')}`);

  const project = path.resolve(args.project);
  const config = JSON.parse(await readFile(path.join(project, 'poster.config.json'), 'utf8'));
  const pngFile = config.outputs?.png ?? 'poster.png';
  const mobileFile = config.outputs?.mobile ?? 'poster-mobile.png';
  if (pngFile !== path.basename(pngFile) || mobileFile !== path.basename(mobileFile)) {
    throw new Error('Visual review outputs must be direct files in the project directory.');
  }

  const report = {
    version: 1,
    reviewedAt: new Date().toISOString(),
    reviewer: args.reviewer,
    status: 'PASS',
    outputs: {
      png: { file: pngFile, sha256: await sha256(path.join(project, pngFile)) },
      mobile: { file: mobileFile, sha256: await sha256(path.join(project, mobileFile)) },
    },
    checks,
    notes: args.notes ?? '',
  };

  const outputPath = path.join(project, 'visual-review.json');
  const temporaryPath = path.join(project, `.visual-review.${randomUUID()}.tmp.json`);
  try {
    await writeFile(temporaryPath, `${JSON.stringify(report, null, 2)}\n`);
    await rm(outputPath, { force: true });
    await rename(temporaryPath, outputPath);
  } finally {
    await rm(temporaryPath, { force: true });
  }
  process.stdout.write(`${JSON.stringify({ success: true, output: outputPath })}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});