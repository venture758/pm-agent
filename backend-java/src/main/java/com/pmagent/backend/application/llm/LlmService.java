package com.pmagent.backend.application.llm;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pmagent.backend.application.config.LlmProviderProperties;
import com.pmagent.backend.domain.LlmUnavailableException;
import com.pmagent.backend.infrastructure.llm.OpenAiCompatibleLlmClient;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
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
        return parseRequirements(message, Map.of());
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> parseRequirements(String message, Map<String, Object> parseContext) {
        String contextJson = writeJson(parseContext == null ? Map.of() : parseContext);
        String prompt = """
            你是需求解析助手。请仅返回 JSON，禁止 markdown。
            你必须基于给定模块候选进行模块归属，不可发明新模块。
            严禁使用 module_path 字段作为依据。
            返回 JSON:
            {
              "reply": "给用户的简短回复（1-2句）",
              "requirements": [
                {
                  "requirement_id":"1",
                  "title":"标题",
                  "priority":"高|中|低",
                  "raw_text":"原文",
                  "big_module":"大模块",
                  "function_module":"功能模块",
                  "abstract_summary":"抽象提炼后的一句话",
                  "match_evidence":["命中关键词xx","参考任务名xx"],
                  "match_status":"matched|needs_confirmation",
                  "candidate_modules":[
                    {"big_module":"候选大模块","function_module":"候选功能模块","reason":"候选理由"}
                  ]
                }
              ]
            }
            用户消息：
            %s

            解析上下文(JSON)：
            %s
            """.formatted(message, contextJson);
        String raw = chatWithFallback(prompt);
        try {
            JsonNode node = objectMapper.readTree(normalizeJsonPayload(raw));
            String reply = node.path("reply").asText("已收到需求");
            List<Map<String, Object>> requirements = new ArrayList<>();
            List<Map<String, Object>> moduleCandidates = extractModuleCandidates(parseContext);
            for (JsonNode req : node.path("requirements")) {
                Map<String, Object> normalized = normalizeRequirementItem(
                    objectMapper.convertValue(req, Map.class),
                    message,
                    moduleCandidates
                );
                requirements.add(normalized);
            }
            if (requirements.isEmpty()) {
                requirements.add(defaultRequirement(message, moduleCandidates));
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

    static Map<String, Object> normalizeRequirementItem(Map<String, Object> rawItem,
                                                        String originalMessage,
                                                        List<Map<String, Object>> moduleCandidates) {
        Map<String, Object> item = rawItem == null ? Map.of() : rawItem;
        List<Map<String, Object>> normalizedCandidates = normalizeCandidates(
            coerceCandidateModules(item.get("candidate_modules")),
            moduleCandidates
        );
        Set<String> knownModuleKeys = knownModuleKeys(moduleCandidates);

        String requirementId = nonBlank(item.get("requirement_id"), UUID.randomUUID().toString());
        String title = nonBlank(item.get("title"), "未命名需求");
        String priority = normalizePriority(String.valueOf(item.getOrDefault("priority", "中")));
        String rawText = nonBlank(item.get("raw_text"), originalMessage == null ? "" : originalMessage);
        String bigModule = trim(String.valueOf(item.getOrDefault("big_module", "")));
        String functionModule = trim(String.valueOf(item.getOrDefault("function_module", "")));
        String abstractSummary = nonBlank(item.get("abstract_summary"), title);
        List<String> matchEvidence = coerceStringList(item.get("match_evidence"));

        String moduleKey = "";
        boolean hasModule = !bigModule.isEmpty() && !functionModule.isEmpty();
        if (hasModule) {
            moduleKey = bigModule + "::" + functionModule;
        }
        boolean moduleValid = hasModule && knownModuleKeys.contains(moduleKey);
        String matchStatus = trim(String.valueOf(item.getOrDefault("match_status", ""))).toLowerCase(Locale.ROOT);

        if (!moduleValid) {
            bigModule = "";
            functionModule = "";
            moduleKey = "";
            matchStatus = "needs_confirmation";
            if (matchEvidence.isEmpty()) {
                matchEvidence = List.of("模块归属待人工确认");
            }
            if (normalizedCandidates.isEmpty()) {
                normalizedCandidates = fallbackCandidates(moduleCandidates, 3);
            }
        } else if (!"matched".equals(matchStatus)) {
            matchStatus = "matched";
        }

        Map<String, Object> normalized = new LinkedHashMap<>();
        normalized.put("requirement_id", requirementId);
        normalized.put("title", title);
        normalized.put("priority", priority);
        normalized.put("raw_text", rawText);
        normalized.put("big_module", bigModule);
        normalized.put("function_module", functionModule);
        normalized.put("abstract_summary", abstractSummary);
        normalized.put("match_evidence", matchEvidence);
        normalized.put("match_status", matchStatus);
        normalized.put("candidate_modules", normalizedCandidates);
        normalized.put("matched_module_keys", moduleKey.isEmpty() ? List.of() : List.of(moduleKey));
        return normalized;
    }

    private static Map<String, Object> defaultRequirement(String message, List<Map<String, Object>> moduleCandidates) {
        Map<String, Object> fallback = new LinkedHashMap<>();
        fallback.put("requirement_id", UUID.randomUUID().toString());
        fallback.put("title", "自动解析需求");
        fallback.put("priority", "中");
        fallback.put("raw_text", message == null ? "" : message);
        fallback.put("big_module", "");
        fallback.put("function_module", "");
        fallback.put("abstract_summary", "请人工补充需求抽象与模块归属");
        fallback.put("match_evidence", List.of("LLM 未返回可用需求条目"));
        fallback.put("match_status", "needs_confirmation");
        fallback.put("candidate_modules", fallbackCandidates(moduleCandidates, 3));
        fallback.put("matched_module_keys", List.of());
        return fallback;
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> extractModuleCandidates(Map<String, Object> parseContext) {
        if (parseContext == null) {
            return List.of();
        }
        Object raw = parseContext.get("module_candidates");
        if (!(raw instanceof List<?> rawList)) {
            return List.of();
        }
        List<Map<String, Object>> candidates = new ArrayList<>();
        for (Object item : rawList) {
            if (!(item instanceof Map<?, ?> source)) {
                continue;
            }
            String bigModule = trim(String.valueOf(valueFromMap(source, "big_module")));
            String functionModule = trim(String.valueOf(valueFromMap(source, "function_module")));
            if (bigModule.isEmpty() || functionModule.isEmpty()) {
                continue;
            }
            Map<String, Object> candidate = new LinkedHashMap<>();
            candidate.put("big_module", bigModule);
            candidate.put("function_module", functionModule);
            candidate.put("module_key", bigModule + "::" + functionModule);
            candidates.add(candidate);
        }
        return candidates;
    }

    private static List<Map<String, Object>> coerceCandidateModules(Object raw) {
        if (!(raw instanceof List<?> list)) {
            return List.of();
        }
        List<Map<String, Object>> candidates = new ArrayList<>();
        for (Object item : list) {
            if (!(item instanceof Map<?, ?> source)) {
                continue;
            }
            String bigModule = trim(String.valueOf(valueFromMap(source, "big_module")));
            String functionModule = trim(String.valueOf(valueFromMap(source, "function_module")));
            String reason = trim(String.valueOf(valueFromMap(source, "reason")));
            if (bigModule.isEmpty() || functionModule.isEmpty()) {
                continue;
            }
            Map<String, Object> candidate = new LinkedHashMap<>();
            candidate.put("big_module", bigModule);
            candidate.put("function_module", functionModule);
            if (!reason.isEmpty()) {
                candidate.put("reason", reason);
            }
            candidates.add(candidate);
        }
        return candidates;
    }

    private static List<Map<String, Object>> normalizeCandidates(List<Map<String, Object>> preferred,
                                                                 List<Map<String, Object>> fallbackPool) {
        if (preferred == null || preferred.isEmpty()) {
            return List.of();
        }
        Set<String> known = knownModuleKeys(fallbackPool);
        List<Map<String, Object>> normalized = new ArrayList<>();
        Set<String> dedup = new LinkedHashSet<>();
        for (Map<String, Object> item : preferred) {
            String bigModule = trim(String.valueOf(item.getOrDefault("big_module", "")));
            String functionModule = trim(String.valueOf(item.getOrDefault("function_module", "")));
            if (bigModule.isEmpty() || functionModule.isEmpty()) {
                continue;
            }
            String moduleKey = bigModule + "::" + functionModule;
            if (!known.isEmpty() && !known.contains(moduleKey)) {
                continue;
            }
            if (!dedup.add(moduleKey)) {
                continue;
            }
            Map<String, Object> normalizedItem = new LinkedHashMap<>();
            normalizedItem.put("big_module", bigModule);
            normalizedItem.put("function_module", functionModule);
            if (item.containsKey("reason")) {
                String reason = trim(String.valueOf(item.get("reason")));
                if (!reason.isEmpty()) {
                    normalizedItem.put("reason", reason);
                }
            }
            normalized.add(normalizedItem);
            if (normalized.size() >= 3) {
                break;
            }
        }
        return normalized;
    }

    private static List<Map<String, Object>> fallbackCandidates(List<Map<String, Object>> moduleCandidates, int limit) {
        if (moduleCandidates == null || moduleCandidates.isEmpty() || limit <= 0) {
            return List.of();
        }
        List<Map<String, Object>> fallback = new ArrayList<>();
        int remaining = limit;
        for (Map<String, Object> candidate : moduleCandidates) {
            String bigModule = trim(String.valueOf(candidate.getOrDefault("big_module", "")));
            String functionModule = trim(String.valueOf(candidate.getOrDefault("function_module", "")));
            if (bigModule.isEmpty() || functionModule.isEmpty()) {
                continue;
            }
            Map<String, Object> value = new LinkedHashMap<>();
            value.put("big_module", bigModule);
            value.put("function_module", functionModule);
            fallback.add(value);
            remaining--;
            if (remaining <= 0) {
                break;
            }
        }
        return fallback;
    }

    private static Set<String> knownModuleKeys(List<Map<String, Object>> moduleCandidates) {
        if (moduleCandidates == null || moduleCandidates.isEmpty()) {
            return Set.of();
        }
        Set<String> known = new LinkedHashSet<>();
        for (Map<String, Object> candidate : moduleCandidates) {
            String bigModule = trim(String.valueOf(candidate.getOrDefault("big_module", "")));
            String functionModule = trim(String.valueOf(candidate.getOrDefault("function_module", "")));
            if (bigModule.isEmpty() || functionModule.isEmpty()) {
                continue;
            }
            known.add(bigModule + "::" + functionModule);
        }
        return known;
    }

    private static List<String> coerceStringList(Object raw) {
        if (raw instanceof List<?> list) {
            List<String> result = new ArrayList<>();
            for (Object item : list) {
                String value = trim(String.valueOf(item));
                if (!value.isEmpty()) {
                    result.add(value);
                }
            }
            return result;
        }
        String value = trim(String.valueOf(raw == null ? "" : raw));
        if (value.isEmpty()) {
            return List.of();
        }
        return List.of(value);
    }

    private static String normalizePriority(String priority) {
        String normalized = trim(priority);
        if ("高".equals(normalized) || "中".equals(normalized) || "低".equals(normalized)) {
            return normalized;
        }
        return "中";
    }

    private static String trim(String text) {
        if (text == null) {
            return "";
        }
        return text.trim();
    }

    private static String nonBlank(Object raw, String fallback) {
        String value = trim(String.valueOf(raw == null ? "" : raw));
        return value.isEmpty() ? fallback : value;
    }

    private static Object valueFromMap(Map<?, ?> source, String key) {
        if (source == null || !source.containsKey(key)) {
            return "";
        }
        Object value = source.get(key);
        return value == null ? "" : value;
    }

    private String writeJson(Object payload) {
        try {
            return objectMapper.writeValueAsString(payload);
        } catch (Exception ex) {
            return "{}";
        }
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
