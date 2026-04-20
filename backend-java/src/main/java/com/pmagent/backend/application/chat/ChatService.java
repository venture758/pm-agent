package com.pmagent.backend.application.chat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pmagent.backend.application.llm.LlmService;
import com.pmagent.backend.infrastructure.entity.ChatMessageEntity;
import com.pmagent.backend.infrastructure.entity.ChatSessionEntity;
import com.pmagent.backend.infrastructure.mapper.ChatMessageMapper;
import com.pmagent.backend.infrastructure.mapper.ChatSessionMapper;
import com.pmagent.backend.infrastructure.mapper.ModuleEntryMapper;
import com.pmagent.backend.infrastructure.mapper.RequirementWriteMapper;
import com.pmagent.backend.infrastructure.mapper.SessionRequirementMapper;
import com.pmagent.backend.infrastructure.mapper.StoryRecordMapper;
import com.pmagent.backend.infrastructure.mapper.TaskRecordMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class ChatService {

    private final ChatSessionMapper chatSessionMapper;
    private final ChatMessageMapper chatMessageMapper;
    private final RequirementWriteMapper requirementWriteMapper;
    private final SessionRequirementMapper sessionRequirementMapper;
    private final ModuleEntryMapper moduleEntryMapper;
    private final TaskRecordMapper taskRecordMapper;
    private final StoryRecordMapper storyRecordMapper;
    private final RequirementParseContextBuilder requirementParseContextBuilder;
    private final LlmService llmService;
    private final ObjectMapper objectMapper;

    public ChatService(ChatSessionMapper chatSessionMapper,
                       ChatMessageMapper chatMessageMapper,
                       RequirementWriteMapper requirementWriteMapper,
                       SessionRequirementMapper sessionRequirementMapper,
                       ModuleEntryMapper moduleEntryMapper,
                       TaskRecordMapper taskRecordMapper,
                       StoryRecordMapper storyRecordMapper,
                       RequirementParseContextBuilder requirementParseContextBuilder,
                       LlmService llmService,
                       ObjectMapper objectMapper) {
        this.chatSessionMapper = chatSessionMapper;
        this.chatMessageMapper = chatMessageMapper;
        this.requirementWriteMapper = requirementWriteMapper;
        this.sessionRequirementMapper = sessionRequirementMapper;
        this.moduleEntryMapper = moduleEntryMapper;
        this.taskRecordMapper = taskRecordMapper;
        this.storyRecordMapper = storyRecordMapper;
        this.requirementParseContextBuilder = requirementParseContextBuilder;
        this.llmService = llmService;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public Map<String, Object> send(String workspaceId, Map<String, Object> payload) {
        String message = normalize(String.valueOf(payload.getOrDefault("message", "")));
        if (message.isEmpty()) {
            throw new IllegalArgumentException("message is required");
        }
        String sessionId = normalize(String.valueOf(payload.getOrDefault("session_id", "")));
        if (sessionId.isEmpty()) {
            ChatSessionEntity active = chatSessionMapper.findActive(workspaceId);
            if (active == null) {
                sessionId = String.valueOf(createSession(workspaceId, Map.of()).get("sessionId"));
            } else {
                sessionId = active.getSessionId();
            }
        }

        String now = Instant.now().toString();
        appendMessage(workspaceId, sessionId, "user", message, "");
        Map<String, Object> parseContext = requirementParseContextBuilder.build(
            moduleEntryMapper.listAllByWorkspaceId(workspaceId),
            taskRecordMapper.listAllByWorkspace(workspaceId),
            storyRecordMapper.listAllByWorkspace(workspaceId)
        );
        Map<String, Object> parsed = llmService.parseRequirements(message, parseContext);
        String reply = String.valueOf(parsed.getOrDefault("reply", "已收到需求"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> requirements = (List<Map<String, Object>>) parsed.getOrDefault("requirements", List.of());
        String parsedJson = writeJson(requirements);
        appendMessage(workspaceId, sessionId, "assistant", reply, parsedJson);

        for (Map<String, Object> requirement : requirements) {
            String requirementId = String.valueOf(requirement.getOrDefault("requirement_id", UUID.randomUUID().toString()));
            String title = String.valueOf(requirement.getOrDefault("title", "未命名需求"));
            String priority = String.valueOf(requirement.getOrDefault("priority", "中"));
            String rawText = String.valueOf(requirement.getOrDefault("raw_text", message));
            requirementWriteMapper.upsert(workspaceId, requirementId, title, priority, rawText, writeJson(requirement), now);
            sessionRequirementMapper.insert(sessionId, requirementId);
        }
        chatSessionMapper.touch(workspaceId, sessionId, now, shorten(reply));

        Map<String, Object> response = new HashMap<>();
        response.put("workspaceId", workspaceId);
        response.put("sessionId", sessionId);
        response.put("messages", toMessageList(chatMessageMapper.list(workspaceId, sessionId)));
        response.put("requirementIds", sessionRequirementMapper.listRequirementIds(sessionId));
        response.put("reply", reply);
        return response;
    }

    @Transactional
    public Map<String, Object> createSession(String workspaceId, Map<String, Object> payload) {
        chatSessionMapper.archiveActive(workspaceId);
        String now = Instant.now().toString();
        ChatSessionEntity entity = new ChatSessionEntity();
        entity.setSessionId(UUID.randomUUID().toString());
        entity.setWorkspaceId(workspaceId);
        entity.setCreatedAt(now);
        entity.setLastActiveAt(now);
        entity.setStatus("active");
        entity.setLastMessagePreview("");
        chatSessionMapper.insert(entity);
        return Map.of(
            "sessionId", entity.getSessionId(),
            "createdAt", entity.getCreatedAt(),
            "status", entity.getStatus()
        );
    }

    public Map<String, Object> listSessions(String workspaceId) {
        List<Map<String, Object>> sessions = chatSessionMapper.listByWorkspace(workspaceId).stream().map(it -> {
            Map<String, Object> item = new HashMap<>();
            item.put("sessionId", it.getSessionId());
            item.put("createdAt", it.getCreatedAt());
            item.put("lastActiveAt", it.getLastActiveAt());
            item.put("status", it.getStatus());
            item.put("lastMessagePreview", it.getLastMessagePreview());
            item.put("requirementIds", sessionRequirementMapper.listRequirementIds(it.getSessionId()));
            return item;
        }).toList();
        ChatSessionEntity active = chatSessionMapper.findActive(workspaceId);
        return Map.of(
            "workspaceId", workspaceId,
            "activeSessionId", active == null ? "" : active.getSessionId(),
            "sessions", sessions
        );
    }

    public Map<String, Object> getSession(String workspaceId, String sessionId) {
        ChatSessionEntity session = chatSessionMapper.get(workspaceId, sessionId);
        if (session == null) {
            throw new IllegalArgumentException("session_not_found: " + sessionId);
        }
        return Map.of(
            "sessionId", sessionId,
            "createdAt", session.getCreatedAt(),
            "lastActiveAt", session.getLastActiveAt(),
            "status", session.getStatus(),
            "messages", toMessageList(chatMessageMapper.list(workspaceId, sessionId)),
            "requirementIds", sessionRequirementMapper.listRequirementIds(sessionId)
        );
    }

    @Transactional
    public Map<String, Object> deleteSession(String workspaceId, String sessionId) {
        ChatSessionEntity session = chatSessionMapper.get(workspaceId, sessionId);
        if (session == null) {
            throw new IllegalArgumentException("session_not_found: " + sessionId);
        }
        chatMessageMapper.deleteBySession(workspaceId, sessionId);
        sessionRequirementMapper.deleteBySession(sessionId);
        chatSessionMapper.delete(workspaceId, sessionId);

        ChatSessionEntity active = chatSessionMapper.findActive(workspaceId);
        return Map.of(
            "workspaceId", workspaceId,
            "activeSessionId", active == null ? "" : active.getSessionId()
        );
    }

    private void appendMessage(String workspaceId, String sessionId, String role, String content, String parsedRequirementsJson) {
        ChatMessageEntity entity = new ChatMessageEntity();
        entity.setWorkspaceId(workspaceId);
        entity.setSessionId(sessionId);
        entity.setSeq(chatMessageMapper.nextSeq(sessionId));
        entity.setRole(role);
        entity.setContent(content);
        entity.setTimestamp(Instant.now().toString());
        entity.setParsedRequirementsJson(parsedRequirementsJson == null ? "" : parsedRequirementsJson);
        chatMessageMapper.insert(entity);
    }

    private List<Map<String, Object>> toMessageList(List<ChatMessageEntity> messages) {
        return messages.stream().map(message -> {
            Map<String, Object> item = new HashMap<>();
            item.put("seq", message.getSeq());
            item.put("role", message.getRole());
            item.put("content", message.getContent());
            item.put("timestamp", message.getTimestamp());
            item.put("parsedRequirements", readAnyJson(message.getParsedRequirementsJson()));
            return item;
        }).toList();
    }

    private Object readAnyJson(String json) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, Object.class);
        } catch (Exception ex) {
            return json;
        }
    }

    private String writeJson(Object payload) {
        try {
            return objectMapper.writeValueAsString(payload);
        } catch (Exception ex) {
            throw new IllegalArgumentException("failed to serialize chat payload", ex);
        }
    }

    private String normalize(String text) {
        return text == null ? "" : text.trim();
    }

    private String shorten(String text) {
        if (text == null) {
            return "";
        }
        String normalized = text.trim();
        if (normalized.length() <= 200) {
            return normalized;
        }
        return normalized.substring(0, 200);
    }
}
