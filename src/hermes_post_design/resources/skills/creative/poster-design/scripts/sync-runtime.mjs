import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(scriptDir, '..');
const runtimeNames = ['browser-paths.mjs', 'poster-contract.mjs', 'prepare-project.mjs', 'render-poster.mjs', 'inspect-poster.mjs', 'record-visual-review.mjs'];
const targetDirectories = [
  path.join(root, 'templates', 'poster-starter', 'scripts'),
];

const checkOnly = process.argv.slice(2).includes('--check');

async function main() {
  const drift = [];

  for (const runtimeName of runtimeNames) {
    const sourcePath = path.join(scriptDir, runtimeName);
    const source = await readFile(sourcePath);

    for (const targetDirectory of targetDirectories) {
      const targetPath = path.join(targetDirectory, runtimeName);
      let target;
      try {
        target = await readFile(targetPath);
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
      }

      if (target?.equals(source)) continue;
      drift.push(path.relative(root, targetPath));
      if (!checkOnly) {
        await mkdir(targetDirectory, { recursive: true });
        await writeFile(targetPath, source);
      }
    }
  }

  if (checkOnly && drift.length) {
    throw new Error(`Generated project runtimes are stale:\n${drift.map((item) => `- ${item}`).join('\n')}\nRun npm run runtime:sync.`);
  }

  process.stdout.write(`${JSON.stringify({ success: true, mode: checkOnly ? 'check' : 'sync', updated: checkOnly ? [] : drift })}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
