import { createHash } from 'node:crypto';
import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const FONT_SPECS = [
  {
    family: 'Ma Shan Zheng',
    source: '@fontsource/ma-shan-zheng/files/ma-shan-zheng-chinese-simplified-400-normal.woff2',
    file: 'assets/fonts/MaShanZheng-Chinese.woff2',
    licenseSource: '@fontsource/ma-shan-zheng/LICENSE',
    licenseFile: 'assets/licenses/MaShanZheng-OFL-1.1.txt',
    package: '@fontsource/ma-shan-zheng@5.3.0',
    samples: ['中文海报'],
  },
  {
    family: 'Ma Shan Zheng',
    source: '@fontsource/ma-shan-zheng/files/ma-shan-zheng-latin-400-normal.woff2',
    file: 'assets/fonts/MaShanZheng-Latin.woff2',
    licenseSource: '@fontsource/ma-shan-zheng/LICENSE',
    licenseFile: 'assets/licenses/MaShanZheng-OFL-1.1.txt',
    package: '@fontsource/ma-shan-zheng@5.3.0',
    samples: ['Poster title'],
  },
  {
    family: 'Noto Sans SC',
    source: '@fontsource-variable/noto-sans-sc/files/noto-sans-sc-119-wght-normal.woff2',
    file: 'assets/fonts/NotoSansSC-ChineseSubset.woff2',
    licenseSource: '@fontsource-variable/noto-sans-sc/LICENSE',
    licenseFile: 'assets/licenses/NotoSansSC-OFL-1.1.txt',
    package: '@fontsource-variable/noto-sans-sc@5.3.0',
    samples: ['中'],
  },
  {
    family: 'Noto Sans SC',
    source: '@fontsource-variable/noto-sans-sc/files/noto-sans-sc-latin-wght-normal.woff2',
    file: 'assets/fonts/NotoSansSC-Latin.woff2',
    licenseSource: '@fontsource-variable/noto-sans-sc/LICENSE',
    licenseFile: 'assets/licenses/NotoSansSC-OFL-1.1.txt',
    package: '@fontsource-variable/noto-sans-sc@5.3.0',
    samples: ['Poster title'],
  },
  {
    family: 'Noto Serif SC',
    source: '@fontsource-variable/noto-serif-sc/files/noto-serif-sc-119-wght-normal.woff2',
    file: 'assets/fonts/NotoSerifSC-ChineseSubset.woff2',
    licenseSource: '@fontsource-variable/noto-serif-sc/LICENSE',
    licenseFile: 'assets/licenses/NotoSerifSC-OFL-1.1.txt',
    package: '@fontsource-variable/noto-serif-sc@5.3.0',
    samples: ['中'],
  },
  {
    family: 'Noto Serif SC',
    source: '@fontsource-variable/noto-serif-sc/files/noto-serif-sc-latin-wght-normal.woff2',
    file: 'assets/fonts/NotoSerifSC-Latin.woff2',
    licenseSource: '@fontsource-variable/noto-serif-sc/LICENSE',
    licenseFile: 'assets/licenses/NotoSerifSC-OFL-1.1.txt',
    package: '@fontsource-variable/noto-serif-sc@5.3.0',
    samples: ['Poster title'],
  },
];

const LICENSE = {
  licenseId: 'OFL-1.1',
  licenseName: 'SIL Open Font License',
  licenseVersion: '1.1',
};

function parseArgs(argv) {
  if (argv.length !== 2 || argv[0] !== '--project' || !argv[1]) {
    throw new Error('Usage: node scripts/prepare-project.mjs --project PATH');
  }
  return { project: path.resolve(argv[1]) };
}

async function sha256(filePath) {
  return createHash('sha256').update(await readFile(filePath)).digest('hex');
}

function relativePath(value) {
  return value.split(path.sep).join('/');
}

function licenseRecords(fonts) {
  return fonts.map((font, index) => ({
    family: font.family,
    file: font.file,
    sha256: font.sha256,
    licenseFile: font.licenseFile,
    ...LICENSE,
    sourcePackage: FONT_SPECS[index].package,
  }));
}

function licensesMarkdown(fonts, records) {
  const sections = records.map((record, index) => [
    `## ${record.family} (${fonts[index].samples.join(', ')})`,
    '',
    `- Package: \`${record.sourcePackage}\``,
    `- File: \`${record.file}\``,
    `- SHA-256: \`${record.sha256}\``,
    `- License: ${record.licenseName} ${record.licenseVersion} (\`${record.licenseId}\`)`,
    `- License file: \`${record.licenseFile}\``,
  ].join('\n'));
  return `# Font and Asset Licenses\n\nGenerated from project-local pinned dependencies by \`npm run prepare\`.\n\n${sections.join('\n\n')}\n`;
}

async function main() {
  const { project } = parseArgs(process.argv.slice(2));
  const fontsDirectory = path.join(project, 'assets', 'fonts');
  const licensesDirectory = path.join(project, 'assets', 'licenses');
  await mkdir(fontsDirectory, { recursive: true });
  await mkdir(licensesDirectory, { recursive: true });

  const copiedLicenses = new Set();
  const fonts = [];
  for (const spec of FONT_SPECS) {
    const sourcePath = path.join(project, 'node_modules', spec.source);
    const targetPath = path.join(project, spec.file);
    const licenseSourcePath = path.join(project, 'node_modules', spec.licenseSource);
    const licenseTargetPath = path.join(project, spec.licenseFile);
    await copyFile(sourcePath, targetPath);
    if (!copiedLicenses.has(spec.licenseFile)) {
      await copyFile(licenseSourcePath, licenseTargetPath);
      copiedLicenses.add(spec.licenseFile);
    }
    fonts.push({
      family: spec.family,
      file: relativePath(spec.file),
      sha256: await sha256(targetPath),
      licenseFile: relativePath(spec.licenseFile),
      samples: spec.samples,
    });
  }

  const manifest = { version: 1, fonts };
  const manifestText = `${JSON.stringify(manifest, null, 2)}\n`;
  const licenseManifest = { version: 1, records: licenseRecords(fonts) };
  const licenseManifestText = `${JSON.stringify(licenseManifest, null, 2)}\n`;
  await writeFile(path.join(fontsDirectory, 'font-manifest.json'), manifestText);
  await writeFile(path.join(project, 'font-manifest.json'), manifestText);
  await writeFile(path.join(licensesDirectory, 'font-license-manifest.json'), licenseManifestText);
  await writeFile(path.join(project, 'font-license-manifest.json'), licenseManifestText);
  await writeFile(path.join(project, 'licenses.md'), licensesMarkdown(fonts, licenseManifest.records));
  process.stdout.write(`${JSON.stringify({ success: true, project, fonts: fonts.map(({ file }) => file) })}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
