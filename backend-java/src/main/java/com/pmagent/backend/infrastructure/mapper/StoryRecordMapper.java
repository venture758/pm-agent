package com.pmagent.backend.infrastructure.mapper;

import com.pmagent.backend.infrastructure.entity.StoryRecordEntity;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface StoryRecordMapper {

    @Insert("""
        INSERT INTO workspace_story_records
        (workspace_id, user_story_code, user_story_name, status, owner_names, tester_names, priority, detail_url, project_name, developer_names, imported_at, updated_at)
        VALUES
        (#{workspaceId}, #{userStoryCode}, #{userStoryName}, #{status}, #{ownerNames}, #{testerNames}, #{priority}, #{detailUrl}, #{projectName}, #{developerNames}, #{importedAt}, #{updatedAt})
        ON DUPLICATE KEY UPDATE
          user_story_name = VALUES(user_story_name),
          status = VALUES(status),
          owner_names = VALUES(owner_names),
          tester_names = VALUES(tester_names),
          priority = VALUES(priority),
          detail_url = VALUES(detail_url),
          project_name = VALUES(project_name),
          developer_names = VALUES(developer_names),
          updated_at = VALUES(updated_at)
        """)
    int upsert(StoryRecordEntity entity);

    @Select("""
        <script>
        SELECT COUNT(1)
        FROM workspace_story_records
        WHERE workspace_id = #{workspaceId}
        <if test="keyword != null and keyword != ''">
          AND (user_story_code LIKE CONCAT('%', #{keyword}, '%')
            OR user_story_name LIKE CONCAT('%', #{keyword}, '%'))
        </if>
        </script>
        """)
    long countByWorkspace(@Param("workspaceId") String workspaceId, @Param("keyword") String keyword);

    @Select("""
        <script>
        SELECT workspace_id, user_story_code, user_story_name, status, owner_names, tester_names, priority, detail_url, project_name, developer_names, imported_at, updated_at
        FROM workspace_story_records
        WHERE workspace_id = #{workspaceId}
        <if test="keyword != null and keyword != ''">
          AND (user_story_code LIKE CONCAT('%', #{keyword}, '%')
            OR user_story_name LIKE CONCAT('%', #{keyword}, '%'))
        </if>
        ORDER BY id DESC
        LIMIT #{pageSize} OFFSET #{offset}
        </script>
        """)
    List<StoryRecordEntity> listByWorkspace(@Param("workspaceId") String workspaceId,
                                            @Param("keyword") String keyword,
                                            @Param("offset") int offset,
                                            @Param("pageSize") int pageSize);

    @Select("""
        SELECT workspace_id, user_story_code, user_story_name, status, owner_names, tester_names, priority, detail_url, project_name, developer_names, imported_at, updated_at
        FROM workspace_story_records
        WHERE workspace_id = #{workspaceId}
        ORDER BY id DESC
        """)
    List<StoryRecordEntity> listAllByWorkspace(@Param("workspaceId") String workspaceId);
}
