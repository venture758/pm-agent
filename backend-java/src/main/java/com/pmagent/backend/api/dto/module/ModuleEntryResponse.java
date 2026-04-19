package com.pmagent.backend.api.dto.module;

import java.util.List;

public record ModuleEntryResponse(
    String moduleKey,
    String bigModule,
    String functionModule,
    String primaryOwner,
    List<String> backupOwners,
    List<String> familiarMembers,
    List<String> awareMembers,
    List<String> unfamiliarMembers,
    String updatedAt
) {
}
