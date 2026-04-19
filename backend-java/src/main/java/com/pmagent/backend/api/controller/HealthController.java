package com.pmagent.backend.api.controller;

import com.pmagent.backend.api.common.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class HealthController {

    @GetMapping("/api/v2/health")
    public ApiResponse<Map<String, String>> health() {
        return ApiResponse.success(Map.of("status", "ok"));
    }
}
