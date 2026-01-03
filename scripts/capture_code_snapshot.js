// capture_code_snapshot.js - Generic Code Snapshot Utility
// Captures code files from a directory into a single text file for sharing with LLMs
// No external dependencies required

const fs = require('fs');
const path = require('path');

// Parse command line args manually (no yargs dependency)
const args = process.argv.slice(2);
const subfolderArg = args.find(a => !a.startsWith('--'));
const outArg = args.find(a => a.startsWith('--out='));
const nameArg = args.find(a => a.startsWith('--name='));

// When run from scripts/ folder, go up one level to project root
const projectRoot = path.join(__dirname, '..');
const targetRoot = subfolderArg ? path.join(projectRoot, subfolderArg) : projectRoot;
const subfolderName = subfolderArg
    ? subfolderArg.replace(/\//g, '_').replace(/\\/g, '_')
    : 'full_repo';

const outputDir = path.join(projectRoot, outArg ? outArg.split('=')[1] : 'dataset_package');
const outputFileName = nameArg ? nameArg.split('=')[1] : `snapshot_${subfolderName}`;
const outputFile = path.join(outputDir, `${outputFileName}.txt`);

// Standard exclusions - common dev/build artifacts
const excludeDirNames = new Set([
    '.git', '.svn', '.hg', '.bzr',
    'node_modules', '.pnpm', '.yarn', 'bower_components',
    'dist', 'build', 'out', '.next', '.nuxt', '.svelte-kit',
    '.cache', '.turbo', '.parcel-cache', 'coverage',
    '__pycache__', '.venv', 'venv', 'env', '.tox', '.pytest_cache',
    '.eggs', 'pip-wheel-metadata', '.ipynb_checkpoints',
    '.vscode', '.idea', '.devcontainer',
    'tmp', 'temp', 'logs',
    'models', 'weights', 'checkpoints', 'dataset_package',
    'chroma_db', 'chroma_db_backup',
    // Project-specific exclusions for cleaner snapshots
    'tests', 'docs', 'examples', 'charts', 'deployment',
    'plugins', 'plugins_rust', 'plugin_templates',
    'mcp-servers', 'agent_runtimes', 'llms', 'nginx', 'data', 'certs',
    '.github', 'mcp_contextforge_gateway.egg-info'
]);

// File patterns to always exclude
const excludeFilePatterns = [
    '.DS_Store', '.env', '.gitignore',
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
];

const excludeExtensions = new Set([
    '.pyc', '.pyo', '.pyd', '.gguf', '.bin', '.safetensors', '.ckpt', '.pth',
    '.onnx', '.pb', '.log', '.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg',
    '.webp', '.mp3', '.mp4', '.wav', '.avi', '.mov', '.zip', '.tar', '.gz',
    '.rar', '.7z', '.pdf', '.doc', '.docx', '.xls', '.xlsx'
]);

function shouldExcludeFile(baseName) {
    if (excludeFilePatterns.includes(baseName)) return true;
    const ext = path.extname(baseName).toLowerCase();
    return excludeExtensions.has(ext);
}

// Allowed file extensions
const allowedExtensions = new Set([
    '.md', '.py', '.js', '.ts', '.jsx', '.tsx',
    '.json', '.yaml', '.yml', '.toml',
    '.sh', '.bash', '.zsh', '.ps1', '.bat',
    '.txt', '.cfg', '.ini',
    '.c', '.cpp', '.h', '.hpp', '.java', '.rb', '.go', '.rs',
    '.html', '.css', '.scss', '.sass', '.vue', '.svelte',
    '.sql', '.graphql', '.proto', '.dockerfile', '.tf'
]);

const fileSeparatorStart = '--- START OF FILE';
const fileSeparatorEnd = '--- END OF FILE';

function appendFileContent(filePath, basePath) {
    const relativePath = path.relative(basePath, filePath).replace(/\\/g, '/');
    let fileContent = '';
    try {
        fileContent = fs.readFileSync(filePath, 'utf8');
    } catch (err) {
        fileContent = `[Read error: ${err.message}]`;
    }
    return `${fileSeparatorStart} ${relativePath} ---\n\n${fileContent.trim()}\n\n${fileSeparatorEnd} ${relativePath} ---\n`;
}

try {
    console.log(`[SNAPSHOT] Code snapshot utility`);
    console.log(`Usage: node capture_code_snapshot.js [directory] [--out=dir] [--name=filename]`);
    console.log('');

    const fileTreeLines = [];
    let snapshotContent = '';
    let filesCaptured = 0;
    let itemsSkipped = 0;

    function traverse(currentPath) {
        const baseName = path.basename(currentPath);
        if (excludeDirNames.has(baseName)) { itemsSkipped++; return; }

        const stats = fs.statSync(currentPath);
        const relativePath = path.relative(targetRoot, currentPath).replace(/\\/g, '/');

        if (relativePath) {
            fileTreeLines.push(relativePath + (stats.isDirectory() ? '/' : ''));
        }

        if (stats.isDirectory()) {
            fs.readdirSync(currentPath).sort().forEach(item => {
                traverse(path.join(currentPath, item));
            });
        } else if (stats.isFile()) {
            if (shouldExcludeFile(baseName)) { itemsSkipped++; return; }
            const ext = path.extname(baseName).toLowerCase();
            if (!allowedExtensions.has(ext)) { itemsSkipped++; return; }

            snapshotContent += appendFileContent(currentPath, targetRoot) + '\n';
            filesCaptured++;
        }
    }

    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    if (subfolderArg) {
        console.log(`[MODE] Subfolder: ${subfolderArg}`);
        if (!fs.existsSync(targetRoot)) {
            console.error(`[ERROR] Directory not found: ${subfolderArg}`);
            process.exit(1);
        }
    } else {
        console.log(`[MODE] Full repository`);
    }

    traverse(targetRoot);

    const prefix = subfolderArg || 'project root';
    const header = `# ${subfolderArg ? subfolderArg + ' Snapshot' : 'Repository Snapshot'}\nGenerated: ${new Date().toISOString()}\n\n`;
    const fileTree = `# Directory Structure (${prefix})\n${fileTreeLines.map(l => '  ./' + l).join('\n')}\n\n`;

    fs.writeFileSync(outputFile, (header + fileTree + snapshotContent).trim(), 'utf8');

    const sizeKB = (fs.statSync(outputFile).size / 1024).toFixed(1);
    console.log(`\n[SUCCESS] ${path.relative(projectRoot, outputFile)}`);
    console.log(`[STATS] Files: ${filesCaptured} | Skipped: ${itemsSkipped} | Size: ${sizeKB} KB`);

} catch (err) {
    console.error(`[FATAL] ${err.message}`);
}