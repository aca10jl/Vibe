"""LLM 客户端：模式选择与输出解析（不发真实请求）。"""
import pytest

from src.agent.llm import OfflineLLM, OpenAICompatLLM, extract_json, make_llm


def test_auto_mode_offline_without_env(tuner_cfg, monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert isinstance(make_llm(tuner_cfg), OfflineLLM)


def test_auto_mode_api_with_env(tuner_cfg, monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1")
    assert isinstance(make_llm(tuner_cfg), OpenAICompatLLM)


def test_api_mode_forced(tuner_cfg, monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = {**tuner_cfg, "llm": {**tuner_cfg["llm"], "mode": "api"}}
    assert isinstance(make_llm(cfg), OpenAICompatLLM)


def test_offline_mode_forced(tuner_cfg, monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1")
    cfg = {**tuner_cfg, "llm": {**tuner_cfg["llm"], "mode": "offline"}}
    assert isinstance(make_llm(cfg), OfflineLLM)


def test_extract_json_plain():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced_with_prose():
    text = '好的，分析如下：\n```json\n{"target_bucket": "B3_RENDER_GAP"}\n```\n'
    assert extract_json(text)["target_bucket"] == "B3_RENDER_GAP"


def test_extract_json_no_object_raises():
    with pytest.raises(ValueError):
        extract_json("没有任何结构化输出")


def test_evidence_blocks_respect_send_images(tuner_cfg, baseline_config):
    """send_images=false 时 DIAGNOSE 内容退化为纯文本，适配纯语言模型。"""
    from src.eval import harness
    from src.triage.bucketing import run_bucketing
    from src.triage.evidence import generate_evidence

    report = harness.run_eval(baseline_config, "mini")
    buckets = generate_evidence(report, run_bucketing(report, baseline_config),
                                max_per_bucket=1)
    api_cfg = {**tuner_cfg["llm"]["api"], "send_images": False}
    llm = OpenAICompatLLM(api_cfg)
    blocks = llm._evidence_blocks(buckets, max_per_bucket=1)
    assert blocks and all(b["type"] == "text" for b in blocks)

    llm_img = OpenAICompatLLM({**api_cfg, "send_images": True})
    blocks_img = llm_img._evidence_blocks(buckets, max_per_bucket=1)
    assert any(b["type"] == "image_url" for b in blocks_img)
    url = next(b for b in blocks_img if b["type"] == "image_url")["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")
