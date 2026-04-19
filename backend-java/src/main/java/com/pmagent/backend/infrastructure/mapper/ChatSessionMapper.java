package com.pmagent.backend.infrastructure.mapper;

import com.pmagent.backend.infrastructure.entity.ChatSessionEntity;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

@Mapper
public interface ChatSessionMapper {

    @Select("""
        SELECT session_id, workspace_id, created_at, last_active_at, status, last_message_preview
        FROM chat_sessions
        WHERE workspace_id = #{workspaceId}
          AND status = 'active'
        ORDER BY last_active_at DESC
        LIMIT 1
        """)
    ChatSessionEntity findActive(@Param("workspaceId") String workspaceId);

    @Select("""
        SELECT session_id, workspace_id, created_at, last_active_at, status, last_message_preview
        FROM chat_sessions
        WHERE workspace_id = #{workspaceId}
        ORDER BY last_active_at DESC
        """)
    List<ChatSessionEntity> listByWorkspace(@Param("workspaceId") String workspaceId);

    @Select("""
        SELECT session_id, workspace_id, created_at, last_active_at, status, last_message_preview
        FROM chat_sessions
        WHERE workspace_id = #{workspaceId}
          AND session_id = #{sessionId}
        LIMIT 1
        """)
    ChatSessionEntity get(@Param("workspaceId") String workspaceId, @Param("sessionId") String sessionId);

    @Insert("""
        INSERT INTO chat_sessions (session_id, workspace_id, created_at, last_active_at, status, last_message_preview)
        VALUES (#{sessionId}, #{workspaceId}, #{createdAt}, #{lastActiveAt}, #{status}, #{lastMessagePreview})
        """)
    int insert(ChatSessionEntity entity);

    @Update("""
        UPDATE chat_sessions
        SET status = 'archived'
        WHERE workspace_id = #{workspaceId}
          AND status = 'active'
        """)
    int archiveActive(@Param("workspaceId") String workspaceId);

    @Update("""
        UPDATE chat_sessions
        SET last_active_at = #{lastActiveAt},
            last_message_preview = #{lastMessagePreview}
        WHERE workspace_id = #{workspaceId}
          AND session_id = #{sessionId}
        """)
    int touch(@Param("workspaceId") String workspaceId,
              @Param("sessionId") String sessionId,
              @Param("lastActiveAt") String lastActiveAt,
              @Param("lastMessagePreview") String lastMessagePreview);

    @Delete("""
        DELETE FROM chat_sessions
        WHERE workspace_id = #{workspaceId}
          AND session_id = #{sessionId}
        """)
    int delete(@Param("workspaceId") String workspaceId, @Param("sessionId") String sessionId);
}
