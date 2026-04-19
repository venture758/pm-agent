package com.pmagent.backend.api.controller;

import com.pmagent.backend.api.common.ApiResponse;
import com.pmagent.backend.api.common.PageResult;
import com.pmagent.backend.api.dto.module.ModuleEntryRequest;
import com.pmagent.backend.api.dto.module.ModuleEntryResponse;
import com.pmagent.backend.application.module.ModuleEntryService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@Validated
@RequestMapping("/api/v2/workspaces/{workspaceId}/modules")
public class WorkspaceModuleController {

    private final ModuleEntryService moduleEntryService;

    public WorkspaceModuleController(ModuleEntryService moduleEntryService) {
        this.moduleEntryService = moduleEntryService;
    }

    @GetMapping
    public ApiResponse<PageResult<ModuleEntryResponse>> list(@PathVariable String workspaceId,
                                                             @RequestParam(defaultValue = "1") @Min(1) int page,
                                                             @RequestParam(defaultValue = "20") @Min(1) int pageSize,
                                                             @RequestParam(defaultValue = "") String bigModule,
                                                             @RequestParam(defaultValue = "") String functionModule,
                                                             @RequestParam(defaultValue = "") String primaryOwner) {
        return ApiResponse.success(moduleEntryService.list(workspaceId, page, pageSize, bigModule, functionModule, primaryOwner));
    }

    @PostMapping
    public ApiResponse<ModuleEntryResponse> create(@PathVariable String workspaceId, @Valid @RequestBody ModuleEntryRequest request) {
        return ApiResponse.success(moduleEntryService.create(workspaceId, request));
    }

    @PutMapping("/{moduleKey}")
    public ApiResponse<ModuleEntryResponse> update(@PathVariable String workspaceId,
                                                   @PathVariable String moduleKey,
                                                   @Valid @RequestBody ModuleEntryRequest request) {
        return ApiResponse.success(moduleEntryService.update(workspaceId, moduleKey, request));
    }

    @DeleteMapping("/{moduleKey}")
    public ApiResponse<Void> delete(@PathVariable String workspaceId, @PathVariable String moduleKey) {
        moduleEntryService.delete(workspaceId, moduleKey);
        return ApiResponse.success(null);
    }
}
