package com.pmagent.backend.api.controller;

import com.pmagent.backend.api.common.ApiResponse;
import com.pmagent.backend.api.dto.member.ManagedMemberRequest;
import com.pmagent.backend.api.dto.member.ManagedMemberResponse;
import com.pmagent.backend.application.member.ManagedMemberService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v2/workspaces/{workspaceId}/members")
public class WorkspaceMemberController {

    private final ManagedMemberService managedMemberService;

    public WorkspaceMemberController(ManagedMemberService managedMemberService) {
        this.managedMemberService = managedMemberService;
    }

    @GetMapping
    public ApiResponse<List<ManagedMemberResponse>> list(@PathVariable String workspaceId) {
        return ApiResponse.success(managedMemberService.list(workspaceId));
    }

    @PostMapping
    public ApiResponse<ManagedMemberResponse> create(@PathVariable String workspaceId, @Valid @RequestBody ManagedMemberRequest request) {
        return ApiResponse.success(managedMemberService.create(workspaceId, request));
    }

    @PutMapping("/{memberName}")
    public ApiResponse<ManagedMemberResponse> update(@PathVariable String workspaceId,
                                                     @PathVariable String memberName,
                                                     @Valid @RequestBody ManagedMemberRequest request) {
        return ApiResponse.success(managedMemberService.update(workspaceId, memberName, request));
    }

    @DeleteMapping("/{memberName}")
    public ApiResponse<Void> delete(@PathVariable String workspaceId, @PathVariable String memberName) {
        managedMemberService.delete(workspaceId, memberName);
        return ApiResponse.success(null);
    }
}
