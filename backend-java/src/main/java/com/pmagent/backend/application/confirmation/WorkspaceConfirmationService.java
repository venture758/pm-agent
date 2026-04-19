package com.pmagent.backend.application.confirmation;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pmagent.backend.api.common.PageResult;
import com.pmagent.backend.infrastructure.entity.ConfirmationRecordEntity;
import com.pmagent.backend.infrastructure.entity.RecommendationEntity;
import com.pmagent.backend.infrastructure.mapper.ConfirmationRecordMapper;
import com.pmagent.backend.infrastructure.mapper.RecommendationMapper;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class WorkspaceConfirmationService {

    private final RecommendationMapper recommendationMapper;
    private final ConfirmationRecordMapper confirmationRecordMapper;
    private final ObjectMapper objectMapper;

    public WorkspaceConfirmationService(RecommendationMapper recommendationMapper,
                                        ConfirmationRecordMapper confirmationRecordMapper,
                                        ObjectMapper objectMapper) {
        this.recommendationMapper = recommendationMapper;
        this.confirmationRecordMapper = confirmationRecordMapper;
        this.objectMapper = objectMapper;
    }

    public Map<String, Object> confirm(String workspaceId, Map<String, Object> payload) {
        String sessionId = String.valueOf(payload.getOrDefault("session_id", UUID.randomUUID().toString()));
        @SuppressWarnings("unchecked")
        Map<String, Object> actions = (Map<String, Object>) payload.getOrDefault("actions", Map.of());

        List<RecommendationEntity> recommendations = recommendationMapper.listByWorkspaceId(workspaceId);
        Map<String, RecommendationEntity> recommendationById = new HashMap<>();
        for (RecommendationEntity recommendation : recommendations) {
            recommendationById.put(recommendation.getRequirementId(), recommendation);
        }

        List<Map<String, Object>> accepted = new ArrayList<>();
        for (Map.Entry<String, Object> entry : actions.entrySet()) {
            String requirementId = entry.getKey();
            @SuppressWarnings("unchecked")
            Map<String, Object> actionPayload = (Map<String, Object>) entry.getValue();
            String action = String.valueOf(actionPayload.getOrDefault("action", ""));
            if (!"accept".equalsIgnoreCase(action)) {
                continue;
            }
            RecommendationEntity recommendation = recommendationById.get(requirementId);
            if (recommendation == null) {
                continue;
            }
            accepted.add(readJson(recommendation.getPayloadJson()));
            recommendationMapper.deleteByRequirementId(workspaceId, requirementId);
        }

        String now = Instant.now().toString();
        ConfirmationRecordEntity entity = new ConfirmationRecordEntity();
        entity.setWorkspaceId(workspaceId);
        entity.setSessionId(sessionId);
        entity.setConfirmedCount(accepted.size());
        entity.setPayloadJson(writeJson(accepted));
        entity.setCreatedAt(now);
        confirmationRecordMapper.insert(entity);

        Map<String, Object> response = new HashMap<>();
        response.put("workspaceId", workspaceId);
        response.put("sessionId", sessionId);
        response.put("confirmedCount", accepted.size());
        response.put("confirmedAssignments", accepted);
        response.put("createdAt", now);
        return response;
    }

    public PageResult<Map<String, Object>> list(String workspaceId, int page, int pageSize) {
        int validatedPage = Math.max(page, 1);
        int validatedPageSize = Math.max(pageSize, 1);
        int offset = (validatedPage - 1) * validatedPageSize;

        long total = confirmationRecordMapper.countByWorkspaceId(workspaceId);
        List<Map<String, Object>> records = confirmationRecordMapper.listByWorkspaceId(workspaceId, offset, validatedPageSize)
            .stream()
            .map(record -> {
                Map<String, Object> item = new HashMap<>();
                item.put("sessionId", record.getSessionId());
                item.put("confirmedCount", record.getConfirmedCount());
                item.put("createdAt", record.getCreatedAt());
                item.put("payload", readAnyJson(record.getPayloadJson()));
                return item;
            })
            .toList();

        return new PageResult<>(validatedPage, validatedPageSize, total, records);
    }

    public Map<String, Object> listKnowledgeUpdateModuleDiffs(String workspaceId, String sessionId, String requirementId) {
        return Map.of(
            "workspaceId", workspaceId,
            "sessionId", sessionId,
            "requirementId", requirementId,
            "items", List.of()
        );
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> readJson(String json) {
        try {
            return objectMapper.readValue(json, Map.class);
        } catch (Exception ex) {
            throw new IllegalArgumentException("invalid recommendation payload json", ex);
        }
    }

    private Object readAnyJson(String json) {
        try {
            return objectMapper.readValue(json, Object.class);
        } catch (Exception ex) {
            return json;
        }
    }

    private String writeJson(Object payload) {
        try {
            return objectMapper.writeValueAsString(payload);
        } catch (Exception ex) {
            throw new IllegalArgumentException("failed to serialize confirmation payload", ex);
        }
    }
}
