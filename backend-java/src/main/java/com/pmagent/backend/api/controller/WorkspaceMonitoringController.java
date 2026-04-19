package com.pmagent.backend.api.controller;

import com.pmagent.backend.api.common.ApiResponse;
import com.pmagent.backend.application.monitoring.MonitoringService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v2/workspaces/{workspaceId}/monitoring")
public class WorkspaceMonitoringController {

    private final MonitoringService monitoringService;

    public WorkspaceMonitoringController(MonitoringService monitoringService) {
        this.monitoringService = monitoringService;
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> get(@PathVariable String workspaceId) {
        return ApiResponse.success(monitoringService.getMonitoring(workspaceId));
    }
}
