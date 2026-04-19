package com.pmagent.backend.infrastructure.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface RequirementWriteMapper {

    @Insert("""
        INSERT INTO requirements
        (workspace_id, requirement_id, title, source, priority, raw_text, complexity, risk, requirement_type, source_url, source_message, payload_json, created_at)
        VALUES
        (#{workspaceId}, #{requirementId}, #{title}, 'chat', #{priority}, #{rawText}, '中', '中', '', '', #{rawText}, #{payloadJson}, #{createdAt})
        ON DUPLICATE KEY UPDATE
          title = VALUES(title),
          priority = VALUES(priority),
          raw_text = VALUES(raw_text),
          payload_json = VALUES(payload_json)
        """)
    int upsert(@Param("workspaceId") String workspaceId,
               @Param("requirementId") String requirementId,
               @Param("title") String title,
               @Param("priority") String priority,
               @Param("rawText") String rawText,
               @Param("payloadJson") String payloadJson,
               @Param("createdAt") String createdAt);
}
