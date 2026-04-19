package com.pmagent.backend.infrastructure.mapper;

import com.pmagent.backend.infrastructure.entity.WorkspaceEntity;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface WorkspaceMapper {

    @Insert("""
        INSERT INTO workspaces (workspace_id, title, created_at, updated_at)
        VALUES (#{workspaceId}, #{title}, #{createdAt}, #{updatedAt})
        ON DUPLICATE KEY UPDATE
          title = VALUES(title),
          updated_at = VALUES(updated_at)
        """)
    int upsert(WorkspaceEntity entity);
}
