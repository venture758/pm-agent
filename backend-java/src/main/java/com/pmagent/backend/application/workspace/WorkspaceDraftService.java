package com.pmagent.backend.application.workspace;

import com.pmagent.backend.infrastructure.entity.WorkspaceEntity;
import com.pmagent.backend.infrastructure.mapper.WorkspaceMapper;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

@Service
public class WorkspaceDraftService {

    private final WorkspaceMapper workspaceMapper;

    public WorkspaceDraftService(WorkspaceMapper workspaceMapper) {
        this.workspaceMapper = workspaceMapper;
    }

    public Map<String, Object> updateDraft(String workspaceId, Map<String, Object> payload) {
        String now = Instant.now().toString();
        String title = String.valueOf(payload.getOrDefault("title", workspaceId));

        WorkspaceEntity entity = new WorkspaceEntity();
        entity.setWorkspaceId(workspaceId);
        entity.setTitle(title);
        entity.setCreatedAt(now);
        entity.setUpdatedAt(now);
        workspaceMapper.upsert(entity);

        Map<String, Object> draft = new HashMap<>();
        draft.put("workspaceId", workspaceId);
        draft.put("title", title);
        draft.put("updatedAt", now);
        draft.put("draftMode", payload.getOrDefault("draft_mode", "chat"));
        draft.put("messageText", payload.getOrDefault("message_text", ""));
        draft.put("requirementRows", payload.getOrDefault("requirement_rows", java.util.List.of()));
        return draft;
    }
}
