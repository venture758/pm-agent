package com.pmagent.backend.infrastructure.mapper;

import com.pmagent.backend.infrastructure.entity.ManagedMemberEntity;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

@Mapper
public interface ManagedMemberMapper {

    @Select("""
        SELECT workspace_id, member_name, role, skills_json, experience_level, workload, capacity, constraints_json, updated_at
        FROM workspace_managed_members
        WHERE workspace_id = #{workspaceId}
        ORDER BY member_name ASC
        """)
    List<ManagedMemberEntity> listByWorkspaceId(@Param("workspaceId") String workspaceId);

    @Insert("""
        INSERT INTO workspace_managed_members
        (workspace_id, member_name, role, skills_json, experience_level, workload, capacity, constraints_json, updated_at)
        VALUES
        (#{workspaceId}, #{memberName}, #{role}, CAST(#{skillsJson} AS JSON), #{experienceLevel}, #{workload}, #{capacity}, CAST(#{constraintsJson} AS JSON), #{updatedAt})
        """)
    int insert(ManagedMemberEntity entity);

    @Update("""
        UPDATE workspace_managed_members
        SET role = #{role},
            skills_json = CAST(#{skillsJson} AS JSON),
            experience_level = #{experienceLevel},
            workload = #{workload},
            capacity = #{capacity},
            constraints_json = CAST(#{constraintsJson} AS JSON),
            updated_at = #{updatedAt}
        WHERE workspace_id = #{workspaceId}
          AND member_name = #{memberName}
        """)
    int update(ManagedMemberEntity entity);

    @Delete("""
        DELETE FROM workspace_managed_members
        WHERE workspace_id = #{workspaceId}
          AND member_name = #{memberName}
        """)
    int delete(@Param("workspaceId") String workspaceId, @Param("memberName") String memberName);
}
