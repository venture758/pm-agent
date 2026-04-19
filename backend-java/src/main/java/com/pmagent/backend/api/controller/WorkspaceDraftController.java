package com.pmagent.backend.api.controller;

import com.pmagent.backend.api.common.ApiResponse;
import com.pmagent.backend.application.workspace.WorkspaceDraftService;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v2/workspaces/{workspaceId}/draft")
public class WorkspaceDraftController {

    private final WorkspaceDraftService workspaceDraftService;

    public WorkspaceDraftController(WorkspaceDraftService workspaceDraftService) {
        this.workspaceDraftService = workspaceDraftService;
    }

    @PutMapping
    public ApiResponse<Map<String, Object>> updateDraft(@PathVariable String workspaceId, @RequestBody Map<String, Object> payload) {
        return ApiResponse.success(workspaceDraftService.updateDraft(workspaceId, payload));
    }
}
