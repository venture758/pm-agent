package com.pmagent.backend.infrastructure.mapper;

import com.pmagent.backend.infrastructure.entity.ChatMessageEntity;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface ChatMessageMapper {

    @Select("""
        SELECT COALESCE(MAX(seq), 0) + 1
        FROM chat_messages
        WHERE session_id = #{sessionId}
        """)
    int nextSeq(@Param("sessionId") String sessionId);

    @Insert("""
        INSERT INTO chat_messages (workspace_id, session_id, seq, role, content, timestamp, parsed_requirements_json)
        VALUES (#{workspaceId}, #{sessionId}, #{seq}, #{role}, #{content}, #{timestamp}, #{parsedRequirementsJson})
        """)
    int insert(ChatMessageEntity entity);

    @Select("""
        SELECT workspace_id, session_id, seq, role, content, timestamp, parsed_requirements_json
        FROM chat_messages
        WHERE workspace_id = #{workspaceId}
          AND session_id = #{sessionId}
        ORDER BY seq ASC
        """)
    List<ChatMessageEntity> list(@Param("workspaceId") String workspaceId, @Param("sessionId") String sessionId);

    @Delete("""
        DELETE FROM chat_messages
        WHERE workspace_id = #{workspaceId}
          AND session_id = #{sessionId}
        """)
    int deleteBySession(@Param("workspaceId") String workspaceId, @Param("sessionId") String sessionId);
}
