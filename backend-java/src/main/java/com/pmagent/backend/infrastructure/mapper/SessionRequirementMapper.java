package com.pmagent.backend.infrastructure.mapper;

import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface SessionRequirementMapper {

    @Insert("""
        INSERT INTO session_requirements (session_id, requirement_id)
        VALUES (#{sessionId}, #{requirementId})
        ON DUPLICATE KEY UPDATE requirement_id = VALUES(requirement_id)
        """)
    int insert(@Param("sessionId") String sessionId, @Param("requirementId") String requirementId);

    @Select("""
        SELECT requirement_id
        FROM session_requirements
        WHERE session_id = #{sessionId}
        ORDER BY id ASC
        """)
    List<String> listRequirementIds(@Param("sessionId") String sessionId);

    @Delete("""
        DELETE FROM session_requirements
        WHERE session_id = #{sessionId}
        """)
    int deleteBySession(@Param("sessionId") String sessionId);
}
