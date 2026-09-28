"""Bounded CLI browser lifecycle checks; no FEM or Chrome dependency for unit cases."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = (ROOT / "scripts/browser-session.mjs").as_uri()
FAKE = ROOT / "tests/fixtures/fake_browser.mjs"


def live(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        return fields[0] not in {"Z", "X"}
    except FileNotFoundError:
        return False


class BrowserSessionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="superfish-browser-unit-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = self.root / "state"
        self.prelude = f"""
import {{ launchBrowser }} from {json.dumps(MODULE)};
import {{ readFile, writeFile }} from 'node:fs/promises';
const stateRoot = {json.dumps(str(self.state))};
const executable = process.execPath;
const args = [{json.dumps(str(FAKE))}];
const pause = ms => new Promise(done => setTimeout(done, ms));
async function ready(session) {{
  for (let i=0;i<100;i++) {{
    try {{ return JSON.parse(await readFile(session.profile + '/ready.json','utf8')); }} catch {{}}
    await pause(20);
  }}
  throw Error('fake browser did not start');
}}
"""

    def run_node(self, body, expected=0, timeout=20):
        result = subprocess.run(
            ["node", "--input-type=module", "-e", self.prelude + body],
            capture_output=True, text=True, timeout=timeout, cwd=ROOT,
        )
        self.assertEqual(result.returncode, expected, result.stderr)
        return result

    def assert_reaped(self):
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if not self.state.exists() or not list(self.state.iterdir()):
                return
            time.sleep(0.05)
        self.fail(f"retained state: {list(self.state.iterdir())}")

    def test_success_repeated_and_idempotent_disposal(self):
        result = self.run_node("""
for (let i=0;i<3;i++) {
  const session=await launchBrowser({stateRoot, executable, args});
  const info=await ready(session);
  if (![info.cache,info.config,info.tmp].every(path=>path.startsWith(stateRoot+'/slot-'))) throw Error('unowned state');
  await Promise.all([session.dispose(),session.dispose()]);
  console.log(JSON.stringify(info));
}
""")
        self.assert_reaped()
        for line in result.stdout.splitlines():
            self.assertFalse(live(json.loads(line)["pid"]))

    def test_report_write_failure_still_disposes(self):
        result = self.run_node("""
const session=await launchBrowser({stateRoot, executable, args});
await ready(session);
try { throw Error('verification failed'); }
finally {
  try { await writeFile(session.profile+'/absent/report.json','report'); }
  finally { await session.dispose(); }
}
""", expected=1)
        self.assertIn("ENOENT", result.stderr)
        self.assert_reaped()

    def test_exception_before_finally_is_cleaned_by_guardian(self):
        self.run_node("""
const session=await launchBrowser({stateRoot, executable, args});
await ready(session);
throw Error('source hash failed before the verifier try block');
""", expected=1)
        self.assert_reaped()

    def test_failed_executable_does_not_reserve_a_slot(self):
        result = self.run_node("await launchBrowser({stateRoot, executable:'/not/a/browser'});", expected=1)
        self.assertIn("ENOENT", result.stderr)
        self.assert_reaped()

    def test_stubborn_browser_and_descendant_are_killed(self):
        result = self.run_node("""
const session=await launchBrowser({stateRoot, executable, args:[...args,'--fake-mode=stubborn'],limits:{graceMs:150}});
const info=await ready(session); await pause(100); await session.dispose(); console.log(JSON.stringify(info));
""")
        info = json.loads(result.stdout)
        self.assertFalse(live(info["pid"]))
        self.assertFalse(live(info["child"]))
        self.assert_reaped()

    def test_live_slot_capacity_and_reuse(self):
        result = self.run_node("""
const first=await launchBrowser({stateRoot, executable, args});
const second=await launchBrowser({stateRoot, executable, args});
try {
  try { await launchBrowser({stateRoot, executable, args}); throw Error('admitted a third browser'); }
  catch(error) { if (!error.message.includes('both browser verification slots')) throw error; }
  await first.dispose();
  const next=await launchBrowser({stateRoot, executable, args}); await next.dispose();
} finally { await first.dispose(); await second.dispose(); }
""")
        self.assertEqual(result.stdout, "")
        self.assert_reaped()

    def test_simultaneous_admission_is_bounded(self):
        self.run_node("""
const results=await Promise.allSettled(Array.from({length:3},()=>launchBrowser({stateRoot,executable,args})));
const sessions=results.filter(result=>result.status==='fulfilled').map(result=>result.value);
try {
  if (sessions.length!==2) throw Error('concurrent admission must reserve exactly two slots');
  if (!results.find(result=>result.status==='rejected').reason.message.includes('both browser verification slots')) throw Error('wrong rejection');
} finally { await Promise.all(sessions.map(session=>session.dispose())); }
""")
        self.assert_reaped()

    def test_unexpected_browser_exit_fails_and_cleans(self):
        result = self.run_node("""
