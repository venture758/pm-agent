package com.pmagent.backend.application.pipeline;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pmagent.backend.application.llm.LlmService;
import com.pmagent.backend.infrastructure.entity.AgentStateEntity;
import com.pmagent.backend.infrastructure.mapper.AgentStateMapper;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class PipelineService {

    private static final List<String> STEPS = List.of(
        "requirement_parsing",
        "personnel_matching",
        "module_extraction",
        "team_analysis",
        "knowledge_update"
    );

    private final AgentStateMapper agentStateMapper;
    private final LlmService llmService;
    private final ObjectMapper objectMapper;

    public PipelineService(AgentStateMapper agentStateMapper, LlmService llmService, ObjectMapper objectMapper) {
        this.agentStateMapper = agentStateMapper;
        this.llmService = llmService;
        this.objectMapper = objectMapper;
    }

    public Map<String, Object> start(String workspaceId, String message) {
        String firstStep = STEPS.get(0);
        Map<String, Object> stepResult = llmService.analyzePipelineStep(firstStep, message, "");

        Map<String, Object> stepProgress = new LinkedHashMap<>();
        for (String step : STEPS) {
            stepProgress.put(step, step.equals(firstStep) ? "in_progress" : "pending");
        }
        Map<String, Object> stepResults = new LinkedHashMap<>();
        stepResults.put(firstStep, stepResult);

        Map<String, Object> state = new LinkedHashMap<>();
        state.put("status", "running");
        state.put("current_step", firstStep);
        state.put("step_progress", stepProgress);
        state.put("step_results", stepResults);
        state.put("history", List.of(historyItem("start", firstStep, "", "")));
        save(workspaceId, state);
        return state;
    }

    public Map<String, Object> state(String workspaceId) {
        AgentStateEntity entity = agentStateMapper.get(stateKey(workspaceId));
        if (entity == null || entity.getPayload() == null || entity.getPayload().isBlank()) {
            return Map.of(
                "status", "idle",
                "current_step", "",
                "step_progress", Map.of(),
                "step_results", Map.of(),
                "history", List.of()
            );
        }
        return readMap(entity.getPayload());
    }

    public Map<String, Object> confirm(String workspaceId, String action, Object modifications, String feedback) {
        Map<String, Object> state = state(workspaceId);
        String status = String.valueOf(state.getOrDefault("status", "idle"));
        if ("idle".equals(status)) {
            throw new IllegalArgumentException("pipeline_not_started");
        }
        String currentStep = String.valueOf(state.getOrDefault("current_step", ""));
        if (currentStep.isBlank()) {
            throw new IllegalArgumentException("pipeline_current_step_missing");
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> stepProgress = new LinkedHashMap<>((Map<String, Object>) state.getOrDefault("step_progress", Map.of()));
        @SuppressWarnings("unchecked")
        Map<String, Object> stepResults = new LinkedHashMap<>((Map<String, Object>) state.getOrDefault("step_results", Map.of()));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> history = new ArrayList<>((List<Map<String, Object>>) state.getOrDefault("history", List.of()));

        String normalizedAction = action == null ? "confirm" : action.trim().toLowerCase();
        if ("reanalyze".equals(normalizedAction)) {
            Object context = stepResults.get(currentStep);
            Map<String, Object> updated = llmService.analyzePipelineStep(currentStep, writeJson(context), feedback == null ? "" : feedback);
            stepResults.put(currentStep, updated);
            history.add(historyItem("reanalyze", currentStep, feedback, ""));
            state.put("step_results", stepResults);
            state.put("history", history);
            save(workspaceId, state);
            return state;
        }
        if ("modify".equals(normalizedAction)) {
            if (modifications == null) {
                throw new IllegalArgumentException("modifications required for modify action");
            }
            stepResults.put(currentStep, modifications);
            history.add(historyItem("modify", currentStep, "", "manual modifications"));
            state.put("step_results", stepResults);
            state.put("history", history);
            save(workspaceId, state);
            return state;
        }

        int currentIndex = STEPS.indexOf(currentStep);
        if (currentIndex < 0) {
            throw new IllegalArgumentException("unknown pipeline step: " + currentStep);
        }
        stepProgress.put(currentStep, "skip".equals(normalizedAction) ? "skipped" : "completed");
        history.add(historyItem(normalizedAction, currentStep, feedback, ""));

        boolean finishNow = "execute".equals(normalizedAction) || currentIndex == STEPS.size() - 1;
        if (finishNow) {
            state.put("status", "completed");
            state.put("current_step", "");
            state.put("step_progress", stepProgress);
            state.put("step_results", stepResults);
            state.put("history", history);
            save(workspaceId, state);
            return state;
        }

        String nextStep = STEPS.get(currentIndex + 1);
        stepProgress.put(nextStep, "in_progress");
        Map<String, Object> nextResult = llmService.analyzePipelineStep(nextStep, writeJson(stepResults.get(currentStep)), feedback == null ? "" : feedback);
        stepResults.put(nextStep, nextResult);

        state.put("status", "running");
        state.put("current_step", nextStep);
        state.put("step_progress", stepProgress);
        state.put("step_results", stepResults);
        state.put("history", history);
        save(workspaceId, state);
        return state;
    }

    private Map<String, Object> historyItem(String action, String step, String feedback, String note) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("timestamp", Instant.now().toString());
        item.put("action", action);
        item.put("step", step);
        item.put("feedback", feedback == null ? "" : feedback);
        item.put("note", note == null ? "" : note);
        return item;
    }

    private void save(String workspaceId, Map<String, Object> state) {
        AgentStateEntity entity = new AgentStateEntity();
        entity.setStateKey(stateKey(workspaceId));
        entity.setPayload(writeJson(state));
        entity.setUpdatedAt(Instant.now().toString());
        agentStateMapper.upsert(entity);
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
}
