package com.pmagent.backend.infrastructure.mapper;

import com.pmagent.backend.infrastructure.entity.RequirementEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface RequirementMapper {

    @Select("""
        SELECT workspace_id, requirement_id, title, payload_json
        FROM requirements
        WHERE workspace_id = #{workspaceId}
        ORDER BY id ASC
        """)
    List<RequirementEntity> listByWorkspaceId(@Param("workspaceId") String workspaceId);
}
