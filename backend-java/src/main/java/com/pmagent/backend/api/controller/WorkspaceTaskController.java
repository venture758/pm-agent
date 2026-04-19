package com.pmagent.backend.api.controller;

import com.pmagent.backend.api.common.ApiResponse;
import com.pmagent.backend.api.common.PageResult;
import com.pmagent.backend.application.delivery.DeliveryService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v2/workspaces/{workspaceId}/tasks")
public class WorkspaceTaskController {

    private final DeliveryService deliveryService;

    public WorkspaceTaskController(DeliveryService deliveryService) {
        this.deliveryService = deliveryService;
    }

    @GetMapping
    public ApiResponse<PageResult<Map<String, Object>>> list(@PathVariable String workspaceId,
                                                             @RequestParam(defaultValue = "1") int page,
                                                             @RequestParam(defaultValue = "20") int pageSize,
                                                             @RequestParam(defaultValue = "") String owner,
                                                             @RequestParam(defaultValue = "") String status,
                                                             @RequestParam(name = "project_name", defaultValue = "") String projectName) {
        return ApiResponse.success(deliveryService.listTasks(workspaceId, page, pageSize, owner, status, projectName));
    }
}
