package com.pmagent.backend.infrastructure.entity;

public class InsightSnapshotEntity {

    private String workspaceId;
    private String snapshotAt;
    private String heatmapJson;
    private String singlePointsJson;
    private String growthSuggestionsJson;
    private String summaryJson;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public void setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
    }

    public String getSnapshotAt() {
        return snapshotAt;
    }

    public void setSnapshotAt(String snapshotAt) {
        this.snapshotAt = snapshotAt;
    }

    public String getHeatmapJson() {
        return heatmapJson;
    }

    public void setHeatmapJson(String heatmapJson) {
        this.heatmapJson = heatmapJson;
    }

    public String getSinglePointsJson() {
        return singlePointsJson;
    }

    public void setSinglePointsJson(String singlePointsJson) {
        this.singlePointsJson = singlePointsJson;
    }

    public String getGrowthSuggestionsJson() {
        return growthSuggestionsJson;
    }

    public void setGrowthSuggestionsJson(String growthSuggestionsJson) {
        this.growthSuggestionsJson = growthSuggestionsJson;
    }

    public String getSummaryJson() {
        return summaryJson;
    }

    public void setSummaryJson(String summaryJson) {
        this.summaryJson = summaryJson;
    }
}
