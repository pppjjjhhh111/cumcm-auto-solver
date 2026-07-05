import json

import app


def test_ui_hides_legacy_sample_artifacts(tmp_path) -> None:
    marker = "examples/" + "sample" + "_problem/problem.txt"
    legacy_log = tmp_path / "solver_state.json"
    fresh_log = tmp_path / "fresh_state.json"
    legacy_log.write_text(json.dumps({"problem_path": marker}), encoding="utf-8")
    fresh_log.write_text(json.dumps({"problem_path": "outputs/uploads/problem/problem.txt"}), encoding="utf-8")

    assert app.contains_legacy_sample_reference({"path": marker}) is True
    assert app.is_legacy_sample_artifact(legacy_log) is True
    assert app.is_legacy_sample_artifact(fresh_log) is False
    assert app.visible_artifact_files([legacy_log, fresh_log]) == [fresh_log]


def test_empty_state_does_not_read_fallback_logs(tmp_path, monkeypatch) -> None:
    fallback = tmp_path / "model_recommendations.json"
    fallback.write_text(json.dumps({"strategies": [{"task_id": "old"}]}), encoding="utf-8")
    monkeypatch.setattr(app, "LOGS_DIR", tmp_path)

    assert app.get_section({}, "candidate_strategies", "model_recommendations.json") == {}

