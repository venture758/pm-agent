package com.pmagent.backend.api.controller;

import com.pmagent.backend.api.common.ApiResponse;
import com.pmagent.backend.application.delivery.DeliveryService;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api/v2/workspaces/{workspaceId}/uploads")
public class WorkspaceUploadController {

    private final DeliveryService deliveryService;

    public WorkspaceUploadController(DeliveryService deliveryService) {
        this.deliveryService = deliveryService;
    }

    @PostMapping("/module-knowledge")
    public ApiResponse<Map<String, Object>> uploadModuleKnowledge(@PathVariable String workspaceId, @RequestPart("file") MultipartFile file) {
        return ApiResponse.success(deliveryService.importModuleKnowledge(workspaceId, file));
    }

    @PostMapping("/platform-sync")
    public ApiResponse<Map<String, Object>> syncPlatform(@PathVariable String workspaceId,
                                                         @RequestPart("story_file") MultipartFile storyFile,
                                                         @RequestPart("task_file") MultipartFile taskFile) {
        return ApiResponse.success(deliveryService.syncPlatform(workspaceId, storyFile, taskFile));
    }

    @PostMapping("/story-only")
    public ApiResponse<Map<String, Object>> storyOnly(@PathVariable String workspaceId, @RequestPart("story_file") MultipartFile storyFile) {
        return ApiResponse.success(deliveryService.importStories(workspaceId, storyFile));
    }

    @PostMapping("/task-only")
    public ApiResponse<Map<String, Object>> taskOnly(@PathVariable String workspaceId, @RequestPart("task_file") MultipartFile taskFile) {
        return ApiResponse.success(deliveryService.importTasks(workspaceId, taskFile));
    }
}
