package com.pmagent.backend.api.controller;

import com.pmagent.backend.api.common.ApiResponse;
import com.pmagent.backend.application.pipeline.PipelineService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v2/workspaces/{workspaceId}/pipeline")
public class WorkspacePipelineController {

    private final PipelineService pipelineService;

    public WorkspacePipelineController(PipelineService pipelineService) {
        this.pipelineService = pipelineService;
    }

    @PostMapping("/start")
    public ApiResponse<Map<String, Object>> start(@PathVariable String workspaceId, @RequestBody Map<String, Object> payload) {
        String message = String.valueOf(payload.getOrDefault("message", ""));
        return ApiResponse.success(pipelineService.start(workspaceId, message));
    }

    @GetMapping("/state")
    public ApiResponse<Map<String, Object>> state(@PathVariable String workspaceId) {
        return ApiResponse.success(pipelineService.state(workspaceId));
    }

    @PostMapping("/confirm")
    public ApiResponse<Map<String, Object>> confirm(@PathVariable String workspaceId, @RequestBody Map<String, Object> payload) {
        String action = String.valueOf(payload.getOrDefault("action", "confirm"));
        Object modifications = payload.get("modifications");
        String feedback = String.valueOf(payload.getOrDefault("feedback", ""));
        return ApiResponse.success(pipelineService.confirm(workspaceId, action, modifications, feedback));
    }
}
