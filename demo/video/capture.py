#!/usr/bin/env python3
"""Capture a real, isolated iOS/pi demo. Requires an installed simulator and Tuist.

python3 demo/video/capture.py --source ~/Developer/patchbay-go --device <UDID>
All subprocesses and simulator recording are owned and stopped by this script.
"""
import argparse
import hashlib
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
PROMPTS = [
    'Read src/worker.js. In this repository, what does the raw route refuse, and how does a valid link open its app? Keep it to two short sentences.',
    'Save those rules as a concise contributor note called raw-route.md. Include the rejection status code and the redirect mechanism. Keep your spoken reply to one sentence.',
]


def command(args, cwd=ROOT, env=None, log=None):
    if log is not None and 'build-for-testing' in args:
        process = subprocess.Popen(args, cwd=cwd, env=env, text=True, stdout=log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 300
        succeeded_at = None
        while process.poll() is None:
            content = Path(log.name).read_text()
            if 'Test Build Succeeded' in content:
                succeeded_at = succeeded_at or time.monotonic()
                if time.monotonic() - succeeded_at > 15:
                    stop_tree(process)
                    return subprocess.CompletedProcess(args, 0)
            if time.monotonic() > deadline:
                stop_tree(process)
                raise RuntimeError('Build exceeded capture deadline; inspect build.log')
            time.sleep(1)
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, args)
        return subprocess.CompletedProcess(args, 0)
    return subprocess.run(args, cwd=cwd, env=env, check=True, text=True,
                          stdout=log or subprocess.PIPE, stderr=subprocess.STDOUT)



