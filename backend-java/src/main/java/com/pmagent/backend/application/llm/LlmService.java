package com.pmagent.backend.application.llm;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pmagent.backend.application.config.LlmProviderProperties;
import com.pmagent.backend.domain.LlmUnavailableException;
import com.pmagent.backend.infrastructure.llm.OpenAiCompatibleLlmClient;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class LlmService {

    private final LlmProviderProperties llmProviderProperties;
    private final OpenAiCompatibleLlmClient client;
    private final ObjectMapper objectMapper;

    public LlmService(LlmProviderProperties llmProviderProperties, ObjectMapper objectMapper) {
        this.llmProviderProperties = llmProviderProperties;
        this.objectMapper = objectMapper;
        this.client = new OpenAiCompatibleLlmClient(objectMapper);
    }

    public Map<String, Object> parseRequirements(String message) {
        String prompt = """
            请解析用户消息，返回 JSON:
            {
              "reply": "给用户的简短回复",
              "requirements": [
                {"requirement_id":"1","title":"标题","priority":"高|中|低","raw_text":"原文"}
              ]
            }
            用户消息：
            """ + message;
        String raw = chatWithFallback(prompt);
        try {
            JsonNode node = objectMapper.readTree(normalizeJsonPayload(raw));
            String reply = node.path("reply").asText("已收到需求");
            List<Map<String, Object>> requirements = new ArrayList<>();
            for (JsonNode req : node.path("requirements")) {
                String requirementId = req.path("requirement_id").asText("");
                if (requirementId.isBlank()) {
                    requirementId = UUID.randomUUID().toString();
                }
                requirements.add(Map.of(
                    "requirement_id", requirementId,
                    "title", req.path("title").asText("未命名需求"),
                    "priority", req.path("priority").asText("中"),
                    "raw_text", req.path("raw_text").asText(message)
                ));
            }
            if (requirements.isEmpty()) {
                requirements.add(Map.of(
                    "requirement_id", UUID.randomUUID().toString(),
                    "title", "自动解析需求",
                    "priority", "中",
                    "raw_text", message
                ));
            }
            return Map.of(
                "reply", reply,
                "requirements", requirements
            );
        } catch (Exception ex) {
            throw new LlmUnavailableException("llm returned invalid json: " + ex.getMessage(), ex);
        }
    }

    public Map<String, Object> analyzePipelineStep(String stepKey, String context, String feedback) {
        String prompt = """
            你是项目经理分析助手。请按 JSON 输出:
            {
              "summary":"本步骤结论",
              "constraints":["约束1","约束2"],
              "items":[{"title":"条目","detail":"说明"}]
            }
            step=%s
            context=%s
            feedback=%s
            """.formatted(stepKey, context == null ? "" : context, feedback == null ? "" : feedback);
        String raw = chatWithFallback(prompt);
        try {
            JsonNode node = objectMapper.readTree(normalizeJsonPayload(raw));
            return objectMapper.convertValue(node, Map.class);
        } catch (Exception ex) {
            throw new LlmUnavailableException("llm returned invalid pipeline json: " + ex.getMessage(), ex);
        }
    }

    static String normalizeJsonPayload(String raw) {
        if (raw == null) {
            return "";
        }
        String text = raw.trim();
        if (text.startsWith("```")) {
            int firstLineBreak = text.indexOf('\n');
            int lastFence = text.lastIndexOf("```");
            if (firstLineBreak >= 0 && lastFence > firstLineBreak) {
                text = text.substring(firstLineBreak + 1, lastFence).trim();
            }
        }

        int objectStart = text.indexOf('{');
        int arrayStart = text.indexOf('[');
        int start = -1;
        if (objectStart >= 0 && arrayStart >= 0) {
            start = Math.min(objectStart, arrayStart);
        } else if (objectStart >= 0) {
            start = objectStart;
        } else if (arrayStart >= 0) {
            start = arrayStart;
        }

        if (start >= 0) {
            int end = Math.max(text.lastIndexOf('}'), text.lastIndexOf(']'));
            if (end >= start) {
                text = text.substring(start, end + 1).trim();
            }
        }
        return text;
    }

    private String chatWithFallback(String prompt) {
        List<String> errors = new ArrayList<>();
        try {
            return callTier(llmProviderProperties.getPrimary(), prompt);
        } catch (Exception ex) {
            errors.add("primary: " + ex.getMessage());
        }
        try {
            return callTier(llmProviderProperties.getFallback(), prompt);
        } catch (Exception ex) {
            errors.add("fallback: " + ex.getMessage());
        }
        throw new LlmUnavailableException("all llm tiers failed: " + String.join(" | ", errors));
    }

    private String callTier(LlmProviderProperties.Tier tier, String prompt) {
        int retry = Math.max(0, tier.getRetryTimes());
        LlmUnavailableException last = null;
        for (int i = 0; i <= retry; i++) {
            try {
                return client.chat(
                    tier.getBaseUrl(),
                    tier.getApiKey(),
                    tier.getModel(),
                    tier.getTimeoutSeconds(),
                    prompt
                );
            } catch (LlmUnavailableException ex) {
                last = ex;
            }
        }
        if (last != null) {
            throw last;
        }
        throw new LlmUnavailableException("llm tier failed");
    }
}
