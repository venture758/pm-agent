package com.pmagent.backend.application.pipeline;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pmagent.backend.application.llm.LlmService;
import com.pmagent.backend.infrastructure.entity.AgentStateEntity;
import com.pmagent.backend.infrastructure.mapper.AgentStateMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Service
public class PipelineService {

    private static final List<String> STEPS = List.of(
        "requirement_parsing",
        "personnel_matching",
        "module_extraction",
        "team_analysis",
        "knowledge_update"
    );
    private static final Set<String> ACTIVE_RUN_STATUSES = Set.of("queued", "running", "awaiting_confirmation");

    private final AgentStateMapper agentStateMapper;
    private final LlmService llmService;
    private final ObjectMapper objectMapper;
    private final ExecutorService executorService;
    private final Duration heartbeatTimeout;
    private final Map<String, Object> workspaceLocks = new ConcurrentHashMap<>();
    private final Map<String, Boolean> activeRuns = new ConcurrentHashMap<>();

    @Autowired
    public PipelineService(AgentStateMapper agentStateMapper, LlmService llmService, ObjectMapper objectMapper) {
        this(
            agentStateMapper,
            llmService,
            objectMapper,
            Executors.newCachedThreadPool((runnable) -> {
                Thread thread = new Thread(runnable, "pipeline-runner");
                thread.setDaemon(true);
                return thread;
            }),
            Duration.ofSeconds(30)
        );
    }

    PipelineService(AgentStateMapper agentStateMapper,
                    LlmService llmService,
                    ObjectMapper objectMapper,
                    ExecutorService executorService,
                    Duration heartbeatTimeout) {
        this.agentStateMapper = agentStateMapper;
        this.llmService = llmService;
        this.objectMapper = objectMapper;
        this.executorService = executorService;
        this.heartbeatTimeout = heartbeatTimeout;
    }

    public Map<String, Object> start(String workspaceId, String message, String executionMode) {
        synchronized (lockFor(workspaceId)) {
            Map<String, Object> existingState = loadStateUnsafe(workspaceId);
            if (isPipelineActive(existingState)) {
                throw new IllegalStateException("pipeline_run_active");
            }

            String normalizedMode = normalizeExecutionMode(executionMode);
            if ("manual".equals(normalizedMode)) {
                return startManualUnsafe(workspaceId, message);
            }
            return startAutoUnsafe(workspaceId, message);
        }
    }

    public Map<String, Object> state(String workspaceId) {
        synchronized (lockFor(workspaceId)) {
            Map<String, Object> state = loadStateUnsafe(workspaceId);
            return maybeMarkTimedOutUnsafe(workspaceId, state);
        }
    }

    public Map<String, Object> confirm(String workspaceId, String action, Object modifications, String feedback) {
        synchronized (lockFor(workspaceId)) {
            Map<String, Object> state = maybeMarkTimedOutUnsafe(workspaceId, loadStateUnsafe(workspaceId));
            String runStatus = String.valueOf(state.getOrDefault("run_status", "idle"));
            if ("idle".equals(runStatus)) {
                throw new IllegalArgumentException("pipeline_not_started");
            }
            String currentStep = String.valueOf(state.getOrDefault("current_step", ""));
            if (currentStep.isBlank()) {
                throw new IllegalArgumentException("pipeline_current_step_missing");
            }

            String executionMode = String.valueOf(state.getOrDefault("execution_mode", "manual"));
            if ("auto".equals(executionMode)) {
                return handleAutoActionUnsafe(workspaceId, state, currentStep, action, modifications, feedback);
            }
            return handleManualActionUnsafe(workspaceId, state, currentStep, action, modifications, feedback);
        }
    }

    private Map<String, Object> startManualUnsafe(String workspaceId, String message) {
        String firstStep = STEPS.get(0);
        Map<String, Object> stepProgress = initializeStepProgress(firstStep);
        Map<String, Object> stepResult = llmService.analyzePipelineStep(firstStep, message, "");
        Map<String, Object> stepResults = new LinkedHashMap<>();
        stepResults.put(firstStep, stepResult);

        Map<String, Object> state = baseState(workspaceId, "manual", message, firstStep, stepProgress, stepResults);
        state.put("status", "awaiting_confirmation");
        state.put("run_status", "awaiting_confirmation");
        state.put("awaiting_confirmation", false);
        state.put("blocking_reason", requiresHumanConfirmation(firstStep, stepResult) ? blockingReason(firstStep, stepResult) : "");
        state.put("history", List.of(historyItem("start", firstStep, "", "manual")));
        saveUnsafe(workspaceId, state);
        return state;
    }

