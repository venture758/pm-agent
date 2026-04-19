package com.pmagent.backend.api.controller;

import com.pmagent.backend.api.common.ApiResponse;
import com.pmagent.backend.application.insight.InsightService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v2/workspaces/{workspaceId}/insights")
public class WorkspaceInsightController {

    private final InsightService insightService;

    public WorkspaceInsightController(InsightService insightService) {
        this.insightService = insightService;
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> get(@PathVariable String workspaceId) {
        return ApiResponse.success(insightService.getInsights(workspaceId));
    }

    @GetMapping("/history")
    public ApiResponse<Map<String, Object>> history(@PathVariable String workspaceId,
                                                    @RequestParam(defaultValue = "20") int limit) {
        return ApiResponse.success(insightService.getInsightHistory(workspaceId, limit));
    }
}
