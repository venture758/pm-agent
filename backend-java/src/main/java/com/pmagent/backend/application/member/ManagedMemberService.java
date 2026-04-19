package com.pmagent.backend.application.member;

import com.pmagent.backend.api.dto.member.ManagedMemberRequest;
import com.pmagent.backend.api.dto.member.ManagedMemberResponse;
import com.pmagent.backend.infrastructure.entity.ManagedMemberEntity;
import com.pmagent.backend.infrastructure.mapper.ManagedMemberMapper;
import com.pmagent.backend.infrastructure.support.JsonListCodec;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

@Service
public class ManagedMemberService {

    private final ManagedMemberMapper managedMemberMapper;

    public ManagedMemberService(ManagedMemberMapper managedMemberMapper) {
        this.managedMemberMapper = managedMemberMapper;
    }

    public List<ManagedMemberResponse> list(String workspaceId) {
        return managedMemberMapper.listByWorkspaceId(workspaceId).stream().map(this::toResponse).toList();
    }

    public ManagedMemberResponse create(String workspaceId, ManagedMemberRequest request) {
        ManagedMemberEntity entity = fromRequest(workspaceId, request);
        int inserted = managedMemberMapper.insert(entity);
        if (inserted != 1) {
            throw new IllegalArgumentException("failed_to_create_member");
        }
        return toResponse(entity);
    }

    public ManagedMemberResponse update(String workspaceId, String memberName, ManagedMemberRequest request) {
        ManagedMemberEntity entity = fromRequest(workspaceId, request);
        entity.setMemberName(memberName);
        int updated = managedMemberMapper.update(entity);
        if (updated != 1) {
            throw new IllegalArgumentException("member_not_found: " + memberName);
        }
        return toResponse(entity);
    }

    public void delete(String workspaceId, String memberName) {
        int deleted = managedMemberMapper.delete(workspaceId, memberName);
        if (deleted != 1) {
            throw new IllegalArgumentException("member_not_found: " + memberName);
        }
    }

    private ManagedMemberEntity fromRequest(String workspaceId, ManagedMemberRequest request) {
        String now = Instant.now().toString();
        ManagedMemberEntity entity = new ManagedMemberEntity();
        entity.setWorkspaceId(workspaceId);
        entity.setMemberName(request.name());
        entity.setRole(request.role());
        entity.setSkillsJson(JsonListCodec.encode(request.skills()));
        entity.setExperienceLevel(request.experienceLevel());
        entity.setWorkload(BigDecimal.valueOf(request.workload()));
        entity.setCapacity(BigDecimal.valueOf(request.capacity()));
        entity.setConstraintsJson(JsonListCodec.encode(request.constraints()));
        entity.setUpdatedAt(now);
        return entity;
    }

    private ManagedMemberResponse toResponse(ManagedMemberEntity entity) {
        return new ManagedMemberResponse(
            entity.getMemberName(),
            entity.getRole(),
            JsonListCodec.decode(entity.getSkillsJson()),
            entity.getExperienceLevel(),
            entity.getWorkload() == null ? 0.0 : entity.getWorkload().doubleValue(),
            entity.getCapacity() == null ? 0.0 : entity.getCapacity().doubleValue(),
            JsonListCodec.decode(entity.getConstraintsJson()),
            entity.getUpdatedAt()
        );
    }
}
