"""Structural checks for the n8n workflow files (they are also tested live in n8n; see docs/n8n.md)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

N8N = Path(__file__).resolve().parent.parent / "n8n"
FILES = ["fanoos-workflow.json", "fanoos-telegram-workflow.optional.json"]


def load(name: str) -> dict:
    return json.loads((N8N / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", FILES)
def test_workflow_is_importable_shape(name: str) -> None:
    wf = load(name)
    assert wf["id"] and wf["name"] and wf["active"] is False
    names = [n["name"] for n in wf["nodes"]]
    assert len(names) == len(set(names))
    assert len({n["id"] for n in wf["nodes"]}) == len(wf["nodes"])
    for node in wf["nodes"]:
        assert node["type"].startswith("n8n-nodes-base.") and isinstance(node["typeVersion"], (int, float))
        assert len(node["position"]) == 2
    for source, outputs in wf["connections"].items():
        assert source in names
        for branch in outputs["main"]:
            for link in branch:
                assert link["node"] in names


@pytest.mark.parametrize("name", FILES)
def test_no_secrets_or_credentials(name: str) -> None:
    text = (N8N / name).read_text(encoding="utf-8")
    for marker in ("xai-", "AIza", "gsk_", "bot_token", "accessToken"):
        assert marker not in text
    for node in load(name)["nodes"]:
        for cred in (node.get("credentials") or {}).values():
            assert cred["id"] == ""


def test_main_workflow_chain() -> None:
    wf = load("fanoos-workflow.json")
    nodes = {n["name"]: n for n in wf["nodes"]}
    hook = nodes["Webhook"]["parameters"]
    assert hook["httpMethod"] == "POST" and hook["path"] == "fanoos-review" and hook["responseMode"] == "responseNode"
    http = nodes["Fanoos review"]["parameters"]
    assert http["url"] == "http://localhost:8000/api/review" and http["method"] == "POST"
    assert "$json.body.url" in http["jsonBody"]
    assert nodes["Respond to Webhook"]["type"] == "n8n-nodes-base.respondToWebhook"
    assert wf["connections"]["Webhook"]["main"][0][0]["node"] == "Fanoos review"
    assert wf["connections"]["Fanoos review"]["main"][0][0]["node"] == "Respond to Webhook"


def test_telegram_workflow_branches() -> None:
    wf = load("fanoos-telegram-workflow.optional.json")
    true_branch, false_branch = wf["connections"]["Has a link?"]["main"]
    assert true_branch[0]["node"] == "Tell user we're reviewing"
    assert false_branch[0]["node"] == "Ask for a link"
