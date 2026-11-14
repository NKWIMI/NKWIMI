#!/usr/bin/env node
// Prepares the Android project for Google Play:
//   1. sets your real package name (applicationId), e.g. com.grevi.ebolaguard
//   2. moves MainActivity.kt to the matching folder
//   3. adds release signing (reads android/key.properties)
//   4. creates config/release.json for your backend URL & hotline
//
// Run from the app/ folder:
//   node tools/prepare-release.js com.yourname.ebolaguard
//
// Safe to run again: steps that are already done are skipped.

const fs = require('node:fs');
const path = require('node:path');

const appDir = path.resolve(__dirname, '..');
const androidApp = path.join(appDir, 'android', 'app');
const gradleFile = path.join(androidApp, 'build.gradle.kts');

function fail(msg) {
  console.error('\n✖ ' + msg + '\n');
  process.exit(1);
}
function ok(msg) {
  console.log('✔ ' + msg);
}

const newId = process.argv[2];
if (!newId) {
  fail('Give your package name, e.g.:  node tools/prepare-release.js com.grevi.ebolaguard');
}
if (!/^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,}$/.test(newId)) {
  fail(`"${newId}" is not a valid package name. Use lowercase letters, numbers and dots, e.g. com.grevi.ebolaguard`);
}
if (newId.startsWith('com.example') || newId.startsWith('com.yourname')) {
  fail('Google Play does not accept com.example / com.yourname. Use your own name or organisation, e.g. com.grevi.ebolaguard');
}
if (!fs.existsSync(gradleFile)) {
  fail(`Cannot find ${gradleFile}. Run "flutter create ." first, and run this from the app folder.`);
}

let gradle = fs.readFileSync(gradleFile, 'utf8');

// ---- 1. package name -------------------------------------------------------
const nsMatch = gradle.match(/namespace\s*=\s*"([^"]+)"/);
const idMatch = gradle.match(/applicationId\s*=\s*"([^"]+)"/);
if (!nsMatch || !idMatch) fail('Could not find namespace / applicationId in build.gradle.kts');
const oldId = nsMatch[1];
gradle = gradle
  .replace(/namespace\s*=\s*"[^"]+"/, `namespace = "${newId}"`)
  .replace(/applicationId\s*=\s*"[^"]+"/, `applicationId = "${newId}"`);
ok(oldId === newId ? `Package name already ${newId}` : `Package name: ${oldId} → ${newId}`);

// ---- 2. move MainActivity.kt -------------------------------------------------
function findFile(dir, name) {
  if (!fs.existsSync(dir)) return null;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      const found = findFile(p, name);
      if (found) return found;
    } else if (entry.name === name) {
      return p;
    }
  }
  return null;
}
function removeEmptyDirs(dir, stopAt) {
  while (dir.startsWith(stopAt) && dir !== stopAt && fs.readdirSync(dir).length === 0) {
    fs.rmdirSync(dir);
    dir = path.dirname(dir);
  }
}
const srcRoot = path.join(androidApp, 'src', 'main', 'kotlin');
const activity = findFile(srcRoot, 'MainActivity.kt') || findFile(path.join(androidApp, 'src', 'main', 'java'), 'MainActivity.java');
if (!activity) fail('Could not find MainActivity.kt');
const ext = path.extname(activity);
const root = activity.includes(`${path.sep}kotlin${path.sep}`) ? srcRoot : path.join(androidApp, 'src', 'main', 'java');
const target = path.join(root, ...newId.split('.'), 'MainActivity' + ext);
let code = fs.readFileSync(activity, 'utf8').replace(/^package\s+[\w.]+;?/m, ext === '.java' ? `package ${newId};` : `package ${newId}`);
if (path.resolve(activity) !== path.resolve(target)) {
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, code);
  fs.unlinkSync(activity);
  removeEmptyDirs(path.dirname(activity), root);
  ok(`MainActivity moved to ${path.relative(appDir, target)}`);
} else {
  fs.writeFileSync(target, code);
  ok('MainActivity already in the right folder');
}

// ---- 3. release signing ------------------------------------------------------
if (gradle.includes('signingConfigs.getByName("release")')) {
  ok('Release signing already set up');
} else {
  if (!gradle.includes('import java.util.Properties')) {
    gradle = 'import java.util.Properties\nimport java.io.FileInputStream\n\n' + gradle;
  }
  // Load key.properties right after the plugins { } block.
  const pluginsEnd = gradle.indexOf('}', gradle.indexOf('plugins {'));
  if (pluginsEnd === -1) fail('Could not find the plugins { } block in build.gradle.kts');
  const loader = `

// Release signing key (see docs/release-guide.md). Never commit key.properties.
val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}`;
  gradle = gradle.slice(0, pluginsEnd + 1) + loader + gradle.slice(pluginsEnd + 1);

  const signing = `    signingConfigs {
        create("release") {
            keyAlias = keystoreProperties["keyAlias"] as String?
            keyPassword = keystoreProperties["keyPassword"] as String?
            storeFile = keystoreProperties["storeFile"]?.let { file(it) }
            storePassword = keystoreProperties["storePassword"] as String?
        }
    }

`;
  const bt = gradle.indexOf('    buildTypes {');
  if (bt === -1) fail('Could not find buildTypes { } in build.gradle.kts');
  gradle = gradle.slice(0, bt) + signing + gradle.slice(bt);

  if (!/signingConfig\s*=\s*signingConfigs\.getByName\("debug"\)/.test(gradle)) {
    fail('Could not find the debug signingConfig line in buildTypes.release');
  }
  gradle = gradle.replace(
    /signingConfig\s*=\s*signingConfigs\.getByName\("debug"\)/,
    'signingConfig = signingConfigs.getByName("release")',
  );
  ok('Release signing added (uses android/key.properties)');
}
fs.writeFileSync(gradleFile, gradle);

// Show SDK levels so you can check targetSdk >= 36 (Google Play requirement).
const sdk = gradle.match(/^\s*(minSdk|targetSdk|compileSdk)\s*=.*$/gm);
if (sdk) console.log('  SDK settings:\n    ' + sdk.map((s) => s.trim()).join('\n    '));

// ---- 4. key.properties template & release config ----------------------------
const keyProps = path.join(appDir, 'android', 'key.properties');
if (!fs.existsSync(keyProps)) {
  fs.writeFileSync(
    keyProps,
    [
      '# Fill in after creating your upload key (docs/release-guide.md, step 3).',
      '# KEEP THIS FILE AND THE .jks FILE PRIVATE AND BACKED UP.',
      'storePassword=CHANGE_ME',
      'keyPassword=CHANGE_ME',
      'keyAlias=upload',
      'storeFile=C:/Users/user/upload-keystore.jks',
      '',
    ].join('\n'),
  );
  ok('Created android/key.properties (fill in your passwords)');
} else {
  ok('android/key.properties already exists');
}

const releaseCfg = path.join(appDir, 'config', 'release.json');
if (!fs.existsSync(releaseCfg)) {
  fs.mkdirSync(path.dirname(releaseCfg), { recursive: true });
  fs.copyFileSync(path.join(appDir, 'config', 'release.example.json'), releaseCfg);
  ok('Created config/release.json (put your backend URL and hotline in it)');
} else {
  ok('config/release.json already exists');
}

console.log('\nDone. Next: follow docs/release-guide.md from step 3.\n');
