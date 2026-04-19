package com.pmagent.backend.application.insight;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pmagent.backend.infrastructure.entity.InsightSnapshotEntity;
import com.pmagent.backend.infrastructure.entity.ManagedMemberEntity;
import com.pmagent.backend.infrastructure.entity.ModuleEntryEntity;
import com.pmagent.backend.infrastructure.mapper.InsightSnapshotMapper;
import com.pmagent.backend.infrastructure.mapper.ManagedMemberMapper;
import com.pmagent.backend.infrastructure.mapper.ModuleEntryMapper;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class InsightService {

    private final ManagedMemberMapper managedMemberMapper;
    private final ModuleEntryMapper moduleEntryMapper;
    private final InsightSnapshotMapper insightSnapshotMapper;
    private final ObjectMapper objectMapper;

    public InsightService(ManagedMemberMapper managedMemberMapper,
                          ModuleEntryMapper moduleEntryMapper,
                          InsightSnapshotMapper insightSnapshotMapper,
                          ObjectMapper objectMapper) {
        this.managedMemberMapper = managedMemberMapper;
        this.moduleEntryMapper = moduleEntryMapper;
        this.insightSnapshotMapper = insightSnapshotMapper;
        this.objectMapper = objectMapper;
    }

    public Map<String, Object> getInsights(String workspaceId) {
        List<ManagedMemberEntity> members = managedMemberMapper.listByWorkspaceId(workspaceId);
        List<ModuleEntryEntity> modules = moduleEntryMapper.listAllByWorkspaceId(workspaceId);

        List<Map<String, Object>> heatmap = new ArrayList<>();
        int highLoadCount = 0;
        for (ManagedMemberEntity member : members) {
            double workload = member.getWorkload() == null ? 0.0 : member.getWorkload().doubleValue();
            double capacity = member.getCapacity() == null ? 1.0 : member.getCapacity().doubleValue();
            String level = workload >= 0.9 ? "high" : (workload >= 0.6 ? "medium" : "low");
            if ("high".equals(level)) {
                highLoadCount++;
            }
            heatmap.add(Map.of(
                "memberName", member.getMemberName(),
                "workload", workload,
                "capacity", capacity,
                "level", level
            ));
        }
        heatmap.sort(Comparator.comparing(item -> String.valueOf(item.getOrDefault("memberName", ""))));

        Map<String, Integer> ownerModuleCount = new HashMap<>();
        for (ModuleEntryEntity module : modules) {
            String owner = normalize(module.getPrimaryOwner());
            if (owner.isEmpty()) {
                continue;
            }
            ownerModuleCount.put(owner, ownerModuleCount.getOrDefault(owner, 0) + 1);
        }

        List<Map<String, Object>> singlePoints = new ArrayList<>();
        for (Map.Entry<String, Integer> entry : ownerModuleCount.entrySet()) {
            if (entry.getValue() >= 2) {
                singlePoints.add(Map.of(
                    "memberName", entry.getKey(),
                    "moduleCount", entry.getValue(),
                    "severity", entry.getValue() >= 4 ? "high" : "medium",
                    "message", "成员承担多个模块主负责人，存在单点风险"
                ));
            }
        }
        singlePoints.sort(Comparator
            .comparing((Map<String, Object> item) -> String.valueOf(item.getOrDefault("severity", "")))
            .thenComparing(item -> String.valueOf(item.getOrDefault("memberName", ""))));

        List<Map<String, Object>> growthSuggestions = new ArrayList<>();
        Set<String> overloadedMembers = new HashSet<>();
        for (Map<String, Object> item : heatmap) {
            if ("high".equals(item.get("level"))) {
                overloadedMembers.add(String.valueOf(item.get("memberName")));
            }
        }
        for (ManagedMemberEntity member : members) {
            String name = normalize(member.getMemberName());
            if (overloadedMembers.contains(name)) {
                growthSuggestions.add(Map.of(
                    "memberName", name,
                    "suggestion", "建议安排 B 角协作与任务拆分，降低单人负载"
                ));
            }
        }
        growthSuggestions.sort(Comparator.comparing(item -> String.valueOf(item.getOrDefault("memberName", ""))));

        Map<String, Object> summary = new HashMap<>();
        summary.put("teamHealthScore", Math.max(0, 100 - highLoadCount * 15 - singlePoints.size() * 10));
        summary.put("highLoadCount", highLoadCount);
        summary.put("singlePointCount", singlePoints.size());
        summary.put("memberCount", members.size());
        summary.put("moduleCount", modules.size());

        persistSnapshot(workspaceId, heatmap, singlePoints, growthSuggestions, summary);

        Map<String, Object> response = new HashMap<>();
        response.put("workspaceId", workspaceId);
        response.put("heatmap", heatmap);
        response.put("singlePoints", singlePoints);
        response.put("growthSuggestions", growthSuggestions);
        response.put("summary", summary);
        return response;
    }

    public Map<String, Object> getInsightHistory(String workspaceId, int limit) {
        int validatedLimit = Math.max(limit, 1);
        List<Map<String, Object>> items = insightSnapshotMapper.listByWorkspace(workspaceId, validatedLimit)
            .stream()
            .map(this::toHistoryItem)
            .toList();
        return Map.of(
            "workspaceId", workspaceId,
            "items", items
        );
    }

    private void persistSnapshot(String workspaceId,
                                 List<Map<String, Object>> heatmap,
                                 List<Map<String, Object>> singlePoints,
                                 List<Map<String, Object>> growthSuggestions,
                                 Map<String, Object> summary) {
        InsightSnapshotEntity entity = new InsightSnapshotEntity();
        entity.setWorkspaceId(workspaceId);
        entity.setSnapshotAt(Instant.now().toString());
        entity.setHeatmapJson(writeJson(heatmap));
        entity.setSinglePointsJson(writeJson(singlePoints));
        entity.setGrowthSuggestionsJson(writeJson(growthSuggestions));
        entity.setSummaryJson(writeJson(summary));
        insightSnapshotMapper.insert(entity);
    }

    private Map<String, Object> toHistoryItem(InsightSnapshotEntity entity) {
        Map<String, Object> item = new HashMap<>();
        item.put("snapshotAt", entity.getSnapshotAt());
        item.put("summary", readJson(entity.getSummaryJson()));
        item.put("singlePoints", readJson(entity.getSinglePointsJson()));
        return item;
    }

    @SuppressWarnings("unchecked")
    private Object readJson(String json) {
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
            throw new IllegalArgumentException("failed to serialize insight payload", ex);
        }
    }

    private String normalize(String text) {
        return text == null ? "" : text.trim();
    }
}
