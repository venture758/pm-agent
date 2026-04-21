package com.pmagent.backend.application.pipeline;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pmagent.backend.application.llm.LlmService;
import com.pmagent.backend.infrastructure.entity.AgentStateEntity;
import com.pmagent.backend.infrastructure.mapper.AgentStateMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.AbstractExecutorService;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PipelineServiceTest {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private FakeAgentStateMapper agentStateMapper;
    private FakeLlmService llmService;

    @BeforeEach
    void setUp() {
        agentStateMapper = new FakeAgentStateMapper();
        llmService = new FakeLlmService(objectMapper);
    }

    @Test
    void autoModeShouldPauseWhenRequirementNeedsConfirmation() {
        llmService.when("requirement_parsing", "新增发票接口", Map.of(
            "summary", "需求解析存在待确认模块归属",
            "requirements", List.of(Map.of("title", "新增发票接口", "match_status", "needs_confirmation"))
        ));

        PipelineService service = new PipelineService(
            agentStateMapper,
            llmService,
            objectMapper,
            new DirectExecutorService(),
            Duration.ofSeconds(30)
        );

        service.start("w1", "新增发票接口", "auto");
        Map<String, Object> state = service.state("w1");

        assertEquals("auto", state.get("execution_mode"));
        assertEquals("awaiting_confirmation", state.get("run_status"));
        assertEquals(Boolean.TRUE, state.get("awaiting_confirmation"));
        assertTrue(String.valueOf(state.get("blocking_reason")).contains("待确认"));
    }

    @Test
    void autoModeShouldResumeAndFinishAfterConfirmation() {
        llmService.when("requirement_parsing", "新增发票接口", Map.of(
            "summary", "需求解析存在待确认模块归属",
            "requirements", List.of(Map.of("title", "新增发票接口", "match_status", "needs_confirmation"))
        ));
        llmService.when("personnel_matching", anyContext(), Map.of("summary", "人员匹配完成", "items", List.of(Map.of("title", "李祥"))));
        llmService.when("module_extraction", anyContext(), Map.of("summary", "模块提炼完成", "items", List.of()));
        llmService.when("team_analysis", anyContext(), Map.of("summary", "梯队分析完成", "items", List.of()));
        llmService.when("knowledge_update", anyContext(), Map.of("summary", "知识更新完成", "items", List.of()));

        PipelineService service = new PipelineService(
            agentStateMapper,
            llmService,
            objectMapper,
            new DirectExecutorService(),
            Duration.ofSeconds(30)
        );

        service.start("w1", "新增发票接口", "auto");
        service.confirm("w1", "confirm", null, "");
        Map<String, Object> state = service.state("w1");

        assertEquals("completed", state.get("run_status"));
        assertEquals("", state.get("current_step"));
        assertFalse(Boolean.TRUE.equals(state.get("awaiting_confirmation")));
    }

    @Test
    void manualModeShouldStayAwaitingConfirmation() {
        llmService.when("requirement_parsing", "新增发票接口", Map.of(
            "summary", "需求解析完成",
            "requirements", List.of()
        ));

        PipelineService service = new PipelineService(
            agentStateMapper,
            llmService,
            objectMapper,
            new DirectExecutorService(),
            Duration.ofSeconds(30)
        );

        Map<String, Object> state = service.start("w2", "新增发票接口", "manual");

        assertEquals("manual", state.get("execution_mode"));
        assertEquals("awaiting_confirmation", state.get("run_status"));
        assertEquals("requirement_parsing", state.get("current_step"));
        assertEquals(Boolean.FALSE, state.get("awaiting_confirmation"));
    }

    @Test
    void stateShouldFailStaleRunningPipeline() throws Exception {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("workspace_id", "w3");
        payload.put("execution_mode", "auto");
        payload.put("run_id", "run-1");
        payload.put("status", "running");
        payload.put("run_status", "running");
        payload.put("current_step", "requirement_parsing");
        payload.put("step_progress", Map.of("requirement_parsing", "in_progress"));
        payload.put("step_results", Map.of());
        payload.put("history", List.of());
        payload.put("awaiting_confirmation", false);
        payload.put("blocking_reason", "");
        payload.put("last_heartbeat_at", Instant.now().minusSeconds(120).toString());

        agentStateMapper.save("pipeline::w3", objectMapper.writeValueAsString(payload));

        PipelineService service = new PipelineService(
            agentStateMapper,
            llmService,
            objectMapper,
            new DirectExecutorService(),
            Duration.ofSeconds(30)
        );

        Map<String, Object> state = service.state("w3");

        assertEquals("failed", state.get("run_status"));
        assertTrue(String.valueOf(state.get("blocking_reason")).contains("heartbeat"));
    }

    private static String anyContext() {
        return "__ANY__";
    }

    private static final class FakeAgentStateMapper implements AgentStateMapper {

        private final Map<String, AgentStateEntity> states = new LinkedHashMap<>();

        @Override
        public AgentStateEntity get(String stateKey) {
            return states.get(stateKey);
        }

        @Override
        public int upsert(AgentStateEntity entity) {
            AgentStateEntity stored = new AgentStateEntity();
            stored.setStateKey(entity.getStateKey());
            stored.setPayload(entity.getPayload());
            stored.setUpdatedAt(entity.getUpdatedAt());
            states.put(entity.getStateKey(), stored);
            return 1;
        }

        void save(String stateKey, String payload) {
            AgentStateEntity entity = new AgentStateEntity();
            entity.setStateKey(stateKey);
            entity.setPayload(payload);
            entity.setUpdatedAt(Instant.now().toString());
            states.put(stateKey, entity);
        }
    }

    private static final class FakeLlmService extends LlmService {

        private final Map<String, Map<String, Object>> exactResponses = new LinkedHashMap<>();
        private final Map<String, Map<String, Object>> wildcardResponses = new LinkedHashMap<>();

        FakeLlmService(ObjectMapper objectMapper) {
            super(null, objectMapper);
        }

        void when(String step, String context, Map<String, Object> response) {
            if (anyContext().equals(context)) {
                wildcardResponses.put(step, response);
                return;
            }
            exactResponses.put(step + "::" + context, response);
        }

        @Override
        public Map<String, Object> analyzePipelineStep(String stepKey, String context, String feedback) {
            Map<String, Object> response = exactResponses.get(stepKey + "::" + context);
            if (response == null) {
                response = wildcardResponses.get(stepKey);
            }
            if (response == null) {
                throw new IllegalStateException("missing fake llm response for " + stepKey);
            }
            return new LinkedHashMap<>(response);
        }
    }

    private static final class DirectExecutorService extends AbstractExecutorService {

        private boolean shutdown;

        @Override
        public void shutdown() {
            shutdown = true;
        }

        @Override
        public List<Runnable> shutdownNow() {
            shutdown = true;
            return new ArrayList<>();
        }

        @Override
        public boolean isShutdown() {
            return shutdown;
        }

        @Override
        public boolean isTerminated() {
            return shutdown;
        }

        @Override
        public boolean awaitTermination(long timeout, TimeUnit unit) {
            return true;
        }

        @Override
        public void execute(Runnable command) {
            command.run();
        }
    }
}
