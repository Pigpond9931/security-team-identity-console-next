import { build } from 'esbuild';
import { mkdir, copyFile } from 'node:fs/promises';
await mkdir('web/assets', { recursive: true });
await build({entryPoints:['frontend/app.jsx'],bundle:true,outfile:'web/assets/app.js',format:'iife',minify:true,define:{'process.env.NODE_ENV':'"production"'},loader:{'.woff2':'file'},assetNames:'[name]-[hash]',target:['chrome110','edge110','safari16']});
await copyFile('frontend/index.html','web/index.html');
console.log('Interfaz React compilada en web/.');
