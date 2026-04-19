package com.pmagent.backend.api.dto.module;

import jakarta.validation.constraints.NotBlank;

import java.util.List;

public record ModuleEntryRequest(
    @NotBlank(message = "bigModule is required")
    String bigModule,
    @NotBlank(message = "functionModule is required")
    String functionModule,
    @NotBlank(message = "primaryOwner is required")
    String primaryOwner,
    List<String> backupOwners,
    List<String> familiarMembers,
    List<String> awareMembers,
    List<String> unfamiliarMembers
) {
}
