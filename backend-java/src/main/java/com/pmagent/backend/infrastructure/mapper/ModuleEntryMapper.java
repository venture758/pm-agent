package com.pmagent.backend.infrastructure.mapper;

import com.pmagent.backend.infrastructure.entity.ModuleEntryEntity;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

@Mapper
public interface ModuleEntryMapper {

    @Select("""
        <script>
        SELECT COUNT(1)
        FROM workspace_module_entries
        WHERE workspace_id = #{workspaceId}
        <if test="bigModule != null and bigModule != ''">
          AND big_module LIKE CONCAT('%', #{bigModule}, '%')
        </if>
        <if test="functionModule != null and functionModule != ''">
          AND function_module LIKE CONCAT('%', #{functionModule}, '%')
        </if>
        <if test="primaryOwner != null and primaryOwner != ''">
          AND primary_owner LIKE CONCAT('%', #{primaryOwner}, '%')
        </if>
        </script>
        """)
    long countByWorkspaceWithFilters(@Param("workspaceId") String workspaceId,
                                     @Param("bigModule") String bigModule,
                                     @Param("functionModule") String functionModule,
                                     @Param("primaryOwner") String primaryOwner);

    @Select("""
        <script>
        SELECT workspace_id, module_key, big_module, function_module, primary_owner,
               backup_owners_json, familiar_members_json, aware_members_json, unfamiliar_members_json, updated_at
        FROM workspace_module_entries
        WHERE workspace_id = #{workspaceId}
        <if test="bigModule != null and bigModule != ''">
          AND big_module LIKE CONCAT('%', #{bigModule}, '%')
        </if>
        <if test="functionModule != null and functionModule != ''">
          AND function_module LIKE CONCAT('%', #{functionModule}, '%')
        </if>
        <if test="primaryOwner != null and primaryOwner != ''">
          AND primary_owner LIKE CONCAT('%', #{primaryOwner}, '%')
        </if>
        ORDER BY big_module ASC, function_module ASC
        LIMIT #{pageSize} OFFSET #{offset}
        </script>
        """)
    List<ModuleEntryEntity> listByWorkspaceWithFilters(@Param("workspaceId") String workspaceId,
                                                       @Param("bigModule") String bigModule,
                                                       @Param("functionModule") String functionModule,
                                                       @Param("primaryOwner") String primaryOwner,
                                                       @Param("offset") int offset,
                                                       @Param("pageSize") int pageSize);

    @Select("""
        SELECT workspace_id, module_key, big_module, function_module, primary_owner,
               backup_owners_json, familiar_members_json, aware_members_json, unfamiliar_members_json, updated_at
        FROM workspace_module_entries
        WHERE workspace_id = #{workspaceId}
        ORDER BY big_module ASC, function_module ASC
        """)
    List<ModuleEntryEntity> listAllByWorkspaceId(@Param("workspaceId") String workspaceId);

    @Insert("""
        INSERT INTO workspace_module_entries
        (workspace_id, module_key, big_module, function_module, primary_owner, backup_owners_json, familiar_members_json, aware_members_json,
         unfamiliar_members_json, source_sheet, source_year, imported_at, recent_assignees_json, suggested_familiarity_json, assignment_history_json, updated_at)
        VALUES
        (#{workspaceId}, #{moduleKey}, #{bigModule}, #{functionModule}, #{primaryOwner},
         CAST(#{backupOwnersJson} AS JSON), CAST(#{familiarMembersJson} AS JSON), CAST(#{awareMembersJson} AS JSON),
         CAST(#{unfamiliarMembersJson} AS JSON), '', 0, #{updatedAt}, JSON_ARRAY(), JSON_OBJECT(), '[]', #{updatedAt})
        """)
    int insert(ModuleEntryEntity entity);

    @Insert("""
        INSERT INTO workspace_module_entries
        (workspace_id, module_key, big_module, function_module, primary_owner, backup_owners_json, familiar_members_json, aware_members_json,
         unfamiliar_members_json, source_sheet, source_year, imported_at, recent_assignees_json, suggested_familiarity_json, assignment_history_json, updated_at)
        VALUES
        (#{workspaceId}, #{moduleKey}, #{bigModule}, #{functionModule}, #{primaryOwner},
         CAST(#{backupOwnersJson} AS JSON), CAST(#{familiarMembersJson} AS JSON), CAST(#{awareMembersJson} AS JSON),
         CAST(#{unfamiliarMembersJson} AS JSON), '', 0, #{updatedAt}, JSON_ARRAY(), JSON_OBJECT(), '[]', #{updatedAt})
        ON DUPLICATE KEY UPDATE
          big_module = VALUES(big_module),
          function_module = VALUES(function_module),
          primary_owner = VALUES(primary_owner),
          backup_owners_json = VALUES(backup_owners_json),
          familiar_members_json = VALUES(familiar_members_json),
          aware_members_json = VALUES(aware_members_json),
          unfamiliar_members_json = VALUES(unfamiliar_members_json),
          updated_at = VALUES(updated_at)
        """)
    int upsert(ModuleEntryEntity entity);

    @Update("""
        UPDATE workspace_module_entries
        SET big_module = #{bigModule},
            function_module = #{functionModule},
            primary_owner = #{primaryOwner},
            backup_owners_json = CAST(#{backupOwnersJson} AS JSON),
            familiar_members_json = CAST(#{familiarMembersJson} AS JSON),
            aware_members_json = CAST(#{awareMembersJson} AS JSON),
            unfamiliar_members_json = CAST(#{unfamiliarMembersJson} AS JSON),
            updated_at = #{updatedAt}
        WHERE workspace_id = #{workspaceId}
          AND module_key = #{moduleKey}
        """)
    int update(ModuleEntryEntity entity);

    @Delete("""
        DELETE FROM workspace_module_entries
        WHERE workspace_id = #{workspaceId}
          AND module_key = #{moduleKey}
        """)
    int delete(@Param("workspaceId") String workspaceId, @Param("moduleKey") String moduleKey);
}
