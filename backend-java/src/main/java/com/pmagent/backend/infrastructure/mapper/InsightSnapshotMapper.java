package com.pmagent.backend.infrastructure.mapper;

import com.pmagent.backend.infrastructure.entity.InsightSnapshotEntity;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface InsightSnapshotMapper {

    @Insert("""
        INSERT INTO workspace_insight_snapshots
        (workspace_id, snapshot_at, heatmap_json, single_points_json, growth_suggestions_json, summary_json)
        VALUES
        (#{workspaceId}, #{snapshotAt}, CAST(#{heatmapJson} AS JSON), CAST(#{singlePointsJson} AS JSON), CAST(#{growthSuggestionsJson} AS JSON), CAST(#{summaryJson} AS JSON))
        """)
    int insert(InsightSnapshotEntity entity);

    @Select("""
        SELECT workspace_id, snapshot_at, CAST(heatmap_json AS CHAR) AS heatmap_json, CAST(single_points_json AS CHAR) AS single_points_json,
               CAST(growth_suggestions_json AS CHAR) AS growth_suggestions_json, CAST(summary_json AS CHAR) AS summary_json
        FROM workspace_insight_snapshots
        WHERE workspace_id = #{workspaceId}
        ORDER BY id DESC
        LIMIT #{limit}
        """)
    List<InsightSnapshotEntity> listByWorkspace(@Param("workspaceId") String workspaceId, @Param("limit") int limit);
}