await launchBrowser({stateRoot, executable, args:[...args,'--fake-mode=exit']});
setInterval(()=>{},1000);
""", expected=1)
        self.assertIn("browser exited", result.stderr)
        self.assert_reaped()

    def test_dead_guardian_with_live_browser_record_is_preserved(self):
        self.state.mkdir(mode=0o700)
        slot = self.state / "slot-0"
        slot.mkdir(mode=0o700)
        start = Path(f"/proc/{os.getpid()}/stat").read_text().rsplit(") ", 1)[1].split()[19]
        record = json.dumps({
            "version": 1, "phase": "ready",
            "guardian": {"pid": os.getpid(), "start": "0"},
            "chrome": {"pid": os.getpid(), "start": start},
        })
        (slot / "owner.json").write_text(record)
        result = self.run_node("""
const session=await launchBrowser({stateRoot,executable,args});
console.log(session.profile); await session.dispose();
""")
        self.assertTrue(result.stdout.strip().endswith("slot-1/profile"))
        self.assertEqual((slot / "owner.json").read_text(), record)
        self.assertEqual(list(self.state.iterdir()), [slot])

    def test_signal_and_parent_sigkill_cleanup(self):
        for stop_signal in (signal.SIGTERM, signal.SIGKILL):
            with self.subTest(signal=stop_signal):
                marker = self.root / "started.json"
                code = self.prelude + f"""
const session=await launchBrowser({{stateRoot, executable, args}});
const info=await ready(session);
await writeFile({json.dumps(str(marker))},JSON.stringify(info));
setInterval(()=>{{}},1000);
"""
                with (self.root / "child.log").open("w+") as log:
                    child = subprocess.Popen(["node", "--input-type=module", "-e", code], stdout=log, stderr=log)
                    try:
                        deadline = time.monotonic() + 10
                        while not marker.exists() and time.monotonic() < deadline:
                            self.assertIsNone(child.poll())
                            time.sleep(0.05)
                        self.assertTrue(marker.exists())
                        info = json.loads(marker.read_text())
                        child.send_signal(stop_signal)
                        child.wait(timeout=15)
                        self.assert_reaped()
                        self.assertFalse(live(info["pid"]))
                    finally:
                        if child.poll() is None:
                            child.kill(); child.wait(timeout=10)
                        marker.unlink(missing_ok=True)

    def test_deadline_fails_and_cleans(self):
        result = self.run_node("""
await launchBrowser({stateRoot, executable, args, limits:{timeoutMs:300}});
setInterval(()=>{},1000);
""", expected=124)
        self.assertIn("deadline exceeded", result.stderr)
        self.assert_reaped()

    def test_byte_budget_fails_and_cleans(self):
        result = self.run_node("""
await launchBrowser({stateRoot, executable, args:[...args,'--fake-bytes=262144'],limits:{maxBytes:65536,pollMs:50}});
setInterval(()=>{},1000);
""", expected=1)
        self.assertIn("byte budget", result.stderr)
        self.assert_reaped()

    def test_unknown_and_symlink_slots_are_preserved(self):
        self.state.mkdir(mode=0o700)
        (self.state / "slot-0").mkdir(mode=0o700)
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "data").write_text("preserve")
        (self.state / "slot-1").symlink_to(outside, target_is_directory=True)
        result = self.run_node("await launchBrowser({stateRoot, executable, args});", expected=1)
        self.assertIn("both browser verification slots", result.stderr)
        self.assertEqual((outside / "data").read_text(), "preserve")
        self.assertTrue((self.state / "slot-0").is_dir())
        self.assertTrue((self.state / "slot-1").is_symlink())

    def test_dead_record_reclaimed_without_trusting_pid_reuse(self):
        self.state.mkdir(mode=0o700)
        slot = self.state / "slot-0"
        slot.mkdir(mode=0o700)
        # Same PID with a different start time is not the recorded owner.
        (slot / "owner.json").write_text(json.dumps({
            "version": 1, "phase": "allocated",
            "guardian": {"pid": os.getpid(), "start": "0"}, "chrome": None,
        }))
        (slot / "old-cache").write_bytes(b"stale")
        self.run_node("const session=await launchBrowser({stateRoot, executable, args});await session.dispose();")
        self.assert_reaped()

    def test_all_verifiers_use_shared_lifecycle_and_parse(self):
        verifiers = []
        for path in sorted((ROOT / "scripts").glob("verify*.mjs")):
            source = path.read_text()
            if "launchBrowser" not in source:
                continue
            verifiers.append(path)
            self.assertNotIn("mkdtemp", source, path.name)
            self.assertNotIn("browser.kill(", source, path.name)
            self.assertIn("await dispose()", source, path.name)
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(verifiers), 63)
        for path in (ROOT / "scripts").glob("*.mjs"):
            self.assertNotIn('mkdtemp("/tmp/ng-gui-chrome-', path.read_text(), path.name)


if __name__ == "__main__":
    unittest.main()