def stop_tree(process):
    """Tuist can detach xcodebuild; terminate its observed descendants too."""
    rows = subprocess.check_output(['ps', '-axo', 'pid=,ppid='], text=True).splitlines()
    pairs = [tuple(map(int, row.split())) for row in rows]
    owned = {process.pid}
    while True:
        expanded = owned | {pid for pid, parent in pairs if parent in owned}
        if expanded == owned:
            break
        owned = expanded
    for pid in reversed(sorted(owned)):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    time.sleep(2)
    for pid in owned:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--device', required=True)
    parser.add_argument('--developer-dir', default='/Applications/Xcode-beta.app/Contents/Developer')
    parser.add_argument('--run', default=time.strftime('%Y%m%d-%H%M%S'))
    parser.add_argument('--port', type=int, default=31560)
    args = parser.parse_args()
    lock = open('/tmp/pbv-video-capture.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Another capture owns the simulator/configuration')
    run = ROOT / 'demo/video/runs' / args.run
    run.mkdir(parents=True, exist_ok=False)
    project = run / 'projects/patchbay-go'
    project.mkdir(parents=True)
    files = ['README.md', 'src/worker.js', 'src/worker.test.js']
    hashes = {}
    for name in files:
        dest = project / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.source / name, dest)
        hashes[name] = hashlib.sha256(dest.read_bytes()).hexdigest()
    for cmd in [['init', '-b', 'develop'], ['config', 'user.name', 'Patchbay Demo'],
                ['config', 'user.email', 'demo@example.invalid'], ['add', '.'],
                ['commit', '-m', 'Seed isolated demo source'], ['branch', 'patchbay']]:
        command(['git', *cmd], cwd=project)
    remote = run / 'notes-remote.git'
    command(['git', 'init', '--bare', str(remote)])
    command(['git', 'remote', 'add', 'origin', str(remote)], cwd=project)
    # Existing notes branch means the first read-only turn can push the unchanged ref.
    command(['git', 'push', 'origin', 'patchbay'], cwd=project)
    (run / 'pi-sessions').mkdir()
    manifest = {'source_revision': command(['git', 'rev-parse', 'HEAD'], cwd=args.source).stdout.strip(),
                'voice_revision': command(['git', 'rev-parse', 'HEAD']).stdout.strip(),
                'source_hashes': hashes, 'prompts': PROMPTS, 'model': 'litellm/small',
                'input': 'typed in the real iOS simulator', 'audio': 'server say; final review videos muted',
                'remote': 'isolated local bare git repository', 'device': args.device}
    manifest_path = run / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2))
    server_env = {**os.environ, 'DEVELOPER_DIR': str(run / 'projects'),
                  'CHATS_FILE': str(run / 'chats.json'), 'VIDEO_RUN_DIR': str(run),
                  'VOICE_FORCE_MODEL': 'small', 'PYTHONUNBUFFERED': '1'}
    apple_env = {**os.environ, 'DEVELOPER_DIR': args.developer_dir}
    config = Path('/tmp/pbv-video-config.json')
    previous = config.read_bytes() if config.exists() else None
    base = f'http://127.0.0.1:{args.port}'
    server = recorder = None
    try:
        with (run / 'server.log').open('w') as log:
            server = subprocess.Popen([str(ROOT / 'server/.venv/bin/python'), '-m', 'uvicorn',
                                       'capture_server:app', '--app-dir', str(ROOT / 'demo/video'),
                                       '--host', '127.0.0.1', '--port', str(args.port)],
                                      env=server_env, stdout=log, stderr=subprocess.STDOUT)
        for _ in range(100):
            try:
                urllib.request.urlopen(base + '/api/chats', timeout=1).close()
                break
            except OSError:
                if server.poll() is not None:
                    raise RuntimeError('Capture server exited; inspect server.log')
                time.sleep(.1)
        request = urllib.request.Request(base + '/api/chats', data=b'{"project_dir":"patchbay-go"}',
                                         headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(request, timeout=10).close()
        config.write_text(json.dumps({'serverURL': base, 'output': str(run), 'prompts': PROMPTS}))
        with (run / 'build.log').open('w') as log:
            command(['tuist', 'generate', '--no-open'], cwd=ROOT / 'ios', env=apple_env, log=log)
            command(['tuist', 'xcodebuild', 'build-for-testing', '-workspace', 'ios/PatchbayVoice.xcworkspace',
                     '-scheme', 'PatchbayVoice', '-destination', f'platform=iOS Simulator,id={args.device}',
                     '-derivedDataPath', '/tmp/pbv-video-build'], env=apple_env, log=log)
        manifest['recording_started_at'] = time.time()
        manifest_path.write_text(json.dumps(manifest, indent=2))
        with (run / 'recording.log').open('w') as log:
            recorder = subprocess.Popen(['xcrun', 'simctl', 'io', args.device, 'recordVideo', '--codec=h264',
                                         str(run / 'simulator.mp4')], env=apple_env, stdout=log, stderr=log)
        with (run / 'test.log').open('w') as log:
            test = subprocess.Popen(['tuist', 'xcodebuild', 'test-without-building', '-workspace', 'ios/PatchbayVoice.xcworkspace',
                     '-scheme', 'PatchbayVoice', '-destination', f'platform=iOS Simulator,id={args.device}',
                     '-derivedDataPath', '/tmp/pbv-video-build',
                     '-only-testing:PatchbayVoiceUITests/VideoCaptureTests/testRecordRealConversation',
                     '-parallel-testing-enabled', 'NO'], cwd=ROOT, env=apple_env, stdout=log,
                     stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic() + 420
            try:
                while test.poll() is None and not (run / 'capture-complete').exists():
                    if 'with 1 failure' in (run / 'test.log').read_text():
                        raise RuntimeError('UI capture failed; inspect test.log')
                    if time.monotonic() > deadline:
                        raise RuntimeError('Capture timed out; inspect test.log')
                    time.sleep(1)
                if not (run / 'capture-complete').exists():
                    raise RuntimeError('UI capture did not complete')
                try:
                    test.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    manifest['test_teardown'] = 'UI capture completed; toolchain teardown exceeded grace period'
            finally:
                if test.poll() is None:
                    stop_tree(test)
        responses = [json.loads((run / f'response-{i}.json').read_text()) for i in range(2)]
        if any(r.get('failed') for r in responses):
            raise RuntimeError('Failed response; capture is not valid')
        note = project / 'docs/patchbay/raw-route.md'
        if not note.exists():
            raise RuntimeError('No note was written')
        local_ref = command(['git', 'rev-parse', 'patchbay'], cwd=project).stdout.strip()
        remote_ref = command(['git', '--git-dir', str(remote), 'rev-parse', 'patchbay']).stdout.strip()
        if local_ref != remote_ref:
            raise RuntimeError('Local and pushed notes refs differ')
        branch = command(['git', 'branch', '--show-current'], cwd=project).stdout.strip()
        if branch != 'develop':
            raise RuntimeError('Working branch changed')
        for name, expected_hash in hashes.items():
            if hashlib.sha256((project / name).read_bytes()).hexdigest() != expected_hash:
                raise RuntimeError(f'Source file changed: {name}')
        command(['git', 'diff', '--cached', '--exit-code'], cwd=project)
        manifest['working_branch'] = branch
        manifest['source_unchanged'] = True
        manifest['notes_commit'] = local_ref
        manifest['note_sha256'] = hashlib.sha256(note.read_bytes()).hexdigest()
        manifest['verified'] = True
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(run, flush=True)
    finally:
        if recorder and recorder.poll() is None:
            recorder.send_signal(signal.SIGINT)
            recorder.wait(timeout=20)
        if server and server.poll() is None:
            server.terminate()
            server.wait(timeout=20)
        if previous is None:
            config.unlink(missing_ok=True)
        else:
            config.write_bytes(previous)


if __name__ == '__main__':
    main()
