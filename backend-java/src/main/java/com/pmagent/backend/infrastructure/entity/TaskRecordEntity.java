package com.pmagent.backend.infrastructure.entity;

import java.math.BigDecimal;

public class TaskRecordEntity {

    private String workspaceId;
    private String taskCode;
    private String relatedStory;
    private String name;
    private String taskType;
    private String owner;
    private String status;
    private String estimatedStart;
    private String estimatedEnd;
    private BigDecimal plannedPersonDays;
    private BigDecimal actualPersonDays;
    private BigDecimal defectCount;
    private String projectName;
    private String importedAt;
    private String updatedAt;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public void setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
    }

    public String getTaskCode() {
        return taskCode;
    }

    public void setTaskCode(String taskCode) {
        this.taskCode = taskCode;
    }

    public String getRelatedStory() {
        return relatedStory;
    }

    public void setRelatedStory(String relatedStory) {
        this.relatedStory = relatedStory;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getTaskType() {
        return taskType;
    }

    public void setTaskType(String taskType) {
        this.taskType = taskType;
    }

    public String getOwner() {
        return owner;
    }

    public void setOwner(String owner) {
        this.owner = owner;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getEstimatedStart() {
        return estimatedStart;
    }

    public void setEstimatedStart(String estimatedStart) {
        this.estimatedStart = estimatedStart;
    }

    public String getEstimatedEnd() {
        return estimatedEnd;
    }

    public void setEstimatedEnd(String estimatedEnd) {
        this.estimatedEnd = estimatedEnd;
    }

    public BigDecimal getPlannedPersonDays() {
        return plannedPersonDays;
    }

    public void setPlannedPersonDays(BigDecimal plannedPersonDays) {
        this.plannedPersonDays = plannedPersonDays;
    }

    public BigDecimal getActualPersonDays() {
        return actualPersonDays;
    }

    public void setActualPersonDays(BigDecimal actualPersonDays) {
        this.actualPersonDays = actualPersonDays;
    }

    public BigDecimal getDefectCount() {
        return defectCount;
    }

    public void setDefectCount(BigDecimal defectCount) {
        this.defectCount = defectCount;
    }

    public String getProjectName() {
        return projectName;
    }

    public void setProjectName(String projectName) {
        this.projectName = projectName;
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
