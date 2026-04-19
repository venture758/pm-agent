package com.pmagent.backend.infrastructure.mapper;

import com.pmagent.backend.infrastructure.entity.TaskRecordEntity;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface TaskRecordMapper {

    @Insert("""
        INSERT INTO workspace_task_records
        (workspace_id, task_code, related_story, name, task_type, owner, status, estimated_start, estimated_end,
         planned_person_days, actual_person_days, defect_count, project_name, imported_at, updated_at)
        VALUES
        (#{workspaceId}, #{taskCode}, #{relatedStory}, #{name}, #{taskType}, #{owner}, #{status}, #{estimatedStart}, #{estimatedEnd},
         #{plannedPersonDays}, #{actualPersonDays}, #{defectCount}, #{projectName}, #{importedAt}, #{updatedAt})
        ON DUPLICATE KEY UPDATE
          related_story = VALUES(related_story),
          name = VALUES(name),
          task_type = VALUES(task_type),
          owner = VALUES(owner),
          status = VALUES(status),
          estimated_start = VALUES(estimated_start),
          estimated_end = VALUES(estimated_end),
          planned_person_days = VALUES(planned_person_days),
          actual_person_days = VALUES(actual_person_days),
          defect_count = VALUES(defect_count),
          project_name = VALUES(project_name),
          updated_at = VALUES(updated_at)
        """)
    int upsert(TaskRecordEntity entity);

    @Select("""
        <script>
        SELECT COUNT(1)
        FROM workspace_task_records
        WHERE workspace_id = #{workspaceId}
        <if test="owner != null and owner != ''">
          AND owner = #{owner}
        </if>
        <if test="status != null and status != ''">
          AND status = #{status}
        </if>
        <if test="projectName != null and projectName != ''">
          AND project_name = #{projectName}
        </if>
        </script>
        """)
    long countByWorkspace(@Param("workspaceId") String workspaceId,
                          @Param("owner") String owner,
                          @Param("status") String status,
                          @Param("projectName") String projectName);

    @Select("""
        <script>
        SELECT workspace_id, task_code, related_story, name, task_type, owner, status, estimated_start, estimated_end,
               planned_person_days, actual_person_days, defect_count, project_name, imported_at, updated_at
        FROM workspace_task_records
        WHERE workspace_id = #{workspaceId}
        <if test="owner != null and owner != ''">
          AND owner = #{owner}
        </if>
        <if test="status != null and status != ''">
          AND status = #{status}
        </if>
        <if test="projectName != null and projectName != ''">
          AND project_name = #{projectName}
        </if>
        ORDER BY id DESC
        LIMIT #{pageSize} OFFSET #{offset}
        </script>
        """)
    List<TaskRecordEntity> listByWorkspace(@Param("workspaceId") String workspaceId,
                                           @Param("owner") String owner,
                                           @Param("status") String status,
                                           @Param("projectName") String projectName,
                                           @Param("offset") int offset,
                                           @Param("pageSize") int pageSize);

    @Select("""
        SELECT workspace_id, task_code, related_story, name, task_type, owner, status, estimated_start, estimated_end,
               planned_person_days, actual_person_days, defect_count, project_name, imported_at, updated_at
        FROM workspace_task_records
        WHERE workspace_id = #{workspaceId}
        ORDER BY id DESC
        """)
    List<TaskRecordEntity> listAllByWorkspace(@Param("workspaceId") String workspaceId);
}
