"""
Backward Compatibility Tests for Interest Definition Chatbot Feature

Validates that:
1. Topics without comprehensiveDescription still work with the relevance evaluator
2. Adding a description to an existing topic causes the evaluator to use it
3. Export/import handles mixed topics (some with descriptions, some without)

Requirements: 5.6
"""
import sys
import os
import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from fastapi.testclient import TestClient
from app.main import app
from app.utils.storage import (
    read_json_file, write_json_file,
    get_user_interest_topics, add_interest_topic,
)
from app.utils.security import create_access_token
from app.services.relevance_evaluator import RelevanceEvaluator

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_test_user(email="compat_test@example.com", user_id="compat-test-user-001"):
    users = read_json_file("users.json")
    users[email] = {"id": user_id, "email": email, "name": "Compat Test User", "password": "pw"}
    write_json_file("users.json", users)
    token = create_access_token(data={"sub": email}, expires_delta=timedelta(minutes=30))
    return token, user_id


def cleanup_test_data(user_id):
    data = read_json_file("interest_topics.json")
    if "topics" in data:
        data["topics"] = [t for t in data["topics"] if t.get("userId") != user_id]
        write_json_file("interest_topics.json", data)
    users = read_json_file("users.json")
    users = {k: v for k, v in users.items() if v.get("id") != user_id}
    write_json_file("users.json", users)


def make_capture_evaluator():
    """Return (evaluator, captured_prompts_list) with a mock Bedrock client."""
    evaluator = RelevanceEvaluator()
    captured = []

    def capture_invoke(*args, **kwargs):
        body = json.loads(kwargs.get("body", "{}"))
        msgs = body.get("messages", [])
        if msgs:
            captured.append(msgs[0]["content"])
        mock_resp = {"body": MagicMock()}
        mock_resp["body"].read.return_value = json.dumps({
            "content": [{"text": json.dumps({
                "isRelevant": True,
                "matchingTopics": ["test topic"],
                "confidence": 0.9
            })}]
        }).encode()
        return mock_resp

    evaluator.bedrock = MagicMock()
    evaluator.bedrock.invoke_model.side_effect = capture_invoke
    return evaluator, captured


# ---------------------------------------------------------------------------
# 1. Relevance evaluator uses topicText when no description exists
# ---------------------------------------------------------------------------

def test_evaluator_uses_topic_text_when_no_description():
    """
    A topic created without a comprehensiveDescription causes the evaluator
    to fall back to topicText.  Requirement 5.6.
    """
    print("\n=== Test: Evaluator falls back to topicText (no description) ===")

    evaluator, captured = make_capture_evaluator()

    topic_no_desc = {
        "id": "t-legacy-001",
        "userId": "user-x",
        "topicText": "signal integrity",
        "comprehensiveDescription": None,
        "conversationStatus": "not_started",
    }

    paper = {
        "id": "p-001",
        "title": "Signal Integrity in High-Speed PCB Design",
        "abstract": "Analysis of signal integrity issues in PCB traces.",
        "keywords": ["signal integrity", "PCB"],
    }

    evaluator.evaluate(paper, [topic_no_desc])

    assert len(captured) == 1, "Expected exactly one Bedrock call"
    prompt = captured[0]
    assert "signal integrity" in prompt.lower(), "topicText must appear in prompt"

    # Extract only the interest topics listing block — the lines between the
    # "User's Research Interest Topics:" header and the next blank line or
    # "Instructions:" section.  This avoids false positives from the prompt
    # template's own bullet-point rules section.
    lines = prompt.splitlines()
    in_topics_block = False
    topic_bullets = []
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("user's research interest topics:"):
            in_topics_block = True
            continue
        if in_topics_block:
            if stripped.lower().startswith("instructions:") or stripped.lower().startswith("rules:"):
                break
            if stripped.startswith("-"):
                topic_bullets.append(stripped)

    assert len(topic_bullets) == 1, (
        f"Expected exactly one topic bullet in the topics block, got: {topic_bullets}"
    )
    assert topic_bullets[0] == "- signal integrity", (
        f"Topic bullet should be simple topicText, got: {topic_bullets[0]}"
    )
    print("✓ Evaluator used topicText when comprehensiveDescription is None")


