"""codex-bootstrap and the codex-main profile switch; mocks only, no network, no secrets on argv."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parents[1]
FAKE_KEY = 'sk-ant-FAKE-VALUE-THAT-MUST-NEVER-APPEAR'

OCX = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
state = Path(os.environ['MOCK_STATE'])
data = json.loads(state.read_text()) if state.is_file() else {"calls": [], "provider": False, "claude": "on"}
args = sys.argv[1:]
data["calls"].append(args)
if args[:1] == ['--version']:
    print('opencodex 2.99.0')
elif args[:2] == ['provider', 'show']:
    if data["provider"]:
        print('Provider: anthropic-apikey (default)')
    else:
        print('Provider "anthropic-apikey" is not configured.'); state.write_text(json.dumps(data)); sys.exit(1)
elif args[:2] == ['provider', 'add']:
    data["provider"] = True; print('added')
elif args[:2] == ['account', 'list']:
    print('PROVIDER TYPE ID'); print('anthropic-apikey  api-key  11111111  ${X}  -')
elif args[:2] == ['models', 'live']:
    print('anthropic-apikey/claude-fable-5-2  [routed, enabled]'); print('anthropic-apikey/claude-opus-5-5  [routed, enabled]')
elif args[:2] == ['integration', 'native'] and len(args) == 2:
    print('CLIENT STATE INSTALLED DESIRED CONFIG'); print('claude  absent  yes  ' + data["claude"] + '  x'); print('codex  current  yes  on  y')
elif args[:4] == ['integration', 'native', 'claude', 'off']:
    data["claude"] = 'off'; print('ok: true')
elif args[:2] == ['service', 'install']:
    data["service"] = True; print('installed')
state.write_text(json.dumps(data))
'''

SYSTEMCTL = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
state = Path(os.environ['MOCK_STATE'])
data = json.loads(state.read_text()) if state.is_file() else {"calls": []}
args = sys.argv[1:]
data.setdefault("systemctl", []).append(args)
state.write_text(json.dumps(data))
if 'show-environment' in args:
    sys.exit(0)
if 'cat' in args:
    sys.exit(0 if data.get("service") else 1)
if args[-3:-1] == ['-p', 'MainPID'] or 'MainPID' in args:
    print(os.environ['MOCK_MAIN_PID'])
'''

CODEX = r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
if '--version' in sys.argv:
    print('codex-cli 0.167.0'); sys.exit(0)
Path(__import__('os').environ['MOCK_CODEX_ARGS']).write_text(json.dumps(sys.argv[1:]))
'''

HEALTH = r'''#!/usr/bin/env python3
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"status": "ok"}).encode()
        self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a):
        pass
HTTPServer(('127.0.0.1', int(sys.argv[1])), H).serve_forever()
'''


def free_port():
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def mock(path, text, env_check=None):
    path.write_text(text)
    path.chmod(0o755)


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='codex-bootstrap-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.bin = self.root / 'mockbin'
        self.bin.mkdir()
        self.state = self.root / 'state.json'
        mock(self.bin / 'ocx', OCX)
        mock(self.bin / 'systemctl', SYSTEMCTL)
        mock(self.bin / 'codex', CODEX)
        mock(self.bin / 'bwrap', '#!/bin/sh\nexit ${MOCK_BWRAP_RC:-1}\n')
        mock(self.bin / 'loginctl', '#!/bin/sh\necho no\n')
        # The proxy "process": carries the key variable names (values are fake) for the /proc environ check.
        self.proxy = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'],
                                      env=dict(os.environ, ANTHROPIC_API_KEY_PRIMARY=FAKE_KEY, ANTHROPIC_API_KEY_SECONDARY=FAKE_KEY))
        self.addCleanup(self.stop, self.proxy)
        self.port = free_port()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('LLM_', 'ANTHROPIC_', 'CODEX_'))}
        self.conf = self.home / '.config/local-worker'
        self.env.update(HOME=str(self.home), PATH=str(self.bin) + os.pathsep + os.defpath, MOCK_STATE=str(self.state),
                        MOCK_MAIN_PID=str(self.proxy.pid), PYTHONDONTWRITEBYTECODE='1', USER='tester', LLM_WORKER_CONF_DIR=str(self.conf),
                        MOCK_CODEX_ARGS=str(self.root / 'codex-args.json'), CODEX_BOOTSTRAP_PROXY_URL='http://127.0.0.1:%d' % self.port)

    @staticmethod
    def stop(proc):
        proc.kill()
        proc.wait(timeout=10)

    def start_health(self):
        script = self.root / 'health.py'
        script.write_text(HEALTH)
        proc = subprocess.Popen([sys.executable, str(script), str(self.port)])
        self.addCleanup(self.stop, proc)
        import time
        import urllib.request
        for _ in range(50):
            try:
                urllib.request.urlopen('http://127.0.0.1:%d/healthz' % self.port, timeout=1)
                return
            except Exception:
                time.sleep(0.1)
        self.fail('mock health endpoint did not start')

    def run_tool(self, *args, code=0):
        result = subprocess.run([sys.executable, '-B', str(KIT / 'bin/codex-bootstrap'), *args], env=self.env,
                                capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def calls(self):
        return json.loads(self.state.read_text())['calls'] if self.state.is_file() else []

    def test_check_mode_changes_nothing_and_plans_every_step(self):
        out = self.run_tool('--check')
        self.assertFalse((self.home / '.config/opencodex/keys.env').exists())
        self.assertFalse((self.home / '.codex/orch.config.toml').exists())
        self.assertNotIn('provider add', ' '.join(' '.join(c) for c in self.calls()))
        for step in ('keys.env', 'provider', 'service', 'codex profile', 'shell env', 'sandbox', 'linger'):
            self.assertIn('[todo] ' + step, out)
        self.assertIn('apparmor_parser', out)

    def test_apply_is_idempotent_and_never_handles_key_values(self):
        self.start_health()
        out = self.run_tool('--yes')
        keys = self.home / '.config/opencodex/keys.env'
        self.assertEqual(stat.S_IMODE(keys.stat().st_mode), 0o600)
        self.assertEqual(keys.read_text(), 'ANTHROPIC_API_KEY_PRIMARY=\nANTHROPIC_API_KEY_SECONDARY=\n')
        add = next(c for c in self.calls() if c[:2] == ['provider', 'add'])
        self.assertIn('${ANTHROPIC_API_KEY_PRIMARY}', add)
        self.assertIn('--default-model', add)
        self.assertEqual(add[add.index('--default-model') + 1], 'claude-fable-5-2')
        dropin = self.home / '.config/systemd/user/opencodex-proxy.service.d/override.conf'
        self.assertEqual(dropin.read_text(), '[Service]\nEnvironmentFile=%h/.config/opencodex/keys.env\n')
        profile = (self.home / '.codex/orch.config.toml').read_text()
        self.assertIn('model = "anthropic-apikey/claude-fable-5-2"', profile)
        self.assertIn('model_reasoning_effort = "high"', profile)
        self.assertIn('sandbox_mode = "workspace-write"', profile)
        self.assertEqual((self.conf / 'codex-profile').read_text(), 'orch\n')
        self.assertFalse((self.home / '.bashrc').exists())
        self.assertIn('[todo] shell env', out)  # shell.sh not generated in this fixture
        self.assertIn(['integration', 'native', 'claude', 'off'], self.calls())
        self.assertIn('[ok] service env', out)
        self.assertIn('[ok] model discovery', out)
        self.assertIn('[todo] sandbox', out)
        self.assertNotIn(FAKE_KEY, out)
        # Filled values stay private: a second run reads names only and changes nothing.
        keys.write_text('ANTHROPIC_API_KEY_PRIMARY=' + FAKE_KEY + '\nANTHROPIC_API_KEY_SECONDARY=' + FAKE_KEY + '\n')
        before = {p: p.read_text() for p in (dropin, self.home / '.codex/orch.config.toml', self.conf / 'codex-profile')}
        out = self.run_tool('--yes')
        self.assertIn('0 changed', out)
        self.assertNotIn(FAKE_KEY, out)
        self.assertNotIn(FAKE_KEY, json.dumps(self.calls()))
        self.assertEqual(before, {p: p.read_text() for p in before})

    def test_profile_merge_keeps_codex_additions_and_rejects_export_prefix(self):
        self.start_health()
        codex = self.home / '.codex'
        codex.mkdir()
        (codex / 'orch.config.toml').write_text('sandbox_mode = "read-only"\n\n[projects."/x"]\ntrust_level = "trusted"\n')
        (self.home / '.config/opencodex').mkdir(parents=True)
        (self.home / '.config/opencodex/keys.env').write_text('export ANTHROPIC_API_KEY_PRIMARY=\nexport ANTHROPIC_API_KEY_SECONDARY=\n')
        out = self.run_tool('--yes')
        self.assertIn('[warn] codex profile', out)
        self.assertIn('removed `export`', out)
        self.assertEqual((self.home / '.config/opencodex/keys.env').read_text(), 'ANTHROPIC_API_KEY_PRIMARY=\nANTHROPIC_API_KEY_SECONDARY=\n')
        self.run_tool('--yes', '--force')
        text = (codex / 'orch.config.toml').read_text()
        self.assertIn('sandbox_mode = "workspace-write"', text)
        self.assertIn('[projects."/x"]', text)
        self.assertIn('model = "anthropic-apikey/claude-fable-5-2"', text.split('[projects')[0])

    def test_model_choice_is_asked_only_interactively_and_flows_into_provider_and_profile(self):
        self.start_health()
        out = self.run_tool('--model', 'claude-opus-5-5', '--effort', 'medium')
        self.assertIn('default model: anthropic-apikey/claude-opus-5-5, effort medium', out)
        add = next(c for c in self.calls() if c[:2] == ['provider', 'add'])
        self.assertEqual(add[add.index('--default-model') + 1], 'claude-opus-5-5')
        profile = (self.home / '.codex/orch.config.toml').read_text()
        self.assertIn('model = "anthropic-apikey/claude-opus-5-5"', profile)
        self.assertIn('model_reasoning_effort = "medium"', profile)
        # Non-interactive stdin: no prompts, first choice and high are the defaults.
        out = self.run_tool('--check')
        self.assertIn('default model: anthropic-apikey/claude-fable-5-2, effort high', out)
        self.assertNotIn('Choose [', out)
        self.assertNotIn('Reasoning effort [', out)

    def test_refuses_the_shared_anthropic_api_key_name(self):
        out = self.run_tool('--check', '--key-vars', 'ANTHROPIC_API_KEY', code=2)
        self.assertIn('ANTHROPIC_API_KEY', out)


class ShellProfileExportTests(unittest.TestCase):
    def test_shell_sh_exports_the_recorded_profile_only_when_present(self):
        with tempfile.TemporaryDirectory(prefix='shell-profile-') as tmp:
            root = Path(tmp)
            home = root / 'home'
            home.mkdir()
            conf = home / '.config/local-worker'
            env = {k: v for k, v in os.environ.items() if not k.startswith(('LLM_', 'ANTHROPIC_', 'CODEX_'))}
            env.update(HOME=str(home), PATH=os.defpath, LLM_WORKER_CONF_DIR=str(conf), PYTHONDONTWRITEBYTECODE='1')
            result = subprocess.run([str(KIT / 'install.sh'), '--install-only', '--setup-path', '--prefix', str(root / 'bin')],
                                    env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            shell = conf / 'shell.sh'
            probe = ['bash', '--noprofile', '--norc', '-c', '. "$1"; printf "%s" "${LLM_CODEX_PROFILE-unset}"', 'probe', str(shell)]
            self.assertEqual(subprocess.run(probe, env=env, capture_output=True, text=True, timeout=15).stdout, 'unset')
            (conf / 'codex-profile').write_text('orch\n')
            self.assertEqual(subprocess.run(probe, env=env, capture_output=True, text=True, timeout=15).stdout, 'orch')


class CodexMainProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='codex-main-profile-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / 'mockbin'
        self.bin.mkdir()
        mock(self.bin / 'codex', CODEX)
        conf = self.root / 'conf'
        conf.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('LLM_', 'ANTHROPIC_', 'CODEX_'))}
        self.env.update(HOME=str(self.root), PATH=str(self.bin) + os.pathsep + os.defpath, LLM_WORKER_CONF_DIR=str(conf),
                        LLM_WORKER_KIT=str(KIT), PYTHONDONTWRITEBYTECODE='1', MOCK_CODEX_ARGS=str(self.root / 'args.json'))

    def args(self, *extra, profile=None):
        env = dict(self.env)
        if profile:
            env['LLM_CODEX_PROFILE'] = profile
        result = subprocess.run([str(KIT / 'bin/codex-main'), *extra], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((self.root / 'args.json').read_text())

    def test_profile_variable_adds_the_flag_once_before_managed_options(self):
        args = self.args(profile='orch')
        self.assertEqual(args[:2], ['-p', 'orch'])
        self.assertEqual(args.count('-p'), 1)
        self.assertNotIn('-p', self.args())
        caller = self.args('-p', 'other', profile='orch')
        self.assertEqual(caller.count('-p'), 1)
        self.assertEqual(caller[caller.index('-p') + 1], 'other')
        prompt = self.args('--', '-p', 'orch', profile='orch')
        self.assertEqual(prompt[:2], ['-p', 'orch'])
        self.assertEqual(prompt[-3:], ['--', '-p', 'orch'])


if __name__ == '__main__':
    unittest.main()
