from __future__ import annotations

import json
import unittest

from pm_agent.agents.orchestrator import OrchestratorAgent
from pm_agent.llm_client import LlmFallbackStats


class MockLlm:
    """Mock LLM that returns different responses based on the system prompt content."""

    def chat_completion(self, messages):
        system = messages[0].get("content", "")
        if "requirement_analysis" in system or "需求解析" in system:
            text = json.dumps({
                "mode": "requirement_analysis",
                "requirements": [
                    {
                        "title": "User login API",
                        "priority": "high",
                        "complexity": "medium",
                        "risk": "low",
                        "skills": ["Python"],
                        "matched_modules": [],
                        "dependency_hints": [],
                        "blockers": [],
                        "split_suggestion": "",
                        "analysis_factors": [],
                    }
                ],
                "reply": "Parsed 1 requirement",
            })
        elif "personnel_matching" in system:
            text = json.dumps({
                "mode": "personnel_matching",
                "assignments": [
                    {
                        "requirement_id": "REQ-001",
                        "requirement_title": "User login API",
                        "development_owner": "Zhang San",
                        "testing_owner": "Li Si",
                        "backup_owner": "Wang Wu",
                        "collaborators": [],
                        "reasons": ["Familiar with Python"],
                        "workload_snapshot": {"Zhang San": 0.3},
                        "confidence": 0.8,
                    }
                ],
                "reply": "Assignment complete",
            })
        elif "module_extraction" in system:
            text = json.dumps({
                "mode": "module_extraction",
                "module_changes": [],
                "reply": "No new modules",
            })
        elif "team_analysis" in system:
            text = json.dumps({
                "mode": "team_analysis",
                "module_familiarity_matrix": {},
                "single_point_risks": [],
                "growth_paths": [],
                "reply": "No significant risks",
            })
        elif "knowledge_update" in system:
            text = json.dumps({
                "mode": "knowledge_update",
                "summary": {
                    "requirements_parsed": 1,
                    "personnel_assigned": 1,
                    "modules_created": 0,
                    "familiarity_updates": 0,
                    "risks_identified": 0,
                },
                "pending_changes": [],
                "reply": "Summary complete",
            })
        else:
            text = json.dumps({"mode": "unknown", "reply": ""})
        return (text, LlmFallbackStats(final_tier="primary"))

    def parse_json_response(self, text):
        return json.loads(text)


class TestOrchestratorAgent(unittest.TestCase):
    def setUp(self):
        self.llm = MockLlm()
        self.orchestrator = OrchestratorAgent(llm_client=self.llm)

    def test_start_executes_first_step(self):
        """start() creates PipelineContext and executes step 1 (requirement_parsing)."""
        result = self.orchestrator.start("w1", "Need a user login API")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["step"], "requirement_parsing")
        self.assertEqual(len(result["data"]["requirements"]), 1)

        state = self.orchestrator.get_state("w1")
        self.assertIsNotNone(state)
        self.assertEqual(state["current_step"], "requirement_parsing")
        self.assertEqual(state["current_step_index"], 0)

    def test_confirm_advances_to_next_step(self):
        """confirm action saves result and advances to the next step."""
        self.orchestrator.start("w2", "Need a user login API")

        # Confirm step 1 -> step 2
        result = self.orchestrator.confirm_step("w2", "confirm")
        self.assertEqual(result["step"], "personnel_matching")
        self.assertEqual(result["status"], "success")

        # Confirm step 2 -> step 3
        result = self.orchestrator.confirm_step("w2", "confirm")
        self.assertEqual(result["step"], "module_extraction")

    def test_skip_advances(self):
        """skip action marks step as skipped and advances to next step."""
        self.orchestrator.start("w3", "Need a user login API")

        # Skip step 1 -> step 2
        result = self.orchestrator.confirm_step("w3", "skip")
        self.assertEqual(result["step"], "personnel_matching")

        state = self.orchestrator.get_state("w3")
        self.assertEqual(state["step_results"]["requirement_parsing"]["status"], "skipped")

    def test_reanalyze_injects_constraint(self):
        """reanalyze action injects feedback as a constraint and re-executes current step."""
        self.orchestrator.start("w4", "Need a user login API")

        # Reanalyze step 1 with feedback
        result = self.orchestrator.confirm_step("w4", "reanalyze", feedback="Make sure to consider security")
        self.assertEqual(result["step"], "requirement_parsing")
        self.assertEqual(result["status"], "success")

        # Verify constraint was saved
        state = self.orchestrator.get_state("w4")
        self.assertIn("Make sure to consider security", state["step_constraints"]["requirement_parsing"])

    def test_get_state(self):
        """get_state returns PipelineContext.to_dict() or None."""
        # Non-existent workspace
        result = self.orchestrator.get_state("nonexistent")
        self.assertIsNone(result)

        # Existing workspace
        self.orchestrator.start("w5", "Need a user login API")
        state = self.orchestrator.get_state("w5")
        self.assertIsNotNone(state)
        self.assertEqual(state["workspace_id"], "w5")
        self.assertEqual(state["user_message"], "Need a user login API")
        self.assertIn("current_step", state)
        self.assertIn("step_progress", state)
        self.assertIn("step_results", state)

    def test_complete_after_all_steps(self):
        """After confirming all 5 steps, pipeline is complete."""
        self.orchestrator.start("w6", "Need a user login API")

        # Confirm through steps 1-4
        for _ in range(4):
            result = self.orchestrator.confirm_step("w6", "confirm")

        # At this point, step 5 (knowledge_update) should have been executed
        # and confirming it should mark as complete
        result = self.orchestrator.confirm_step("w6", "confirm")
        self.assertEqual(result["status"], "complete")

        state = self.orchestrator.get_state("w6")
        self.assertTrue(state["is_complete"])