def test_evaluator_uses_topic_text_when_description_is_empty_string():
    """
    An empty-string comprehensiveDescription is treated the same as None —
    the evaluator falls back to topicText.  Requirement 5.6.
    """
    print("\n=== Test: Evaluator falls back to topicText (empty description) ===")

    evaluator, captured = make_capture_evaluator()

    topic_empty_desc = {
        "id": "t-legacy-002",
        "userId": "user-x",
        "topicText": "power integrity",
        "comprehensiveDescription": "",   # empty string
        "conversationStatus": "not_started",
    }

    paper = {
        "id": "p-002",
        "title": "Power Delivery Network Design",
        "abstract": "Methods for PDN design and decoupling.",
        "keywords": ["power integrity", "PDN"],
    }

    evaluator.evaluate(paper, [topic_empty_desc])

    assert len(captured) == 1
    prompt = captured[0]
    assert "power integrity" in prompt.lower()
    print("✓ Evaluator used topicText when comprehensiveDescription is empty string")


def test_evaluator_uses_topic_text_when_description_is_whitespace():
    """
    A whitespace-only comprehensiveDescription is treated as absent.
    Requirement 5.6.
    """
    print("\n=== Test: Evaluator falls back to topicText (whitespace description) ===")

    evaluator, captured = make_capture_evaluator()

    topic_ws_desc = {
        "id": "t-legacy-003",
        "userId": "user-x",
        "topicText": "EBG structures",
        "comprehensiveDescription": "   ",   # whitespace only
        "conversationStatus": "not_started",
    }

    paper = {
        "id": "p-003",
        "title": "Electromagnetic Bandgap Structures for EMI Suppression",
        "abstract": "EBG periodic structures for noise suppression.",
        "keywords": ["EBG", "EMI"],
    }

    evaluator.evaluate(paper, [topic_ws_desc])

    assert len(captured) == 1
    prompt = captured[0]
    assert "ebg structures" in prompt.lower()
    print("✓ Evaluator used topicText when comprehensiveDescription is whitespace")


# ---------------------------------------------------------------------------
# 2. Adding a description to an existing topic switches the evaluator
# ---------------------------------------------------------------------------

