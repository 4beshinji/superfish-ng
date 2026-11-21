// SPDX-License-Identifier: Apache-2.0
import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
const option = name => process.argv.find(arg => arg.startsWith(`${name}=`))?.split('=').slice(1).join('=');
const profile = option('--user-data-dir');
if (option('--fake-mode') === 'exit') process.exit(7);
let child;
if (option('--fake-mode') === 'stubborn') {
  process.on('SIGTERM', () => {});
  child = spawn(process.execPath, ['-e', 'process.on("SIGTERM",()=>{});setInterval(()=>{},1000)'], { stdio: 'ignore' });
}
if (option('--fake-bytes')) writeFileSync(`${profile}/cache`, Buffer.alloc(Number(option('--fake-bytes'))));
if (option('--fake-mode') === 'verbose') process.stderr.write('x'.repeat(1024 * 1024));
writeFileSync(`${profile}/ready.json`, JSON.stringify({ pid: process.pid, child: child?.pid,
  cache: process.env.XDG_CACHE_HOME, config: process.env.XDG_CONFIG_HOME, tmp: process.env.TMPDIR }));
setInterval(() => {}, 1000);
