import { createHash } from 'node:crypto';
import { copyFile, lstat, readFile, realpath, writeFile } from 'node:fs/promises';
import path from 'node:path';
import * as fontkit from 'fontkit';
import { loadFontConfig, customLicensePolicy } from './font-policy.mjs';
import { assertSafeDestinationPath, ensureSafeDirectory, publishProjectFile, resolveProjectRoot } from './path-safety.mjs';

const FONT_PACKAGES = [
  {
    family: 'Ma Shan Zheng',
    slug: 'ma-shan-zheng',
    cssSource: '@fontsource/ma-shan-zheng/400.css',
    licenseSource: '@fontsource/ma-shan-zheng/LICENSE',
    licenseFile: 'assets/licenses/MaShanZheng-OFL-1.1.txt',
    licenseSha256: '37784825d863bab31cdff1f4bfabae5b8d8e9913b91db2064a6b803b2edc92db',
    package: '@fontsource/ma-shan-zheng@5.3.0',
  },
  {
    family: 'Noto Sans SC',
    sourceFamily: 'Noto Sans SC Variable',
    slug: 'noto-sans-sc',
    cssSource: '@fontsource-variable/noto-sans-sc/wght.css',
    licenseSource: '@fontsource-variable/noto-sans-sc/LICENSE',
    licenseFile: 'assets/licenses/NotoSansSC-OFL-1.1.txt',
    licenseSha256: '18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3',
    package: '@fontsource-variable/noto-sans-sc@5.3.0',
  },
  {
    family: 'Noto Serif SC',
    sourceFamily: 'Noto Serif SC Variable',
    slug: 'noto-serif-sc',
    cssSource: '@fontsource-variable/noto-serif-sc/wght.css',
    licenseSource: '@fontsource-variable/noto-serif-sc/LICENSE',
    licenseFile: 'assets/licenses/NotoSerifSC-OFL-1.1.txt',
    licenseSha256: '18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3',
    package: '@fontsource-variable/noto-serif-sc@5.3.0',
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

function declaration(block, name) {
  return block.match(new RegExp(`${name}\\s*:\\s*([^;]+);`, 'i'))?.[1]?.trim() ?? null;
}

function parsePinnedFaces(css, spec) {
  const faces = [];
  for (const match of css.matchAll(/@font-face\s*\{([\s\S]*?)\}/gi)) {
    const block = match[1];
    const family = declaration(block, 'font-family')?.replace(/^['"]|['"]$/g, '');
    const source = [...block.matchAll(/url\(\s*["']?([^"')]+\.woff2)["']?\s*\)/gi)][0]?.[1];
    const unicodeRange = declaration(block, 'unicode-range');
    if (family !== (spec.sourceFamily ?? spec.family) || !source || !unicodeRange) {
      throw new Error(`Pinned font CSS is incomplete for ${spec.package}`);
    }
    const basename = path.posix.basename(source);
    faces.push({
      ...spec,
      source: path.posix.join(path.posix.dirname(spec.cssSource), source.replace(/^\.\//, '')),
      file: `assets/fonts/${spec.slug}/${basename}`,
      style: declaration(block, 'font-style') ?? 'normal',
      weight: declaration(block, 'font-weight') ?? '400',
      unicodeRange,
    });
  }
  if (!faces.length) throw new Error(`Pinned font CSS declares no WOFF2 faces for ${spec.package}`);
  return faces;
}

function explicitSample(buffer) {
  const parsed = fontkit.create(buffer);
  const codePoint = parsed.characterSet.find((value) => String.fromCodePoint(value).trim() !== '');
  if (codePoint === undefined) throw new Error('Pinned font shard contains no explicit sample glyph');
  return String.fromCodePoint(codePoint);
}

function fontCss(fonts, roles) {
  const blocks = fonts.map((font) => [
    '@font-face {',
    `  font-family: "${font.family}";`,
    `  src: url("${font.file}") format("${({ '.ttf': 'truetype', '.otf': 'opentype', '.woff': 'woff' })[path.extname(font.file).toLowerCase()] ?? 'woff2'}");`,
    `  font-style: ${font.style};`,
    `  font-weight: ${font.weight};`,
    '  font-display: block;',
    `  unicode-range: ${font.unicodeRange};`,
    '}',
  ].join('\n'));
  const roleCss = roles ? `\n:root {\n${Object.entries(roles).map(([role, family]) => `  --font-${role}: "${family}";`).join('\n')}\n}\n` : '';
  return `/* Generated from selected project fonts by npm run prepare. */\n\n${blocks.join('\n\n')}\n${roleCss}`;
}

function licenseRecords(fonts) {
  return fonts.map((font) => ({
    family: font.family,
    file: font.file,
    sha256: font.sha256,
    licenseFile: font.licenseFile,
    licenseSha256: font.licenseSha256,
    ...(font.license ?? LICENSE),
    sourcePackage: font.package,
  }));
}

function licensesMarkdown(fonts) {
  const families = [...new Map(fonts.map((font) => [font.family, font])).values()];
  const sections = families.map((font) => [
    `## ${font.family}`,
    '',
    `- Package: \`${font.package}\``,
    `- Bundled WOFF2 shards: ${fonts.filter((entry) => entry.family === font.family).length}`,
    `- License: ${(font.license ?? LICENSE).licenseName} ${(font.license ?? LICENSE).licenseVersion} (\`${(font.license ?? LICENSE).licenseId}\`)`,
    `- License file: \`${font.licenseFile}\``,
    `- License SHA-256: \`${font.licenseSha256}\``,
  ].join('\n'));
  return [
    '# Font and Asset Licenses',
    '',
    'Generated from project-local pinned dependencies by `npm run prepare`.',
    'Per-file font hashes are recorded in `font-license-manifest.json`.',
    'Non-font asset rights and authorization are recorded in `asset-manifest.json`.',
    '',
    sections.join('\n\n'),
    '',
  ].join('\n');
}

async function writeText(project, destination, value) {
  await publishProjectFile(project, destination, (temporary) => writeFile(temporary, value));
}

async function rejectCustomInputCollisions(project, customFonts, destinations) {
  const inputs = new Set(customFonts.flatMap((font) => [font.file, font.licenseFile, font.authorization.evidenceFile]));
  const identities = [];
  for (const input of inputs) {
    const file = path.join(project, input);
    const stats = await lstat(file, { bigint: true });
    identities.push({ input, resolved: await realpath(file), dev: stats.dev, ino: stats.ino });
  }
  for (const destination of destinations) {
    let stats;
    let resolved = path.resolve(destination);
    try {
      stats = await lstat(destination, { bigint: true });
      resolved = await realpath(destination);
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
    const collision = identities.find((input) => input.resolved === resolved
      || (stats && input.dev === stats.dev && input.ino === stats.ino));
    if (collision) throw new Error(`Custom font input collides with prepare output: ${collision.input} -> ${relativePath(path.relative(project, destination))}`);
  }
}

async function main() {
  const parsed = parseArgs(process.argv.slice(2));
  const project = await resolveProjectRoot(parsed.project);
  const config = await loadFontConfig(project);
  const selectedPackages = FONT_PACKAGES.filter((spec) => config.families.includes(spec.family));
  const fontsDirectory = path.join(project, 'assets', 'fonts');
  const licensesDirectory = path.join(project, 'assets', 'licenses');

  const specs = [];
  for (const fontPackage of selectedPackages) {
    const css = await readFile(path.join(project, 'node_modules', fontPackage.cssSource), 'utf8');
    specs.push(...parsePinnedFaces(css, fontPackage));
  }
  const destinations = [
    ...specs.map((spec) => path.join(project, spec.file)),
    ...selectedPackages.map((spec) => path.join(project, spec.licenseFile)),
    path.join(project, 'font-faces.css'),
    path.join(project, 'font-manifest.json'),
    path.join(fontsDirectory, 'font-manifest.json'),
    path.join(project, 'font-license-manifest.json'),
    path.join(licensesDirectory, 'font-license-manifest.json'),
    path.join(project, 'licenses.md'),
  ];
  for (const destination of destinations) {
    await assertSafeDestinationPath(project, destination);
  }
  await rejectCustomInputCollisions(project, config.customFonts, destinations);
  await ensureSafeDirectory(project, fontsDirectory);
  await ensureSafeDirectory(project, licensesDirectory);

  const copiedLicenses = new Set();
  const fonts = [];
  for (const spec of specs) {
    const sourcePath = path.join(project, 'node_modules', spec.source);
    const targetPath = path.join(project, spec.file);
    await publishProjectFile(project, targetPath, (temporary) => copyFile(sourcePath, temporary));
    if (!copiedLicenses.has(spec.licenseFile)) {
      const licenseSourcePath = path.join(project, 'node_modules', spec.licenseSource);
      const licenseTargetPath = path.join(project, spec.licenseFile);
      const actualSourceHash = await sha256(licenseSourcePath);
      if (actualSourceHash !== spec.licenseSha256) {
        throw new Error(`Pinned license hash mismatch for ${spec.family}: expected ${spec.licenseSha256}, got ${actualSourceHash}`);
      }
      await publishProjectFile(project, licenseTargetPath, (temporary) => copyFile(licenseSourcePath, temporary));
      copiedLicenses.add(spec.licenseFile);
    }
    const buffer = await readFile(targetPath);
    fonts.push({
      family: spec.family,
      file: relativePath(spec.file),
      sha256: createHash('sha256').update(buffer).digest('hex'),
      licenseFile: relativePath(spec.licenseFile),
      unicodeRange: spec.unicodeRange,
      samples: [explicitSample(buffer)],
      package: spec.package,
      licenseSha256: spec.licenseSha256,
      style: spec.style,
      weight: spec.weight,
    });
  }

  for (const custom of config.customFonts) {
    const buffer = await readFile(path.join(project, custom.file));
    const policy = customLicensePolicy(custom);
    const parsedFont = fontkit.create(buffer);
    const weight = parsedFont.variationAxes?.wght;
    fonts.push({ family: custom.family, file: custom.file, sha256: custom.sha256,
      licenseFile: custom.licenseFile, licenseSha256: custom.licenseSha256,
      package: policy.sourcePackage,
      license: { licenseId: policy.licenseId, licenseName: policy.licenseName, licenseVersion: policy.licenseVersion },
      unicodeRange: 'U+0-10FFFF', samples: [explicitSample(buffer)],
      style: /italic|oblique/i.test(parsedFont.subfamilyName ?? '') ? 'italic' : 'normal',
      weight: weight ? `${weight.min} ${weight.max}` : String(parsedFont['OS/2']?.usWeightClass ?? 400),
    });
  }
  const manifestFonts = fonts.map(({ package: _package, license: _license, licenseSha256: _licenseSha256, style: _style, weight: _weight, ...font }) => font);
  const manifest = { version: 2, ...(config.roles ? { roles: config.roles } : {}), fonts: manifestFonts };
  const manifestText = `${JSON.stringify(manifest, null, 2)}\n`;
  const licenseManifest = { version: 1, records: licenseRecords(fonts) };
  const licenseManifestText = `${JSON.stringify(licenseManifest, null, 2)}\n`;
  await writeText(project, path.join(project, 'font-faces.css'), fontCss(fonts, config.roles));
  await writeText(project, path.join(fontsDirectory, 'font-manifest.json'), manifestText);
  await writeText(project, path.join(project, 'font-manifest.json'), manifestText);
  await writeText(project, path.join(licensesDirectory, 'font-license-manifest.json'), licenseManifestText);
  await writeText(project, path.join(project, 'font-license-manifest.json'), licenseManifestText);
  await writeText(project, path.join(project, 'licenses.md'), licensesMarkdown(fonts));
  process.stdout.write(`${JSON.stringify({ success: true, project, fonts: fonts.map(({ file }) => file) })}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