    private Map<String, Object> startAutoUnsafe(String workspaceId, String message) {
        String firstStep = STEPS.get(0);
        Map<String, Object> stepProgress = initializeStepProgress(firstStep);
        Map<String, Object> state = baseState(workspaceId, "auto", message, firstStep, stepProgress, new LinkedHashMap<>());
        state.put("status", "queued");
        state.put("run_status", "queued");
        state.put("awaiting_confirmation", false);
        state.put("blocking_reason", "");
        state.put("history", List.of(historyItem("start", firstStep, "", "auto")));
        saveUnsafe(workspaceId, state);
        submitAutoRun(workspaceId, String.valueOf(state.get("run_id")));
        return state;
    }

    private Map<String, Object> handleManualActionUnsafe(String workspaceId,
                                                         Map<String, Object> state,
                                                         String currentStep,
                                                         String action,
                                                         Object modifications,
                                                         String feedback) {
        Map<String, Object> mutableState = mutableState(state);
        Map<String, Object> stepProgress = mutableStepProgress(mutableState);
        Map<String, Object> stepResults = mutableStepResults(mutableState);
        List<Map<String, Object>> history = mutableHistory(mutableState);
        String normalizedAction = normalizeAction(action);

        if ("reanalyze".equals(normalizedAction)) {
            Object context = stepResults.get(currentStep);
            Map<String, Object> updated = llmService.analyzePipelineStep(currentStep, writeJson(context), normalizeText(feedback));
            stepResults.put(currentStep, updated);
            history.add(historyItem("reanalyze", currentStep, feedback, ""));
            mutableState.put("blocking_reason", requiresHumanConfirmation(currentStep, updated) ? blockingReason(currentStep, updated) : "");
            mutableState.put("awaiting_confirmation", false);
            saveUnsafe(workspaceId, mutableState);
            return mutableState;
        }

        if ("modify".equals(normalizedAction)) {
            if (modifications == null) {
                throw new IllegalArgumentException("modifications required for modify action");
            }
            stepResults.put(currentStep, castResult(modifications));
            history.add(historyItem("modify", currentStep, "", "manual modifications"));
            mutableState.put("blocking_reason", "");
            mutableState.put("awaiting_confirmation", false);
            saveUnsafe(workspaceId, mutableState);
            return mutableState;
        }

        int currentIndex = indexOfStep(currentStep);
        stepProgress.put(currentStep, "skip".equals(normalizedAction) ? "skipped" : "completed");
        history.add(historyItem(normalizedAction, currentStep, feedback, ""));

        boolean finishNow = "execute".equals(normalizedAction) || currentIndex == STEPS.size() - 1;
        if (finishNow) {
            markCompleted(mutableState);
            saveUnsafe(workspaceId, mutableState);
            return mutableState;
        }

        String nextStep = STEPS.get(currentIndex + 1);
        stepProgress.put(nextStep, "in_progress");
        Map<String, Object> nextResult = llmService.analyzePipelineStep(
            nextStep,
            contextForStep(mutableState, stepResults, currentIndex + 1),
            normalizeText(feedback)
        );
        stepResults.put(nextStep, nextResult);
        mutableState.put("current_step", nextStep);
        mutableState.put("status", "awaiting_confirmation");
        mutableState.put("run_status", "awaiting_confirmation");
        mutableState.put("awaiting_confirmation", false);
        mutableState.put("blocking_reason", requiresHumanConfirmation(nextStep, nextResult) ? blockingReason(nextStep, nextResult) : "");
        saveUnsafe(workspaceId, mutableState);
        return mutableState;
    }

