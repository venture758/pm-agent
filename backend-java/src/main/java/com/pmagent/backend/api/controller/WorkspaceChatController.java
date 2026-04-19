package com.pmagent.backend.api.controller;

import com.pmagent.backend.api.common.ApiResponse;
import com.pmagent.backend.application.chat.ChatService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v2/workspaces/{workspaceId}/chat")
public class WorkspaceChatController {

    private final ChatService chatService;

    public WorkspaceChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping
    public ApiResponse<Map<String, Object>> send(@PathVariable String workspaceId, @RequestBody Map<String, Object> payload) {
        return ApiResponse.success(chatService.send(workspaceId, payload));
    }

    @PostMapping("/sessions")
    public ApiResponse<Map<String, Object>> createSession(@PathVariable String workspaceId, @RequestBody Map<String, Object> payload) {
        return ApiResponse.success(chatService.createSession(workspaceId, payload));
    }

    @GetMapping("/sessions")
    public ApiResponse<Map<String, Object>> listSessions(@PathVariable String workspaceId) {
        return ApiResponse.success(chatService.listSessions(workspaceId));
    }

    @GetMapping("/sessions/{sessionId}")
    public ApiResponse<Map<String, Object>> getSession(@PathVariable String workspaceId, @PathVariable String sessionId) {
        return ApiResponse.success(chatService.getSession(workspaceId, sessionId));
    }

    @DeleteMapping("/sessions/{sessionId}")
    public ApiResponse<Map<String, Object>> deleteSession(@PathVariable String workspaceId, @PathVariable String sessionId) {
        return ApiResponse.success(chatService.deleteSession(workspaceId, sessionId));
    }
}
