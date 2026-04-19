package com.pmagent.backend.api.controller;

import com.pmagent.backend.api.common.ApiResponse;
import com.pmagent.backend.api.common.PageResult;
import com.pmagent.backend.application.confirmation.WorkspaceConfirmationService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v2/workspaces/{workspaceId}/confirmations")
public class WorkspaceConfirmationController {

    private final WorkspaceConfirmationService workspaceConfirmationService;

    public WorkspaceConfirmationController(WorkspaceConfirmationService workspaceConfirmationService) {
        this.workspaceConfirmationService = workspaceConfirmationService;
    }

    @GetMapping
    public ApiResponse<PageResult<Map<String, Object>>> list(@PathVariable String workspaceId,
                                                             @RequestParam(defaultValue = "1") int page,
                                                             @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.success(workspaceConfirmationService.list(workspaceId, page, pageSize));
    }

    @PostMapping
    public ApiResponse<Map<String, Object>> confirm(@PathVariable String workspaceId, @RequestBody Map<String, Object> payload) {
        return ApiResponse.success(workspaceConfirmationService.confirm(workspaceId, payload));
    }

    @GetMapping("/{sessionId}/requirements/{requirementId}/knowledge-update-modules")
    public ApiResponse<Map<String, Object>> moduleDiffs(@PathVariable String workspaceId,
                                                        @PathVariable String sessionId,
                                                        @PathVariable String requirementId) {
        return ApiResponse.success(
            workspaceConfirmationService.listKnowledgeUpdateModuleDiffs(workspaceId, sessionId, requirementId)
        );
    }
}
