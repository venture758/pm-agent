package com.pmagent.backend.infrastructure.entity;

public class StoryRecordEntity {

    private String workspaceId;
    private String userStoryCode;
    private String userStoryName;
    private String status;
    private String ownerNames;
    private String testerNames;
    private String priority;
    private String detailUrl;
    private String projectName;
    private String developerNames;
    private String importedAt;
    private String updatedAt;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public void setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
    }

    public String getUserStoryCode() {
        return userStoryCode;
    }

    public void setUserStoryCode(String userStoryCode) {
        this.userStoryCode = userStoryCode;
    }

    public String getUserStoryName() {
        return userStoryName;
    }

    public void setUserStoryName(String userStoryName) {
        this.userStoryName = userStoryName;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getOwnerNames() {
        return ownerNames;
    }

    public void setOwnerNames(String ownerNames) {
        this.ownerNames = ownerNames;
    }

    public String getTesterNames() {
        return testerNames;
    }

    public void setTesterNames(String testerNames) {
        this.testerNames = testerNames;
    }

    public String getPriority() {
        return priority;
    }

    public void setPriority(String priority) {
        this.priority = priority;
    }

    public String getDetailUrl() {
        return detailUrl;
    }

    public void setDetailUrl(String detailUrl) {
        this.detailUrl = detailUrl;
    }

    public String getProjectName() {
        return projectName;
    }

    public void setProjectName(String projectName) {
        this.projectName = projectName;
    }

    public String getDeveloperNames() {
        return developerNames;
    }

    public void setDeveloperNames(String developerNames) {
        this.developerNames = developerNames;
    }

    public String getImportedAt() {
        return importedAt;
    }

    public void setImportedAt(String importedAt) {
        this.importedAt = importedAt;
    }

    public String getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(String updatedAt) {
        this.updatedAt = updatedAt;
    }
}