    private Map<String, Object> handleAutoActionUnsafe(String workspaceId,
                                                       Map<String, Object> state,
                                                       String currentStep,
                                                       String action,
                                                       Object modifications,
                                                       String feedback) {
        if (activeRuns.containsKey(workspaceId)) {
            throw new IllegalStateException("pipeline_run_active");
        }

        Map<String, Object> mutableState = mutableState(state);
        Map<String, Object> stepProgress = mutableStepProgress(mutableState);
        Map<String, Object> stepResults = mutableStepResults(mutableState);
        List<Map<String, Object>> history = mutableHistory(mutableState);
        String normalizedAction = normalizeAction(action);
        String runStatus = String.valueOf(mutableState.getOrDefault("run_status", "idle"));

        if (!"awaiting_confirmation".equals(runStatus) && !"failed".equals(runStatus)) {
            throw new IllegalStateException("pipeline_not_awaiting_confirmation");
        }

        if ("reanalyze".equals(normalizedAction)) {
            Object context = stepResults.get(currentStep);
            Map<String, Object> updated = llmService.analyzePipelineStep(currentStep, writeJson(context), normalizeText(feedback));
            stepResults.put(currentStep, updated);
            history.add(historyItem("reanalyze", currentStep, feedback, "auto"));
            if (requiresHumanConfirmation(currentStep, updated)) {
                mutableState.put("status", "awaiting_confirmation");
                mutableState.put("run_status", "awaiting_confirmation");
                mutableState.put("awaiting_confirmation", true);
                mutableState.put("blocking_reason", blockingReason(currentStep, updated));
                saveUnsafe(workspaceId, mutableState);
                return mutableState;
            }

            stepProgress.put(currentStep, "in_progress");
            mutableState.put("status", "running");
            mutableState.put("run_status", "running");
            mutableState.put("awaiting_confirmation", false);
            mutableState.put("blocking_reason", "");
            saveUnsafe(workspaceId, mutableState);
            submitAutoRun(workspaceId, String.valueOf(mutableState.get("run_id")));
            return mutableState;
        }

        if ("modify".equals(normalizedAction)) {
            if (modifications == null) {
                throw new IllegalArgumentException("modifications required for modify action");
            }
            stepResults.put(currentStep, castResult(modifications));
            history.add(historyItem("modify", currentStep, "", "auto"));
            return advanceAutoRunUnsafe(workspaceId, mutableState, currentStep, "completed");
        }

        if ("skip".equals(normalizedAction)) {
            history.add(historyItem("skip", currentStep, feedback, "auto"));
            return advanceAutoRunUnsafe(workspaceId, mutableState, currentStep, "skipped");
        }

        history.add(historyItem(normalizedAction, currentStep, feedback, "auto"));
        return advanceAutoRunUnsafe(workspaceId, mutableState, currentStep, "completed");
    }

    private Map<String, Object> advanceAutoRunUnsafe(String workspaceId,
                                                     Map<String, Object> state,
                                                     String currentStep,
                                                     String terminalStepStatus) {
        Map<String, Object> stepProgress = mutableStepProgress(state);
        stepProgress.put(currentStep, terminalStepStatus);

        int currentIndex = indexOfStep(currentStep);
        if (currentIndex == STEPS.size() - 1) {
            markCompleted(state);
            saveUnsafe(workspaceId, state);
            return state;
        }

        String nextStep = STEPS.get(currentIndex + 1);
        stepProgress.put(nextStep, "in_progress");
        state.put("current_step", nextStep);
        state.put("status", "running");
        state.put("run_status", "running");
        state.put("awaiting_confirmation", false);
        state.put("blocking_reason", "");
        saveUnsafe(workspaceId, state);
        submitAutoRun(workspaceId, String.valueOf(state.get("run_id")));
        return state;
    }

    private void submitAutoRun(String workspaceId, String runId) {
        activeRuns.put(workspaceId, Boolean.TRUE);
        executorService.submit(() -> runAuto(workspaceId, runId));
    }

