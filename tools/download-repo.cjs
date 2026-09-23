const https = require('https');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const OUT = 'F:\\dsh harness work\\goutoujunshi.zip';
const URL = 'https://api.github.com/repos/shengjidaguai-china/goutoujunshi/zipball/main';

console.log('Downloading...');
const req = https.get(URL, { headers: { 'User-Agent': 'Node.js' } }, (res) => {
  if (res.statusCode === 302 || res.statusCode === 301) {
    console.log('Redirecting to:', res.headers.location);
    https.get(res.headers.location, (res2) => {
      const stream = fs.createWriteStream(OUT);
      res2.pipe(stream);
      stream.on('finish', () => { console.log('Downloaded:', fs.statSync(OUT).size, 'bytes'); extract(OUT); });
    }).on('error', e => console.error('Redirect error:', e.message));
    return;
  }
  const stream = fs.createWriteStream(OUT);
  res.pipe(stream);
  stream.on('finish', () => { console.log('Downloaded:', fs.statSync(OUT).size, 'bytes'); extract(OUT); });
});
req.on('error', e => console.error('Error:', e.message));

function extract(zipPath) {
  const outDir = path.join(path.dirname(zipPath), 'goutoujunshi');
  try {
    execSync(`powershell -Command "Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory('${zipPath}', '${outDir}')"`, { stdio: 'inherit' });
    console.log('Extracted to', outDir);
    listFiles(outDir);
  } catch (e) {
    console.error('Extract error:', e.message);
  }
}

function listFiles(dir, prefix = '') {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) listFiles(full, prefix + entry.name + '/');
    else console.log(prefix + entry.name, '(' + fs.statSync(full).size + ' bytes)');
  }
}