def test_evaluator_switches_to_description_after_it_is_added():
    """
    After saving a comprehensiveDescription to an existing topic, the evaluator
    must use the description instead of topicText.  Requirements 5.5, 5.6.
    """
    print("\n=== Test: Evaluator switches to description after it is added ===")

    token, user_id = setup_test_user("compat_switch@example.com", "compat-switch-001")

    try:
        # Create topic (no description yet)
        resp = client.post(
            "/api/user/interests",
            json={"topicText": "machine learning"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        topic_id = resp.json()["id"]

        # Verify topic has no description
        topics = client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"}).json()
        assert topics[0]["comprehensiveDescription"] is None
        print("✓ Topic created without description")

        # --- Phase 1: evaluator uses topicText ---
        evaluator_before, captured_before = make_capture_evaluator()
        paper = {
            "id": "p-ml-001",
            "title": "Gradient Descent Optimisation for Neural Networks",
            "abstract": "Study of gradient descent variants for training deep networks.",
            "keywords": ["machine learning", "neural networks"],
        }
        evaluator_before.evaluate(paper, topics)
        assert len(captured_before) == 1
        prompt_before = captured_before[0]
        assert "machine learning" in prompt_before.lower()
        print("✓ Phase 1: evaluator used topicText (no description)")

        # --- Add description via API ---
        description = (
            "Research on supervised machine learning algorithms, specifically gradient "
            "descent optimisation and neural network training. Focuses on convergence "
            "properties and computational efficiency. Excludes unsupervised methods."
        )
        resp = client.post(
            f"/api/user/interests/{topic_id}/description/save",
            json={"description": description},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["comprehensiveDescription"] == description
        print("✓ Description saved via API")

        # --- Phase 2: evaluator uses comprehensive description ---
        topics_after = client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"}).json()
        assert topics_after[0]["comprehensiveDescription"] == description

        evaluator_after, captured_after = make_capture_evaluator()
        evaluator_after.evaluate(paper, topics_after)
        assert len(captured_after) == 1
        prompt_after = captured_after[0]

        # Description-specific content must appear in the prompt
        assert "gradient descent" in prompt_after.lower() or "supervised" in prompt_after.lower()
        # The prompt must be richer than the simple-text prompt
        assert len(prompt_after) > len(prompt_before)
        # The two prompts must differ
        assert prompt_after != prompt_before
        print("✓ Phase 2: evaluator used comprehensiveDescription after it was added")

    finally:
        cleanup_test_data("compat-switch-001")


def test_topic_text_still_present_after_description_added():
    """
    After adding a comprehensiveDescription, the topicText field must still
    be stored and returned.  Requirement 5.2.
    """
    print("\n=== Test: topicText preserved after description is added ===")

    token, user_id = setup_test_user("compat_dual@example.com", "compat-dual-001")

    try:
        resp = client.post(
            "/api/user/interests",
            json={"topicText": "quantum computing"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        topic_id = resp.json()["id"]

        description = "Research on quantum algorithms for cryptography and optimisation."
        client.post(
            f"/api/user/interests/{topic_id}/description/save",
            json={"description": description},
            headers={"Authorization": f"Bearer {token}"},
        )

        topics = client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"}).json()
        topic = topics[0]

        assert topic["topicText"] == "quantum computing", "topicText must be preserved"
        assert topic["comprehensiveDescription"] == description, "description must be stored"
        print("✓ Both topicText and comprehensiveDescription are present after save")

    finally:
        cleanup_test_data("compat-dual-001")


# ---------------------------------------------------------------------------
# 3. Export/import with mixed topics (some with descriptions, some without)
# ---------------------------------------------------------------------------

def test_export_mixed_topics_includes_description_field():
    """
    Exporting a mix of topics (some with descriptions, some without) must
    include the comprehensiveDescription field for all topics.
    Requirements 10.1, 10.2.
    """
    print("\n=== Test: Export mixed topics includes comprehensiveDescription field ===")

    token, user_id = setup_test_user("compat_export@example.com", "compat-export-001")

    try:
        # Topic 1: no description (legacy)
        resp = client.post(
            "/api/user/interests",
            json={"topicText": "signal integrity"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        topic1_id = resp.json()["id"]

        # Topic 2: with description (new)
        resp = client.post(
            "/api/user/interests",
            json={"topicText": "power integrity"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        topic2_id = resp.json()["id"]
        description2 = "Research on power delivery networks and decoupling capacitor placement."
        client.post(
            f"/api/user/interests/{topic2_id}/description/save",
            json={"description": description2},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Export
        resp = client.post(
            "/api/user/interests/export",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        export_data = resp.json()

        assert export_data["topicCount"] == 2
        exported_topics = export_data["topics"]
        assert len(exported_topics) == 2

        # Both topics must have the comprehensiveDescription key
        for t in exported_topics:
            assert "comprehensiveDescription" in t, f"Missing comprehensiveDescription in {t['topicText']}"

        # Topic without description → field is None
        t1 = next(t for t in exported_topics if t["topicText"] == "signal integrity")
        assert t1["comprehensiveDescription"] is None
        print("✓ Topic without description exports with comprehensiveDescription=None")

        # Topic with description → field has the value
        t2 = next(t for t in exported_topics if t["topicText"] == "power integrity")
        assert t2["comprehensiveDescription"] == description2
        print("✓ Topic with description exports with correct comprehensiveDescription")

        # conversationHistory must NOT be exported
        for t in exported_topics:
            assert "conversationHistory" not in t, "conversationHistory must not be exported"
        print("✓ conversationHistory excluded from export")

    finally:
        cleanup_test_data("compat-export-001")


def test_import_mixed_topics_restores_descriptions():
    """
    Importing a file with mixed topics (some with descriptions, some without)
    correctly restores descriptions only where present.
    Requirements 10.3, 10.4.
    """
    print("\n=== Test: Import mixed topics restores descriptions correctly ===")

    token, user_id = setup_test_user("compat_import@example.com", "compat-import-001")

    try:
        import_data = {
            "exportedAt": "2024-01-01T00:00:00Z",
            "userId": "some-other-user",
            "topicCount": 3,
            "topics": [
                # Legacy topic: no comprehensiveDescription field at all
                {"topicText": "signal integrity"},
                # New topic: has description
                {
                    "topicText": "power integrity",
                    "comprehensiveDescription": "Research on PDN design and decoupling.",
                    "conversationStatus": "completed",
                },
                # New topic: explicit None description
                {
                    "topicText": "EBG structures",
                    "comprehensiveDescription": None,
                    "conversationStatus": "not_started",
                },
            ],
        }

        file_content = json.dumps(import_data).encode()
        files = {"file": ("topics.json", BytesIO(file_content), "application/json")}

        resp = client.post(
            "/api/user/interests/import",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result["results"]["added"] == 3
        print("✓ All 3 mixed topics imported successfully")

        # Verify stored state
        topics = client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"}).json()
        assert len(topics) == 3

        by_text = {t["topicText"]: t for t in topics}

        # Legacy topic: description must be None
        assert by_text["signal integrity"]["comprehensiveDescription"] is None
        print("✓ Legacy topic (no description field) imported with comprehensiveDescription=None")

        # Topic with description: description must be restored
        assert by_text["power integrity"]["comprehensiveDescription"] == "Research on PDN design and decoupling."
        assert by_text["power integrity"]["conversationStatus"] == "completed"
        print("✓ Topic with description imported with correct comprehensiveDescription")

        # Topic with explicit None: description must be None
        assert by_text["EBG structures"]["comprehensiveDescription"] is None
        print("✓ Topic with explicit None description imported correctly")

    finally:
        cleanup_test_data("compat-import-001")


def test_export_import_roundtrip_mixed_topics():
    """
    Full roundtrip: export mixed topics, delete them, re-import, and verify
    the evaluator behaves correctly for each topic.
    Requirements 5.6, 10.1, 10.2, 10.3.
    """
    print("\n=== Test: Export/import roundtrip with mixed topics ===")

    token, user_id = setup_test_user("compat_roundtrip@example.com", "compat-roundtrip-001")

    try:
        # Create topic 1 (no description)
        resp = client.post(
            "/api/user/interests",
            json={"topicText": "signal integrity"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        t1_id = resp.json()["id"]

        # Create topic 2 (with description)
        resp = client.post(
            "/api/user/interests",
            json={"topicText": "machine learning"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        t2_id = resp.json()["id"]
        desc2 = (
            "Research on supervised learning algorithms, neural networks, and "
            "gradient-based optimisation. Excludes unsupervised and reinforcement learning."
        )
        client.post(
            f"/api/user/interests/{t2_id}/description/save",
            json={"description": desc2},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Export
        resp = client.post("/api/user/interests/export", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        export_data = resp.json()
        assert export_data["topicCount"] == 2

        # Delete all topics
        for t in client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"}).json():
            client.delete(f"/api/user/interests/{t['id']}", headers={"Authorization": f"Bearer {token}"})
        assert len(client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"}).json()) == 0
        print("✓ Topics deleted before re-import")

        # Re-import
        file_content = json.dumps(export_data).encode()
        files = {"file": ("topics.json", BytesIO(file_content), "application/json")}
        resp = client.post("/api/user/interests/import", files=files, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["results"]["added"] == 2
        print("✓ Topics re-imported successfully")

        # Verify restored state
        topics = client.get("/api/user/interests", headers={"Authorization": f"Bearer {token}"}).json()
        by_text = {t["topicText"]: t for t in topics}

        assert by_text["signal integrity"]["comprehensiveDescription"] is None
        assert by_text["machine learning"]["comprehensiveDescription"] == desc2
        print("✓ Descriptions correctly restored after roundtrip")

        # Verify evaluator behaviour after roundtrip
        paper = {
            "id": "p-rt-001",
            "title": "Neural Network Training with Adam Optimiser",
            "abstract": "Gradient-based optimisation for deep learning.",
            "keywords": ["machine learning", "neural networks"],
        }

        # Topic without description → uses topicText
        evaluator_si, captured_si = make_capture_evaluator()
        evaluator_si.evaluate(paper, [by_text["signal integrity"]])
        assert "signal integrity" in captured_si[0].lower()
        print("✓ After roundtrip: evaluator uses topicText for topic without description")

        # Topic with description → uses description
        evaluator_ml, captured_ml = make_capture_evaluator()
        evaluator_ml.evaluate(paper, [by_text["machine learning"]])
        assert "gradient" in captured_ml[0].lower() or "supervised" in captured_ml[0].lower()
        assert len(captured_ml[0]) > len(captured_si[0])
        print("✓ After roundtrip: evaluator uses comprehensiveDescription for topic with description")

    finally:
        cleanup_test_data("compat-roundtrip-001")


# ---------------------------------------------------------------------------
# 4. Storage layer backward compatibility (topics missing new fields)
# ---------------------------------------------------------------------------

def test_storage_backward_compat_missing_fields():
    """
    Topics stored without the new fields (comprehensiveDescription,
    conversationHistory, conversationStatus) are returned with safe defaults.
    Requirement 5.6.
    """
    print("\n=== Test: Storage backward compat — missing new fields ===")

    user_id = "compat-storage-legacy-001"

    # Directly write a legacy topic (no new fields) into storage
    data = read_json_file("interest_topics.json")
    if "topics" not in data:
        data["topics"] = []

    legacy_topic = {
        "id": "legacy-topic-001",
        "userId": user_id,
        "topicText": "legacy topic text",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z",
        # Intentionally omit: comprehensiveDescription, conversationHistory, conversationStatus
    }
    data["topics"].append(legacy_topic)
    write_json_file("interest_topics.json", data)

    try:
        from app.utils.storage import get_user_interest_topics, get_interest_topic_by_id

        topics = get_user_interest_topics(user_id)
        assert len(topics) == 1
        t = topics[0]

        assert t["comprehensiveDescription"] is None, "Missing field must default to None"
        assert t["conversationHistory"] is None, "Missing field must default to None"
        assert t["conversationStatus"] == "not_started", "Missing field must default to 'not_started'"
        print("✓ get_user_interest_topics fills in safe defaults for legacy topics")

        t_by_id = get_interest_topic_by_id("legacy-topic-001", user_id)
        assert t_by_id is not None
        assert t_by_id["comprehensiveDescription"] is None
        assert t_by_id["conversationStatus"] == "not_started"
        print("✓ get_interest_topic_by_id fills in safe defaults for legacy topics")

        # Evaluator must use topicText for this legacy topic
        evaluator, captured = make_capture_evaluator()
        paper = {
            "id": "p-legacy-001",
            "title": "A Paper About Legacy Topics",
            "abstract": "Abstract about legacy topic text.",
            "keywords": ["legacy"],
        }
        evaluator.evaluate(paper, topics)
        assert "legacy topic text" in captured[0].lower()
        print("✓ Evaluator uses topicText for legacy topic loaded from storage")

    finally:
        # Clean up the injected legacy topic
        data = read_json_file("interest_topics.json")
        data["topics"] = [t for t in data.get("topics", []) if t.get("userId") != user_id]
        write_json_file("interest_topics.json", data)


# ---------------------------------------------------------------------------
# 5. Evaluator handles mixed topic list (some with, some without descriptions)
# ---------------------------------------------------------------------------

def test_evaluator_mixed_topic_list():
    """
    When the evaluator receives a list containing both legacy topics (no
    description) and new topics (with description), each topic uses the
    correct text.  Requirement 5.6.
    """
    print("\n=== Test: Evaluator handles mixed topic list ===")

    evaluator, captured = make_capture_evaluator()

    topics = [
        {
            "id": "t-mix-1",
            "userId": "user-mix",
            "topicText": "signal integrity",
            "comprehensiveDescription": None,
        },
        {
            "id": "t-mix-2",
            "userId": "user-mix",
            "topicText": "machine learning",
            "comprehensiveDescription": (
                "Research on supervised learning algorithms and neural network "
                "training. Excludes unsupervised methods."
            ),
        },
        {
            "id": "t-mix-3",
            "userId": "user-mix",
            "topicText": "power integrity",
            "comprehensiveDescription": "",  # empty → falls back to topicText
        },
    ]

    paper = {
        "id": "p-mix-001",
        "title": "Mixed Topic Paper",
        "abstract": "A paper touching on multiple research areas.",
        "keywords": ["signal", "ML", "power"],
    }

    evaluator.evaluate(paper, topics)

    assert len(captured) == 1
    prompt = captured[0]

    # topicText for topic 1 (no description)
    assert "signal integrity" in prompt.lower()
    # comprehensiveDescription for topic 2
    assert "supervised learning" in prompt.lower() or "neural network" in prompt.lower()
    # topicText for topic 3 (empty description)
    assert "power integrity" in prompt.lower()

    print("✓ Mixed topic list: each topic uses the correct text in the prompt")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("Backward Compatibility Tests — Interest Definition Chatbot")
    print("=" * 70)

    # Relevance evaluator fallback
    test_evaluator_uses_topic_text_when_no_description()
    test_evaluator_uses_topic_text_when_description_is_empty_string()
    test_evaluator_uses_topic_text_when_description_is_whitespace()

    # Adding description to existing topic
    test_evaluator_switches_to_description_after_it_is_added()
    test_topic_text_still_present_after_description_added()

    # Export/import with mixed topics
    test_export_mixed_topics_includes_description_field()
    test_import_mixed_topics_restores_descriptions()
    test_export_import_roundtrip_mixed_topics()

    # Storage layer backward compat
    test_storage_backward_compat_missing_fields()

    # Evaluator with mixed list
    test_evaluator_mixed_topic_list()

    print("\n" + "=" * 70)
    print("All backward compatibility tests completed!")
    print("=" * 70)