    private void runAuto(String workspaceId, String runId) {
        try {
            while (true) {
                String currentStep;
                String stepContext;
                Map<String, Object> existingResult;

                synchronized (lockFor(workspaceId)) {
                    Map<String, Object> state = loadStateUnsafe(workspaceId);
                    if (!runId.equals(String.valueOf(state.getOrDefault("run_id", "")))) {
                        return;
                    }
                    if (!"auto".equals(String.valueOf(state.getOrDefault("execution_mode", "")))) {
                        return;
                    }
                    String runStatus = String.valueOf(state.getOrDefault("run_status", "idle"));
                    if ("awaiting_confirmation".equals(runStatus)
                        || "completed".equals(runStatus)
                        || "failed".equals(runStatus)
                        || "idle".equals(runStatus)) {
                        return;
                    }

                    currentStep = String.valueOf(state.getOrDefault("current_step", ""));
                    if (currentStep.isBlank()) {
                        markCompleted(state);
                        saveUnsafe(workspaceId, state);
                        return;
                    }

                    Map<String, Object> stepResults = mutableStepResults(state);
                    existingResult = castResult(stepResults.get(currentStep));
                    if (existingResult.isEmpty()) {
                        state.put("status", "running");
                        state.put("run_status", "running");
                        state.put("awaiting_confirmation", false);
                        state.put("blocking_reason", "");
                        saveUnsafe(workspaceId, state);
                    }
                    stepContext = contextForStep(state, stepResults, indexOfStep(currentStep));
                }

                Map<String, Object> stepResult = existingResult;
                if (stepResult.isEmpty()) {
                    stepResult = llmService.analyzePipelineStep(currentStep, stepContext, "");
                }
                if (stepResult == null || stepResult.isEmpty()) {
                    throw new IllegalStateException("pipeline_step_empty_result:" + currentStep);
                }

                synchronized (lockFor(workspaceId)) {
                    Map<String, Object> state = loadStateUnsafe(workspaceId);
                    if (!runId.equals(String.valueOf(state.getOrDefault("run_id", "")))) {
                        return;
                    }

                    Map<String, Object> stepProgress = mutableStepProgress(state);
                    Map<String, Object> stepResults = mutableStepResults(state);
                    List<Map<String, Object>> history = mutableHistory(state);
                    stepResults.put(currentStep, stepResult);

                    if (requiresHumanConfirmation(currentStep, stepResult)) {
                        state.put("status", "awaiting_confirmation");
                        state.put("run_status", "awaiting_confirmation");
                        state.put("awaiting_confirmation", true);
                        state.put("blocking_reason", blockingReason(currentStep, stepResult));
                        history.add(historyItem("await_confirmation", currentStep, "", "auto"));
                        saveUnsafe(workspaceId, state);
                        return;
                    }

                    int currentIndex = indexOfStep(currentStep);
                    stepProgress.put(currentStep, "completed");
                    history.add(historyItem("auto_complete", currentStep, "", ""));
                    if (currentIndex == STEPS.size() - 1) {
                        markCompleted(state);
                        saveUnsafe(workspaceId, state);
                        return;
                    }

                    String nextStep = STEPS.get(currentIndex + 1);
                    stepProgress.put(nextStep, "in_progress");
                    state.put("current_step", nextStep);
                    state.put("status", "running");
                    state.put("run_status", "running");
                    state.put("awaiting_confirmation", false);
                    state.put("blocking_reason", "");
                    saveUnsafe(workspaceId, state);
                }
            }
        } catch (Exception ex) {
            synchronized (lockFor(workspaceId)) {
                Map<String, Object> state = loadStateUnsafe(workspaceId);
                state.put("status", "failed");
                state.put("run_status", "failed");
                state.put("awaiting_confirmation", false);
                state.put("blocking_reason", normalizeText(ex.getMessage()));
                mutableHistory(state).add(historyItem("failed", String.valueOf(state.getOrDefault("current_step", "")), "", normalizeText(ex.getMessage())));
                saveUnsafe(workspaceId, state);
            }
        } finally {
            activeRuns.remove(workspaceId);
        }
    }

    private Map<String, Object> maybeMarkTimedOutUnsafe(String workspaceId, Map<String, Object> state) {
        String runStatus = String.valueOf(state.getOrDefault("run_status", "idle"));
        if (!Set.of("queued", "running").contains(runStatus) || activeRuns.containsKey(workspaceId)) {
            return state;
        }
        Instant heartbeat = parseInstant(state.get("last_heartbeat_at"));
        if (heartbeat != null && heartbeat.isAfter(Instant.now().minus(heartbeatTimeout))) {
            return state;
        }
        state.put("status", "failed");
        state.put("run_status", "failed");
        state.put("awaiting_confirmation", false);
        state.put("blocking_reason", "pipeline runner heartbeat expired");
        mutableHistory(state).add(historyItem("failed", String.valueOf(state.getOrDefault("current_step", "")), "", "heartbeat timeout"));
        saveUnsafe(workspaceId, state);
        return state;
    }

