package com.pmagent.backend.application.module;

import com.pmagent.backend.api.common.PageResult;
import com.pmagent.backend.api.dto.module.ModuleEntryRequest;
import com.pmagent.backend.api.dto.module.ModuleEntryResponse;
import com.pmagent.backend.infrastructure.entity.ModuleEntryEntity;
import com.pmagent.backend.infrastructure.mapper.ModuleEntryMapper;
import com.pmagent.backend.infrastructure.support.JsonListCodec;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;

@Service
public class ModuleEntryService {

    private final ModuleEntryMapper moduleEntryMapper;

    public ModuleEntryService(ModuleEntryMapper moduleEntryMapper) {
        this.moduleEntryMapper = moduleEntryMapper;
    }

    public PageResult<ModuleEntryResponse> list(String workspaceId,
                                                int page,
                                                int pageSize,
                                                String bigModule,
                                                String functionModule,
                                                String primaryOwner) {
        int validatedPage = Math.max(page, 1);
        int validatedPageSize = Math.max(pageSize, 1);
        int offset = (validatedPage - 1) * validatedPageSize;

        long total = moduleEntryMapper.countByWorkspaceWithFilters(workspaceId, bigModule, functionModule, primaryOwner);
        List<ModuleEntryResponse> items = moduleEntryMapper
            .listByWorkspaceWithFilters(workspaceId, bigModule, functionModule, primaryOwner, offset, validatedPageSize)
            .stream()
            .map(this::toResponse)
            .toList();
        return new PageResult<>(validatedPage, validatedPageSize, total, items);
    }

    public ModuleEntryResponse create(String workspaceId, ModuleEntryRequest request) {
        ModuleEntryEntity entity = fromRequest(workspaceId, request);
        int inserted = moduleEntryMapper.insert(entity);
        if (inserted != 1) {
            throw new IllegalArgumentException("failed_to_create_module_entry");
        }
        return toResponse(entity);
    }

    public ModuleEntryResponse update(String workspaceId, String moduleKey, ModuleEntryRequest request) {
        ModuleEntryEntity entity = fromRequest(workspaceId, request);
        entity.setModuleKey(moduleKey);
        int updated = moduleEntryMapper.update(entity);
        if (updated != 1) {
            throw new IllegalArgumentException("module_entry_not_found: " + moduleKey);
        }
        return toResponse(entity);
    }

    public void delete(String workspaceId, String moduleKey) {
        int deleted = moduleEntryMapper.delete(workspaceId, moduleKey);
        if (deleted != 1) {
            throw new IllegalArgumentException("module_entry_not_found: " + moduleKey);
        }
    }

    private ModuleEntryEntity fromRequest(String workspaceId, ModuleEntryRequest request) {
        String now = Instant.now().toString();
        ModuleEntryEntity entity = new ModuleEntryEntity();
        entity.setWorkspaceId(workspaceId);
        entity.setBigModule(request.bigModule());
        entity.setFunctionModule(request.functionModule());
        entity.setModuleKey(request.bigModule() + "::" + request.functionModule());
        entity.setPrimaryOwner(request.primaryOwner());
        entity.setBackupOwnersJson(JsonListCodec.encode(request.backupOwners()));
        entity.setFamiliarMembersJson(JsonListCodec.encode(request.familiarMembers()));
        entity.setAwareMembersJson(JsonListCodec.encode(request.awareMembers()));
        entity.setUnfamiliarMembersJson(JsonListCodec.encode(request.unfamiliarMembers()));
        entity.setUpdatedAt(now);
        return entity;
    }

    private ModuleEntryResponse toResponse(ModuleEntryEntity entity) {
        return new ModuleEntryResponse(
            entity.getModuleKey(),
            entity.getBigModule(),
            entity.getFunctionModule(),
            entity.getPrimaryOwner(),
            JsonListCodec.decode(entity.getBackupOwnersJson()),
            JsonListCodec.decode(entity.getFamiliarMembersJson()),
            JsonListCodec.decode(entity.getAwareMembersJson()),
            JsonListCodec.decode(entity.getUnfamiliarMembersJson()),
            entity.getUpdatedAt()
        );
    }
}
