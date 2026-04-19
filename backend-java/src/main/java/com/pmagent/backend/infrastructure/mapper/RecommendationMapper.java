package com.pmagent.backend.infrastructure.mapper;

import com.pmagent.backend.infrastructure.entity.RecommendationEntity;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface RecommendationMapper {

    @Select("""
        SELECT workspace_id, requirement_id, payload_json, created_at, updated_at
        FROM workspace_recommendations
        WHERE workspace_id = #{workspaceId}
        ORDER BY requirement_id ASC
        """)
    List<RecommendationEntity> listByWorkspaceId(@Param("workspaceId") String workspaceId);

    @Insert("""
        INSERT INTO workspace_recommendations (workspace_id, requirement_id, payload_json, created_at, updated_at)
        VALUES (#{workspaceId}, #{requirementId}, #{payloadJson}, #{createdAt}, #{updatedAt})
        ON DUPLICATE KEY UPDATE
          payload_json = VALUES(payload_json),
          updated_at = VALUES(updated_at)
        """)
    int upsert(RecommendationEntity entity);

    @Delete("""
        DELETE FROM workspace_recommendations
        WHERE workspace_id = #{workspaceId}
          AND requirement_id = #{requirementId}
        """)
    int deleteByRequirementId(@Param("workspaceId") String workspaceId, @Param("requirementId") String requirementId);

    @Delete("""
        <script>
        DELETE FROM workspace_recommendations
        WHERE workspace_id = #{workspaceId}
          AND requirement_id IN
          <foreach collection="requirementIds" item="item" open="(" separator="," close=")">
            #{item}
          </foreach>
        </script>
        """)
    int batchDelete(@Param("workspaceId") String workspaceId, @Param("requirementIds") List<String> requirementIds);
}