    private boolean requiresHumanConfirmation(String step, Map<String, Object> stepResult) {
        if (truthy(stepResult.get("requires_confirmation"))) {
            return true;
        }
        if (!"requirement_parsing".equals(step)) {
            return false;
        }
        for (Map<String, Object> requirement : extractRows(stepResult)) {
            if ("needs_confirmation".equalsIgnoreCase(String.valueOf(requirement.getOrDefault("match_status", "")))) {
                return true;
            }
        }
        return false;
    }

    private String blockingReason(String step, Map<String, Object> stepResult) {
        String explicitReason = firstNonBlank(
            stepResult.get("blocking_reason"),
            stepResult.get("attention_reason"),
            stepResult.get("summary")
        );
        if (!explicitReason.isBlank()) {
            return explicitReason;
        }
        if ("requirement_parsing".equals(step)) {
            for (Map<String, Object> requirement : extractRows(stepResult)) {
                if ("needs_confirmation".equalsIgnoreCase(String.valueOf(requirement.getOrDefault("match_status", "")))) {
                    return "需求解析存在待确认模块归属: " + String.valueOf(requirement.getOrDefault("title", "未命名需求"));
                }
            }
        }
        return "当前步骤需要人工确认";
    }

    private List<Map<String, Object>> extractRows(Map<String, Object> stepResult) {
        Object requirements = stepResult.get("requirements");
        if (requirements instanceof List<?> rawRequirements) {
            return coerceMapList(rawRequirements);
        }
        Object items = stepResult.get("items");
        if (items instanceof List<?> rawItems) {
            return coerceMapList(rawItems);
        }
        return List.of();
    }

