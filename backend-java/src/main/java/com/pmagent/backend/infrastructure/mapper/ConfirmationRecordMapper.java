package com.pmagent.backend.infrastructure.mapper;

import com.pmagent.backend.infrastructure.entity.ConfirmationRecordEntity;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface ConfirmationRecordMapper {

    @Insert("""
        INSERT INTO workspace_confirmation_records (workspace_id, session_id, confirmed_count, payload_json, created_at)
        VALUES (#{workspaceId}, #{sessionId}, #{confirmedCount}, #{payloadJson}, #{createdAt})
        """)
    int insert(ConfirmationRecordEntity entity);

    @Select("""
        SELECT workspace_id, session_id, confirmed_count, payload_json, created_at
        FROM workspace_confirmation_records
        WHERE workspace_id = #{workspaceId}
        ORDER BY id DESC
        LIMIT #{pageSize} OFFSET #{offset}
        """)
    List<ConfirmationRecordEntity> listByWorkspaceId(@Param("workspaceId") String workspaceId,
                                                     @Param("offset") int offset,
                                                     @Param("pageSize") int pageSize);

    @Select("""
        SELECT COUNT(1)
        FROM workspace_confirmation_records
        WHERE workspace_id = #{workspaceId}
        """)
    long countByWorkspaceId(@Param("workspaceId") String workspaceId);
}
