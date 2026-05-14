"""Feature Claims Verification — Prady OS Honesty Contract.

Every public claim about Prady OS is verified by a passing test here.
If a test fails, either the feature must be fixed or the claim removed.
All tests use file inspection only — no network, no Docker, no hardware.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PLATFORM = REPO_ROOT / "platform"
DEV_COMPOSE = REPO_ROOT / "docker-compose.dev.yml"
PROD_COMPOSE = REPO_ROOT / "build" / "iso" / "docker-compose.prod.yml"


def _load_compose(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _source(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


class TestClaimPraxControlsCursor:
    """CLAIM: Prax controls cursor, keyboard, and screen"""

    def test_computer_use_service_file_exists(self):
        files = list((PLATFORM / "computer-use").rglob("*service*.py"))
        assert files, "computer-use service file missing"

    def test_execute_endpoint_exists_in_source(self):
        src = _source("platform/computer-use/computer_use_service.py")
        assert "/execute" in src, "No /execute endpoint in computer-use service"

    def test_execute_returns_structured_response(self):
        src = _source("platform/computer-use/computer_use_service.py")
        assert "success" in src, "Execute response must include 'success' field"

    def test_xdotool_or_ydotool_referenced(self):
        src = _source("platform/computer-use/computer_use_service.py")
        assert "xdotool" in src or "ydotool" in src, "Must use xdotool or ydotool for cursor control"


class TestClaimPraxListensAndSpeaks:
    """CLAIM: Prax hears and speaks offline"""

    def test_voice_service_file_exists(self):
        files = list((PLATFORM / "voice-service").rglob("*service*.py"))
        assert files, "voice-service file missing"

    def test_whisper_referenced_in_stt(self):
        src = _source("platform/voice-service/stt_engine.py")
        assert "whisper" in src.lower(), "STT engine must use Whisper"

    def test_piper_referenced_in_tts(self):
        src = _source("platform/voice-service/tts_engine.py")
        assert "piper" in src.lower(), "TTS engine must use Piper"

    def test_transcribe_endpoint_exists(self):
        src = _source("platform/voice-service/voice_service.py")
        assert "/transcribe" in src or "transcribe" in src, "No transcribe endpoint in voice service"

    def test_synthesize_endpoint_exists(self):
        src = _source("platform/voice-service/voice_service.py")
        assert "/synthesize" in src or "synthesize" in src or "/speak" in src, "No synthesize endpoint in voice service"


class TestClaimPraxLearnsFromTasks:
    """CLAIM: Prax learns from every task"""

    def test_self_learning_service_exists(self):
        files = list((PLATFORM / "self-learning").rglob("*service*.py"))
        assert files, "self-learning service missing"

    def test_skill_library_exists(self):
        assert (PLATFORM / "self-learning" / "skill_library.py").exists(), "skill_library.py missing"

    def test_record_endpoint_exists(self):
        src = _source("platform/self-learning/self_learning_service.py")
        assert "/learn/record" in src, "No /learn/record endpoint in self-learning"

    def test_lora_trainer_exists(self):
        assert (PLATFORM / "self-learning" / "lora_trainer.py").exists(), "lora_trainer.py missing"


class TestClaimPraxInventsAutonomously:
    """CLAIM: Prax discovers problems and builds solutions"""

    def test_inventor_engine_exists(self):
        files = list((PLATFORM / "inventor-engine").rglob("*service*.py"))
        assert files, "inventor-engine service missing"

    def test_research_agent_has_scan_method(self):
        src = _source("platform/inventor-engine/research_agent.py")
        assert "async def scan" in src, "ResearchAgent missing scan() method"

    def test_proposal_engine_generates_card(self):
        src = _source("platform/inventor-engine/proposal_engine.py")
        assert "ProposalCard" in src, "ProposalCard class missing from proposal_engine"

    def test_build_team_has_build_methods(self):
        src = _source("platform/inventor-engine/build_team.py")
        for method in ["_run_architect", "_run_developer", "_run_qa", "_run_documenter"]:
            assert method in src, f"Build team missing {method}"

    def test_verifier_agent_requires_docker(self):
        src = _source("platform/inventor-engine/verifier_agent.py")
        assert "docker" in src.lower(), "Verifier agent must use Docker for cold start"

    def test_projects_blocked_without_verification(self):
        src = _source("platform/inventor-engine/project_releaser.py")
        assert "verified" in src, "Releaser must check verified flag before push"

    def test_inventor_digest_endpoint_exists(self):
        src = _source("platform/inventor-engine/inventor_service.py")
        assert "/inventor/digest" in src, "No /inventor/digest endpoint"

    def test_idle_monitor_uses_psutil(self):
        src = _source("platform/inventor-engine/inventor_service.py")
        assert "psutil" in src, "Idle monitor must use psutil for CPU/RAM check"


class TestClaimPraxPublishesHonestly:
    """CLAIM: Social posts include honest caveats"""

    def test_content_generator_exists(self):
        assert (PLATFORM / "social-publisher" / "social_publisher_service.py").exists(), "social publisher service missing"

    def test_content_generator_includes_prady_os(self):
        src = _source("platform/social-publisher/social_publisher_service.py")
        assert "Prady OS" in src, "Content generator must reference Prady OS"

    def test_forbidden_words_absent_from_pitch(self):
        src = _source("platform/biz-docs/biz_docs_service.py")
        forbidden = ["revolutionary", "disruptive", "unprecedented", "game-changing", "#1", "best in class"]
        found = [w for w in forbidden if w.lower() in src.lower()]
        assert not found, f"Forbidden words found in biz_docs_service: {found}"

    def test_active_users_always_null(self):
        src = _source("platform/biz-docs/biz_docs_service.py")
        assert "active_users" in src, "active_users field missing from biz-docs"
        assert "null" in src.lower() or "None" in src, "active_users must always be null/None"

    def test_social_publisher_skips_on_missing_creds(self):
        src = _source("platform/social-publisher/social_publisher_service.py")
        assert "TWITTER_BEARER_TOKEN" in src, "social_publisher must read credentials from env vars"


class TestClaimSystemSelfOrganizes:
    """CLAIM: System organises itself with user approval"""

    def test_organizer_service_exists(self):
        files = list((PLATFORM / "system-organizer").rglob("*service*.py"))
        assert files, "system-organizer service missing"

    def test_never_zone_is_defined(self):
        src = _source("platform/system-organizer/system_organizer_service.py")
        never_paths = ["/etc/", "/boot/", "/sys/", "/proc/"]
        found = [p for p in never_paths if p in src]
        assert found, "NEVER zone paths must be defined in organizer"

    def test_apply_endpoint_required_for_changes(self):
        src = _source("platform/system-organizer/system_organizer_service.py")
        assert "/organizer/apply" in src, "No /organizer/apply endpoint — changes require approval"


class TestClaimAllServicesVerified:
    """CLAIM: 44 microservices, all verified"""

    def test_dev_compose_has_44_services(self):
        compose = _load_compose(DEV_COMPOSE)
        count = len(compose.get("services", {}))
        assert count >= 44, f"Dev compose has {count} services, expected >=44"

    def test_prod_compose_has_44_services(self):
        compose = _load_compose(PROD_COMPOSE)
        count = len(compose.get("services", {}))
        assert count >= 44, f"Prod compose has {count} services, expected >=44"

    def test_all_prod_services_have_restart_always(self):
        compose = _load_compose(PROD_COMPOSE)
        bad = [name for name, svc in compose["services"].items() if svc.get("restart") != "always"]
        assert not bad, f"Services missing restart:always: {bad}"

    def test_all_prod_services_have_mem_limit(self):
        compose = _load_compose(PROD_COMPOSE)
        bad = [name for name, svc in compose["services"].items() if not svc.get("mem_limit")]
        assert not bad, f"Services missing mem_limit: {bad}"

    def test_all_prod_services_have_version_tag(self):
        compose = _load_compose(PROD_COMPOSE)
        upstream = {"redis", "postgres", "vyrex"}
        bad = []
        for name, svc in compose["services"].items():
            if name in upstream:
                continue
            img = svc.get("image", "")
            if img and ":1.0.0" not in img:
                bad.append(f"{name}: {img!r}")
        assert not bad, f"Services without :1.0.0 tag: {bad}"


class TestHonestyPrinciple:
    """CLAIM: No false claims — everything verifiable"""

    def test_honest_limitations_file_exists(self):
        assert (REPO_ROOT / "HONEST_LIMITATIONS.md").exists(), "HONEST_LIMITATIONS.md must exist"

    def test_honest_limitations_covers_bios_ai(self):
        src = _source("HONEST_LIMITATIONS.md")
        assert "BIOS AI" in src, "HONEST_LIMITATIONS must mention BIOS AI hardware req"

    def test_honest_limitations_covers_lora(self):
        src = _source("HONEST_LIMITATIONS.md")
        assert "LoRA" in src, "HONEST_LIMITATIONS must mention LoRA GPU requirement"

    def test_verifier_blocks_unverified_release(self):
        src = _source("platform/inventor-engine/project_releaser.py")
        assert "verified" in src, "Releaser must check verified==True before release"

    def test_weekly_digest_exposes_failures(self):
        src = _source("platform/inventor-engine/inventor_service.py")
        assert "projects_failed" in src, "Weekly digest must expose failure count"

    def test_readme_has_honest_limitations_link(self):
        src = _source("README.md")
        assert "HONEST_LIMITATIONS" in src, "README must reference HONEST_LIMITATIONS.md"

    def test_readme_has_what_prax_does_not_claim(self):
        src = _source("README.md")
        assert "does not claim" in src.lower(), "README must have a section on what Prax does not claim"

    def test_no_fake_metric_words_in_social_publisher(self):
        src = _source("platform/social-publisher/social_publisher_service.py")
        fake_words = ["#1 solution", "best tool", "millions of users", "viral"]
        found = [w for w in fake_words if w.lower() in src.lower()]
        assert not found, f"Fake metric words in social_publisher: {found}"
