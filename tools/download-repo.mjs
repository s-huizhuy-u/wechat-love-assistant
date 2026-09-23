const https = require('https');
const http = require('http');
const zlib = require('zlib');
const fs = require('fs');
const path = require('path');

const URL = 'https://api.github.com/repos/shengjidaguai-china/goutoujunshi/zipball/main';
const OUT = 'F:\\dsh harness work\\goutoujunshi.zip';

const parsed = new URL(URL);
const client = parsed.protocol === 'https:' ? https : http;

const req = client.get(URL, { headers: { 'User-Agent': 'Node.js' } }, (res) => {
  if (res.statusCode === 302 || res.statusCode === 301) {
    console.log('Redirecting to:', res.headers.location);
    const redirectUrl = new URL(res.headers.location);
    const redirectClient = redirectUrl.protocol === 'https:' ? https : http;
    redirectClient.get(redirectUrl, (res2) => {
      const stream = fs.createWriteStream(OUT);
      res2.pipe(stream);
      stream.on('finish', () => {
        console.log('Downloaded to', OUT, 'size:', fs.statSync(OUT).size);
        extractZip(OUT);
      });
    }).on('error', (e) => console.error('Redirect error:', e.message));
    return;
  }
  const stream = fs.createWriteStream(OUT);
  res.pipe(stream);
  stream.on('finish', () => {
    console.log('Downloaded to', OUT, 'size:', fs.statSync(OUT).size);
    extractZip(OUT);
  });
});
req.on('error', (e) => console.error('Request error:', e.message));

function extractZip(zipPath) {
  const data = fs.readFileSync(zipPath);
  zlib.unzip(data, (err, buffer) => {
    if (err) { console.error('Unzip error:', err.message); return; }
    const outDir = path.join(path.dirname(zipPath), 'goutoujunshi');
    if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
    const entries = [];
    const archive = require('archiver');
    // Use native approach
    const { execSync } = require('child_process');
    try {
      // Try 7z or powershell
      execSync(`powershell -Command "Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory('${zipPath}', '${outDir}')"`, { stdio: 'inherit' });
      console.log('Extracted to', outDir);
      listFiles(outDir);
    } catch (e) {
      console.error('Extraction failed:', e.message);
    }
  });
}

function listFiles(dir, prefix = '') {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      listFiles(full, prefix + entry.name + '/');
    } else {
      console.log(prefix + entry.name, '(' + fs.statSync(full).size + ' bytes)');
    }
  }
}
