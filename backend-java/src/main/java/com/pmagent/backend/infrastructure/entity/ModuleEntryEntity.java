package com.pmagent.backend.infrastructure.entity;

public class ModuleEntryEntity {

    private String workspaceId;
    private String moduleKey;
    private String bigModule;
    private String functionModule;
    private String primaryOwner;
    private String backupOwnersJson;
    private String familiarMembersJson;
    private String awareMembersJson;
    private String unfamiliarMembersJson;
    private String updatedAt;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public void setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
    }

    public String getModuleKey() {
        return moduleKey;
    }

    public void setModuleKey(String moduleKey) {
        this.moduleKey = moduleKey;
    }

    public String getBigModule() {
        return bigModule;
    }

    public void setBigModule(String bigModule) {
        this.bigModule = bigModule;
    }

    public String getFunctionModule() {
        return functionModule;
    }

    public void setFunctionModule(String functionModule) {
        this.functionModule = functionModule;
    }

    public String getPrimaryOwner() {
        return primaryOwner;
    }

    public void setPrimaryOwner(String primaryOwner) {
        this.primaryOwner = primaryOwner;
    }

    public String getBackupOwnersJson() {
        return backupOwnersJson;
    }

    public void setBackupOwnersJson(String backupOwnersJson) {
        this.backupOwnersJson = backupOwnersJson;
    }

    public String getFamiliarMembersJson() {
        return familiarMembersJson;
    }

    public void setFamiliarMembersJson(String familiarMembersJson) {
        this.familiarMembersJson = familiarMembersJson;
    }

    public String getAwareMembersJson() {
        return awareMembersJson;
    }

    public void setAwareMembersJson(String awareMembersJson) {
        this.awareMembersJson = awareMembersJson;
    }

    public String getUnfamiliarMembersJson() {
        return unfamiliarMembersJson;
    }

    public void setUnfamiliarMembersJson(String unfamiliarMembersJson) {
        this.unfamiliarMembersJson = unfamiliarMembersJson;
    }

    public String getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(String updatedAt) {
        this.updatedAt = updatedAt;
    }
}
