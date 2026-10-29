import json
from types import SimpleNamespace

import pytest

from fec.speech import classify_member_longform_two_passes_local as T2


def envelope(result='{"identity_sequence":"NEUTRAL","turns":[]}', *, stop_reason="end_turn", is_error=False):
    return json.dumps({"type": "result", "is_error": is_error, "result": result, "stop_reason": stop_reason,
                       "session_id": "s1", "usage": {"output_tokens": 50, "output_tokens_details": {"thinking_tokens": 20}},
                       "modelUsage": {"claude-haiku-5-5": {}}})


def generator(calls, *, stdout=None, returncode=0):
    def run(args, **kwargs):
        calls.append({"args": args, **kwargs})
        return SimpleNamespace(returncode=returncode, stdout=stdout if stdout is not None else envelope(), stderr="boom")
    return T2.CliGenerator(run=run)


@pytest.fixture(autouse=True)
def scratch(tmp_path, monkeypatch):
    monkeypatch.setattr(T2, "CLI_CWD", tmp_path / "cli_cwd")


def test_clean_finish_returns_result_and_usage_with_stripped_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-x")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok")
    calls = []
    raw, tokens = generator(calls).generate("PROMPT")
    (call,) = calls
    assert raw.startswith("{") and tokens["output"] == 50 and tokens["thinking"] == 20 and tokens["output_complete"] is True
    assert call["input"] == "PROMPT" and call["timeout"] == 600
    assert "ANTHROPIC_API_KEY" not in call["env"] and "ANTHROPIC_AUTH_TOKEN" not in call["env"]
    assert call["env"]["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "32000"
    assert "--bare" not in call["args"] and call["args"][call["args"].index("--effort") + 1] == "low"
    assert not any(ch in arg for arg in call["args"] for ch in "%&^|<>")  # cmd.exe shim hazards
    assert "creationflags" in call


@pytest.mark.parametrize("kwargs", [{"stdout": envelope(stop_reason="max_tokens")},
                                    {"stdout": envelope(stop_reason=None)},
                                    {"stdout": envelope(is_error=True, stop_reason="end_turn")},
                                    {"returncode": 1}])
def test_unclean_finish_raises(kwargs):
    with pytest.raises(RuntimeError):
        generator([], **kwargs).generate("PROMPT")


def test_fenced_json_parses():
    raw, _ = generator([], stdout=envelope('```json\n{"identity_sequence":"NEUTRAL","turns":[]}\n```')).generate("P")
    assert T2.physical.parse_json(raw) == {"identity_sequence": "NEUTRAL", "turns": []}


def test_runtime_has_no_cli_version_and_marks_passes_not_independent():
    runtime = generator([]).runtime
    assert runtime["backend"] == "claude_cli_subscription" and runtime["model_id"] == "claude-haiku-5-5"
    assert runtime["same_model_passes"] is True and runtime["passes_independent"] is False
    assert "version" not in json.dumps(runtime).lower()


def test_effort_flag_reaches_command_and_tokens_but_not_runtime():
    calls = []
    gen = T2.CliGenerator(run=lambda args, **kw: (calls.append(args), SimpleNamespace(returncode=0, stdout=envelope(), stderr=""))[1],
                          effort="medium")
    _, tokens = gen.generate("P")
    assert calls[0][calls[0].index("--effort") + 1] == "medium" and tokens["cli_effort"] == "medium"
    assert "--effort" not in gen.runtime["cli_flags"] and "medium" not in json.dumps(gen.runtime)
    assert gen.runtime == T2.CliGenerator(effort="low").runtime  # resume survives an effort change


def run_main(monkeypatch, tmp_path, *flags):
    requests = []

    class Fake:
        runtime = {"backend": "fake"}

        def __init__(self, effort="low"):
            pass

        def generate(self, request):
            requests.append(request)
            return '{"identity_sequence":"NEUTRAL","turns":[]}', {"output_complete": True}

    source = {"member": "M", "source_id": "s", "wav_sha256": "w", "transcript_sha256": "t"}
    words = [{"word": "hello", "start_sec": 0.0, "end_sec": 0.5}]
    monkeypatch.setattr(T2, "CliGenerator", Fake)
    monkeypatch.setattr(T2.SMR, "read_jsonl", lambda *a, **k: [source])
    monkeypatch.setattr(T2.physical, "validate_source", lambda s: (words, None))
    monkeypatch.setattr("sys.argv", ["x", "--input", "i", "--out-root", str(tmp_path), "--backend", "cli", *flags])
    assert T2.main() == 0
    return requests, [json.loads((tmp_path / f"pass-{p}.json").read_text(encoding="utf-8")) for p in "ab"]


def test_same_prompt_flag_sends_pass_b_prompt_in_both_sessions_and_records_it(monkeypatch, tmp_path):
    (a_req, b_req), (a, b) = run_main(monkeypatch, tmp_path, "--same-prompt-both-passes")
    assert a_req == b_req and "Identify the host's questions" in a_req
    assert a["request_sha256"] == b["request_sha256"] and a["pass_label"] == "a" and b["pass_label"] == "b"
    assert a["prompt_focus"] == b["prompt_focus"] == "b"
    assert a["runtime"]["same_prompt_both_passes"] is True


def test_default_keeps_distinct_pass_prompts(monkeypatch, tmp_path):
    (a_req, b_req), (a, b) = run_main(monkeypatch, tmp_path)
    assert a_req != b_req and (a["prompt_focus"], b["prompt_focus"]) == ("a", "b")
    assert "same_prompt_both_passes" not in a["runtime"]
