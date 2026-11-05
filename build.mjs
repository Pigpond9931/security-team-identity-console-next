import { build } from 'esbuild';
import { mkdir, copyFile, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
const projectRoot=fileURLToPath(new URL('.', import.meta.url));
process.chdir(projectRoot);
const policyPython=process.env.ST_POLICY_PYTHON||(existsSync('.venv/Scripts/python.exe')?'.venv/Scripts/python.exe':existsSync('.venv/bin/python')?'.venv/bin/python':'python');
execFileSync(policyPython,['tools/build_policy.py'],{stdio:'inherit'});
await mkdir('web/assets', { recursive: true });
await build({absWorkingDir:projectRoot,entryPoints:['frontend/app.jsx'],bundle:true,outfile:'web/assets/app.js',format:'iife',minify:true,define:{'process.env.NODE_ENV':'"production"'},loader:{'.woff2':'file'},assetNames:'[name]-[hash]',target:['chrome110','edge110','safari16']});
await copyFile('frontend/index.html','web/index.html');
await copyFile('frontend/motion-init.js','web/assets/motion-init.js');
const thirdParty=['react','react-dom','scheduler','lucide-react','jsqr','@fontsource-variable/manrope'];
const notices=['SECURITY TEAM Next — notices for bundled JavaScript and fonts.\n'];
for (const name of thirdParty) {
  const base=new URL(`./node_modules/${name}/`,import.meta.url);
  const metadata=JSON.parse(await readFile(new URL('package.json',base),'utf8'));
  notices.push(`\n${'='.repeat(72)}\n${name} ${metadata.version}\n${'='.repeat(72)}\n`+
    await readFile(new URL('LICENSE',base),'utf8'));
}
await writeFile('web/assets/third-party-notices.txt',notices.join('\n'),'utf8');
console.log('Interfaz React compilada en web/.');
