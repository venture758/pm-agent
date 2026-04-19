package com.pmagent.backend.infrastructure.llm;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pmagent.backend.domain.LlmUnavailableException;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class OpenAiCompatibleLlmClient {

    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public OpenAiCompatibleLlmClient(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder().build();
    }

    public String chat(String baseUrl, String apiKey, String model, int timeoutSeconds, String prompt) {
        if (baseUrl == null || baseUrl.isBlank() || apiKey == null || apiKey.isBlank() || model == null || model.isBlank()) {
            throw new LlmUnavailableException("llm configuration is incomplete");
        }
        String endpoint = baseUrl.endsWith("/") ? baseUrl + "chat/completions" : baseUrl + "/chat/completions";
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("model", model);
            payload.put("temperature", 0.2);
            payload.put("messages", List.of(
                Map.of("role", "system", "content", "You are a strict JSON output assistant."),
                Map.of("role", "user", "content", prompt)
            ));
            String body = objectMapper.writeValueAsString(payload);

            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(endpoint))
                .timeout(Duration.ofSeconds(Math.max(timeoutSeconds, 1)))
                .header("Authorization", "Bearer " + apiKey)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() >= 400) {
                throw new LlmUnavailableException("llm upstream returned status " + response.statusCode());
            }
            JsonNode root = objectMapper.readTree(response.body());
            JsonNode contentNode = root.path("choices").path(0).path("message").path("content");
            String content = contentNode.asText("");
            if (content.isBlank()) {
                throw new LlmUnavailableException("llm returned empty content");
            }
            return content;
        } catch (LlmUnavailableException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new LlmUnavailableException("llm call failed: " + ex.getMessage(), ex);
        }
    }
}
