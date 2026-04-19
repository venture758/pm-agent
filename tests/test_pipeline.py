from __future__ import annotations

import unittest

from pm_agent.pipeline import PipelineContext, PipelineStore, PIPELINE_STEPS


class TestPipelineContext(unittest.TestCase):
    def test_initial_state(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        self.assertEqual(ctx.current_step, "requirement_parsing")
        self.assertFalse(ctx.is_complete)
        self.assertEqual(ctx.current_step_index, 0)

    def test_step_progress(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        ctx.current_step_index = 2
        progress = ctx.step_progress
        self.assertEqual(progress[0]["status"], "completed")
        self.assertEqual(progress[1]["status"], "completed")
        self.assertEqual(progress[2]["status"], "current")
        self.assertEqual(progress[3]["status"], "pending")

    def test_complete(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        ctx.current_step_index = len(PIPELINE_STEPS)
        self.assertTrue(ctx.is_complete)
        self.assertIsNone(ctx.current_step)

    def test_serialization(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        ctx.requirements = [{"title": "R1"}]
        ctx.current_step_index = 1
        d = ctx.to_dict()
        restored = PipelineContext.from_dict(d)
        self.assertEqual(restored.workspace_id, "w1")
        self.assertEqual(restored.requirements, [{"title": "R1"}])
        self.assertEqual(restored.current_step_index, 1)


class TestPipelineStore(unittest.TestCase):
    def test_save_load(self):
        store = PipelineStore()
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        store.save(ctx)
        loaded = store.load("w1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.workspace_id, "w1")

    def test_delete(self):
        store = PipelineStore()
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        store.save(ctx)
        store.delete("w1")
        self.assertIsNone(store.load("w1"))
