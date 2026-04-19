package com.pmagent.backend.infrastructure.mapper;

import com.pmagent.backend.infrastructure.entity.AgentStateEntity;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface AgentStateMapper {

    @Select("""
        SELECT state_key, payload, updated_at
        FROM agent_states
        WHERE state_key = #{stateKey}
        LIMIT 1
        """)
    AgentStateEntity get(@Param("stateKey") String stateKey);

    @Insert("""
        INSERT INTO agent_states (state_key, payload, updated_at)
        VALUES (#{stateKey}, #{payload}, #{updatedAt})
        ON DUPLICATE KEY UPDATE
          payload = VALUES(payload),
          updated_at = VALUES(updated_at)
        """)
    int upsert(AgentStateEntity entity);
}
