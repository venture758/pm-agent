package com.pmagent.backend.api.controller;

import com.pmagent.backend.api.common.ApiResponse;
import com.pmagent.backend.application.recommendation.WorkspaceRecommendationService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v2/workspaces/{workspaceId}/recommendations")
public class WorkspaceRecommendationController {

    private final WorkspaceRecommendationService workspaceRecommendationService;

    public WorkspaceRecommendationController(WorkspaceRecommendationService workspaceRecommendationService) {
        this.workspaceRecommendationService = workspaceRecommendationService;
    }

    @PostMapping
    public ApiResponse<Map<String, Object>> generate(@PathVariable String workspaceId) {
        return ApiResponse.success(workspaceRecommendationService.generate(workspaceId));
    }

    @DeleteMapping("/{requirementId}")
    public ApiResponse<Void> delete(@PathVariable String workspaceId, @PathVariable String requirementId) {
        workspaceRecommendationService.delete(workspaceId, requirementId);
        return ApiResponse.success(null);
    }

    @PostMapping("/batch-delete")
    public ApiResponse<Map<String, Object>> batchDelete(@PathVariable String workspaceId, @RequestBody Map<String, Object> payload) {
        Object listObj = payload.getOrDefault("requirement_ids", java.util.List.of());
        @SuppressWarnings("unchecked")
        java.util.List<String> requirementIds = (java.util.List<String>) listObj;
        return ApiResponse.success(workspaceRecommendationService.batchDelete(workspaceId, requirementIds));
    }
}