    private List<Map<String, Object>> coerceMapList(List<?> rawItems) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (Object rawItem : rawItems) {
            if (rawItem instanceof Map<?, ?> map) {
                rows.add(castResult(map));
            }
        }
        return rows;
    }

    private int indexOfStep(String step) {
        int currentIndex = STEPS.indexOf(step);
        if (currentIndex < 0) {
            throw new IllegalArgumentException("unknown pipeline step: " + step);
        }
        return currentIndex;
    }

    private Map<String, Object> initializeStepProgress(String currentStep) {
        Map<String, Object> stepProgress = new LinkedHashMap<>();
        for (String step : STEPS) {
            stepProgress.put(step, step.equals(currentStep) ? "in_progress" : "pending");
        }
        return stepProgress;
    }

    private Map<String, Object> baseState(String workspaceId,
                                          String executionMode,
                                          String message,
                                          String currentStep,
                                          Map<String, Object> stepProgress,
                                          Map<String, Object> stepResults) {
        Map<String, Object> state = new LinkedHashMap<>();
        state.put("workspace_id", workspaceId);
        state.put("run_id", UUID.randomUUID().toString());
        state.put("execution_mode", executionMode);
        state.put("status", "queued");
        state.put("run_status", "queued");
        state.put("input_message", normalizeText(message));
        state.put("current_step", currentStep);
        state.put("step_progress", stepProgress);
        state.put("step_results", stepResults);
        state.put("history", new ArrayList<Map<String, Object>>());
        state.put("awaiting_confirmation", false);
        state.put("blocking_reason", "");
        state.put("last_heartbeat_at", Instant.now().toString());
        return state;
    }

    private void markCompleted(Map<String, Object> state) {
        state.put("status", "completed");
        state.put("run_status", "completed");
        state.put("current_step", "");
        state.put("awaiting_confirmation", false);
        state.put("blocking_reason", "");
    }

    private boolean isPipelineActive(Map<String, Object> state) {
        String runStatus = String.valueOf(state.getOrDefault("run_status", "idle"));
        return ACTIVE_RUN_STATUSES.contains(runStatus);
    }

    private String contextForStep(Map<String, Object> state, Map<String, Object> stepResults, int currentIndex) {
        if (currentIndex <= 0) {
            return String.valueOf(state.getOrDefault("input_message", ""));
        }
        return writeJson(stepResults.getOrDefault(STEPS.get(currentIndex - 1), Map.of()));
    }

    private Map<String, Object> loadStateUnsafe(String workspaceId) {
        AgentStateEntity entity = agentStateMapper.get(stateKey(workspaceId));
        if (entity == null || entity.getPayload() == null || entity.getPayload().isBlank()) {
            return idleState(workspaceId);
        }
        return readMap(entity.getPayload());
    }

    private Map<String, Object> idleState(String workspaceId) {
        Map<String, Object> state = new LinkedHashMap<>();
        state.put("workspace_id", workspaceId);
        state.put("status", "idle");
        state.put("run_status", "idle");
        state.put("run_id", "");
        state.put("execution_mode", "");
        state.put("current_step", "");
        state.put("step_progress", Map.of());
        state.put("step_results", Map.of());
        state.put("history", List.of());
        state.put("awaiting_confirmation", false);
        state.put("blocking_reason", "");
        state.put("last_heartbeat_at", "");
        return state;
    }

    private Map<String, Object> mutableState(Map<String, Object> state) {
        return new LinkedHashMap<>(state);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mutableStepProgress(Map<String, Object> state) {
        Map<String, Object> stepProgress = (Map<String, Object>) state.get("step_progress");
        Map<String, Object> copy = stepProgress == null ? new LinkedHashMap<>() : new LinkedHashMap<>(stepProgress);
        state.put("step_progress", copy);
        return copy;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mutableStepResults(Map<String, Object> state) {
        Map<String, Object> stepResults = (Map<String, Object>) state.get("step_results");
        Map<String, Object> copy = stepResults == null ? new LinkedHashMap<>() : new LinkedHashMap<>(stepResults);
        state.put("step_results", copy);
        return copy;
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> mutableHistory(Map<String, Object> state) {
        List<Map<String, Object>> history = (List<Map<String, Object>>) state.get("history");
        List<Map<String, Object>> copy = history == null ? new ArrayList<>() : new ArrayList<>(history);
        state.put("history", copy);
        return copy;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> castResult(Object raw) {
        if (raw instanceof Map<?, ?> map) {
            return (Map<String, Object>) objectMapper.convertValue(map, Map.class);
        }
        return new LinkedHashMap<>();
    }

    private Map<String, Object> historyItem(String action, String step, String feedback, String note) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("timestamp", Instant.now().toString());
        item.put("action", action);
        item.put("step", step == null ? "" : step);
        item.put("feedback", normalizeText(feedback));
        item.put("note", normalizeText(note));
        return item;
    }

    private void saveUnsafe(String workspaceId, Map<String, Object> state) {
        state.put("last_heartbeat_at", Instant.now().toString());
        AgentStateEntity entity = new AgentStateEntity();
        entity.setStateKey(stateKey(workspaceId));
        entity.setPayload(writeJson(state));
        entity.setUpdatedAt(Instant.now().toString());
        agentStateMapper.upsert(entity);
    }

    private Object lockFor(String workspaceId) {
        return workspaceLocks.computeIfAbsent(workspaceId, ignored -> new Object());
    }

    private String stateKey(String workspaceId) {
        return "pipeline::" + workspaceId;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> readMap(String json) {
        try {
            return objectMapper.readValue(json, Map.class);
        } catch (Exception ex) {
            throw new IllegalArgumentException("invalid pipeline state json", ex);
        }
    }

    private String writeJson(Object payload) {
        try {
            return objectMapper.writeValueAsString(payload);
        } catch (Exception ex) {
            throw new IllegalArgumentException("failed to serialize pipeline state", ex);
        }
    }

    private boolean truthy(Object value) {
        if (value instanceof Boolean booleanValue) {
            return booleanValue;
        }
        return "true".equalsIgnoreCase(String.valueOf(value).trim());
    }

    private String normalizeExecutionMode(String executionMode) {
        return "manual".equalsIgnoreCase(normalizeText(executionMode)) ? "manual" : "auto";
    }

    private String normalizeAction(String action) {
        return action == null ? "confirm" : action.trim().toLowerCase();
    }

    private String normalizeText(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String firstNonBlank(Object... values) {
        for (Object value : values) {
            String normalized = normalizeText(value);
            if (!normalized.isBlank()) {
                return normalized;
            }
        }
        return "";
    }

    private Instant parseInstant(Object value) {
        String text = normalizeText(value);
        if (text.isBlank()) {
            return null;
        }
        try {
            return Instant.parse(text);
        } catch (DateTimeParseException ignored) {
            return null;
        }
    }
}
