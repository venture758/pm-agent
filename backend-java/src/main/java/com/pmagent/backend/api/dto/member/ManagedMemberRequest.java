package com.pmagent.backend.api.dto.member;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.util.List;

public record ManagedMemberRequest(
    @NotBlank(message = "name is required")
    String name,
    @NotBlank(message = "role is required")
    String role,
    @NotNull(message = "skills is required")
    List<String> skills,
    @NotBlank(message = "experienceLevel is required")
    String experienceLevel,
    @NotNull(message = "workload is required")
    @DecimalMin(value = "0.0", message = "workload must be >= 0")
    @DecimalMax(value = "1.0", message = "workload must be <= 1")
    Double workload,
    @NotNull(message = "capacity is required")
    @DecimalMin(value = "0.0", message = "capacity must be >= 0")
    @DecimalMax(value = "10.0", message = "capacity must be <= 10")
    Double capacity,
    List<String> constraints
) {
}
