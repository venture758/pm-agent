package com.pmagent.backend.api.dto.member;

import java.util.List;

public record ManagedMemberResponse(
    String name,
    String role,
    List<String> skills,
    String experienceLevel,
    double workload,
    double capacity,
    List<String> constraints,
    String updatedAt
) {
}
