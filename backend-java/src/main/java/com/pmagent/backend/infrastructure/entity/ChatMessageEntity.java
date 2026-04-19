package com.pmagent.backend.infrastructure.entity;

public class ChatMessageEntity {

    private String workspaceId;
    private String sessionId;
    private Integer seq;
    private String role;
    private String content;
    private String timestamp;
    private String parsedRequirementsJson;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public void setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public Integer getSeq() {
        return seq;
    }

    public void setSeq(Integer seq) {
        this.seq = seq;
    }

    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public String getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(String timestamp) {
        this.timestamp = timestamp;
    }

    public String getParsedRequirementsJson() {
        return parsedRequirementsJson;
    }

    public void setParsedRequirementsJson(String parsedRequirementsJson) {
        this.parsedRequirementsJson = parsedRequirementsJson;
    }
}
