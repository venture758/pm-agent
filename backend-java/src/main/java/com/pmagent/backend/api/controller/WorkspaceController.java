package com.pmagent.backend.api.controller;

import com.pmagent.backend.api.common.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.Map;

@RestController
@RequestMapping("/api/v2/workspaces")
public class WorkspaceController {

    @GetMapping("/{workspaceId}")
    public ApiResponse<Map<String, Object>> getWorkspace(@PathVariable String workspaceId) {
        return ApiResponse.success(
            Map.of(
                "workspaceId", workspaceId,
                "updatedAt", Instant.now().toString(),
                "note", "workspace endpoint scaffolded"
            )
        );
    }
}
