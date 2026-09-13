"""Offline contract tests: grading must fail closed and replay must stay isolated."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_incomplete_or_non_boolean_judgment_cannot_pass():
    from eval_runner import validate_judgment

    criteria = {"grounding": "Use repository evidence", "subject": "Answer about the repo"}
    for payload in [
        {},
        {"criteria": [{"id": "grounding", "passed": True, "reason": "ok"}]},
        {"criteria": [
            {"id": "grounding", "passed": "true", "reason": "ok"},
            {"id": "subject", "passed": True, "reason": "ok"},
        ]},
        {"criteria": [
            {"id": "grounding", "passed": True, "reason": "ok"},
            {"id": "grounding", "passed": True, "reason": "ok"},
        ]},
    ]:
        with pytest.raises(ValueError):
            validate_judgment(json.dumps(payload), criteria)


def test_one_failed_criterion_fails_whole_case():
    from eval_runner import validate_judgment

    result = validate_judgment(json.dumps({"criteria": [
        {"id": "subject", "passed": False, "reason": "Describes the agent instead"},
        {"id": "brief", "passed": True, "reason": "Two sentences"},
    ]}), {"subject": "Answer about repo", "brief": "Be brief"})
    assert result["passed"] is False


def test_complete_ndjson_judgment_is_validated_without_discarding_failures():
    from eval_runner import validate_judgment

    text = ('{"id":"subject","passed":true,"reason":"Read README"}\n'
            '{"id":"brief","passed":false,"reason":"Long answer"}')
    result = validate_judgment(text, {"subject": "Answer about repo", "brief": "Be brief"})
    assert result["passed"] is False
    assert len(result["criteria"]) == 2
    with pytest.raises(ValueError):
        validate_judgment(text + '\nExtra explanation', {"subject": "repo", "brief": "brief"})


def test_comma_separated_criteria_are_normalized_but_extra_fields_are_rejected():
    from eval_runner import validate_judgment

    text = ('{"id":"subject","passed":true,"reason":"Read README"},\n'
            '{"id":"brief","passed":false,"reason":"Long answer"}')
    assert validate_judgment(text, {"subject": "repo", "brief": "brief"})["passed"] is False
    with pytest.raises(ValueError):
        validate_judgment('{"criteria":[{"id":"subject","passed":true,"reason":"ok","bonus":1}]}',
                          {"subject": "repo"})


@pytest.mark.parametrize("mode,extra,exit_code,status", [
    ("pass", [], 0, "passed"), ("fail", [], 1, "failed"),
    ("invalid", [], 2, "error"), ("crash", [], 2, "error"),
    ("pass", ["--calibrate"], 0, "passed"),
    ("missing_note", ["--case", "003-short-speech-detailed-note"], 1, "failed"),
    ("pass", ["--all"], 0, "passed"),
    ("provider_error", [], 2, "error"),
    ("always_fail", ["--calibrate"], 2, "error"),
])
def test_cli_uses_production_path_without_leaking_gold_or_touching_chats(tmp_path, mode, extra, exit_code, status):
    # Substitute only the external pi process. The real run_pi, response
    # extraction, report writing, CLI exit handling and grading all execute.
    fake = tmp_path / "pi"
    fake.write_text("#!/usr/bin/env python3\n" + r'''
import json, os, pathlib, sys
args = sys.argv[1:]
if args == ['--version']:
    print('test-pi'); sys.exit(0)
prompt = args[-1]
judge = '--system-prompt' in args
if judge:
    assert '--no-tools' in args and '--no-context-files' in args
    payload = json.loads(sys.stdin.read())
    ids = list(payload['criteria'])
    bad = "I can't actually open the pi documentation" in payload['candidate']['reply']
    answer = json.dumps({'criteria': [
        {'id': k, 'passed': os.environ['EVAL_FAKE_MODE'] not in ('fail', 'always_fail') and not bad, 'reason': 'test evidence'}
        for k in ids
    ]}) if os.environ['EVAL_FAKE_MODE'] != 'invalid' else '{}'
else:
    assert '--append-system-prompt' in args and '--extension' in args
    assert '--no-builtin-tools' in args and '--no-skills' in args
    assert '--session' not in args and '--session-dir' in args
    assert any(s in prompt for s in ['How are raw route', 'Walk me through', 'How do we block'])
    assert 'reference_answer' not in prompt and 'observed_failure' not in prompt
    assert set(p.name for p in pathlib.Path.cwd().iterdir()) == {'README.md'}
    assert 'What `/raw` refuses' in pathlib.Path('README.md').read_text()
    assert str(pathlib.Path.cwd()) != os.environ['REAL_PROJECT']
    if os.environ['EVAL_FAKE_MODE'] == 'crash': sys.exit(3)
    if 'save the full walkthrough' in prompt and os.environ['EVAL_FAKE_MODE'] != 'missing_note':
        note = pathlib.Path('docs/patchbay/note.md')
        note.parent.mkdir(parents=True)
        note.write_text('A contributor walkthrough.')
    print(json.dumps({'type': 'session', 'id': 'eval-only-session'}))
    print(json.dumps({'type': 'tool_execution_start', 'toolName': 'read_file', 'toolCallId': 'r1', 'args': {'path': 'README.md'}}))
    print(json.dumps({'type': 'tool_execution_end', 'toolName': 'read_file', 'toolCallId': 'r1', 'isError': False, 'result': {'content': [{'type': 'text', 'text': 'Repository content'}]}}))
    answer = 'The raw route rejects browser schemes with HTTP 400 to prevent open redirects. Valid links hand off to the native app with a fallback link.'
message = {'role': 'assistant', 'model': 'test-model', 'provider': 'test', 'content': [{'type': 'thinking', 'thinking': 'PRIVATE_REASONING'}, {'type': 'text', 'text': answer}]}
if judge and os.environ['EVAL_FAKE_MODE'] == 'provider_error':
    message.update({'stopReason': 'error', 'errorMessage': '429: unavailable test route', 'content': []})
print(json.dumps({'type': 'agent_end', 'messages': [message]}))
''')
    fake.chmod(0o755)
    chats = tmp_path / "personal-chats.json"
    chats.write_text('{"sentinel": "untouched"}')
    report = tmp_path / "report.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "server/eval_runner.py"), "--output", str(report), *extra],
        env={**os.environ, "PI_BIN": str(fake), "CHATS_FILE": str(chats),
             "EVAL_FAKE_MODE": mode, "REAL_PROJECT": str(ROOT.parent / "patchbay-go")},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == exit_code, result.stdout + result.stderr
    saved = json.loads(report.read_text())
    assert saved["status"] == status
    assert chats.read_text() == '{"sentinel": "untouched"}'
    assert "PRIVATE_REASONING" not in report.read_text()
    if "--all" in extra:
        assert len(saved["outputs"]) == 4
        assert all(r["status"] == "passed" for r in saved["outputs"].values())
        return
    if mode == "provider_error":
        assert "429: unavailable test route" in saved["error"]["message"]
    if mode not in ("crash", "always_fail"):
        assert saved["candidate"]["tool_trace"][0]["toolName"] == "read_file"
        assert saved["candidate"]["models"] == [{"provider": "test", "model": "test-model"}]
