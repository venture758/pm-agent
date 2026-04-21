package com.pmagent.backend.infrastructure.llm;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.*;

public class EmbeddingClient {

    private static final Logger log = LoggerFactory.getLogger(EmbeddingClient.class);

    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public EmbeddingClient(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();
    }

    /**
     * @return sorted candidate list with embedding_score added, empty if API call fails
     */
    public List<Map<String, Object>> embedAndRank(
            String baseUrl, String apiKey, String model, String query,
            List<String> candidateTexts) {

        if (baseUrl == null || baseUrl.isBlank() || model == null || model.isBlank()
                || query == null || query.isBlank() || candidateTexts.isEmpty()) {
            return List.of();
        }

        try {
            List<String> allTexts = new ArrayList<>();
            allTexts.add(query);
            allTexts.addAll(candidateTexts);

            List<double[]> embeddings = batchEmbed(baseUrl, apiKey, model, allTexts);
            if (embeddings == null || embeddings.size() != allTexts.size()) {
                log.warn("Embedding API returned unexpected result");
                return List.of();
            }

            double[] queryEmbedding = embeddings.get(0);
            List<Map<String, Object>> ranked = new ArrayList<>();

            for (int i = 0; i < candidateTexts.size(); i++) {
                double similarity = cosineSimilarity(queryEmbedding, embeddings.get(i + 1));
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("embedding_score", Math.round(similarity * 1000.0) / 1000.0);
                ranked.add(item);
            }

            ranked.sort(Comparator.<Map<String, Object>>comparingDouble(
                m -> (Double) m.get("embedding_score")).reversed());
            return ranked;

        } catch (Exception ex) {
            log.warn("Embedding call failed: {}", ex.getMessage());
            return List.of();
        }
    }

    private List<double[]> batchEmbed(String baseUrl, String apiKey, String model, List<String> texts) throws Exception {
        String endpoint = baseUrl.endsWith("/") ? baseUrl + "embeddings" : baseUrl + "/embeddings";
        Map<String, Object> payload = Map.of(
            "model", model,
            "input", texts
        );
        String body = objectMapper.writeValueAsString(payload);

        var requestBuilder = HttpRequest.newBuilder()
            .uri(URI.create(endpoint))
            .timeout(Duration.ofSeconds(15))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(body));

        if (apiKey != null && !apiKey.isBlank()) {
            requestBuilder.header("Authorization", "Bearer " + apiKey);
        }

        HttpRequest request = requestBuilder.build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() >= 400) {
            throw new RuntimeException("Embedding API returned status " + response.statusCode());
        }

        JsonNode root = objectMapper.readTree(response.body());
        JsonNode dataArray = root.path("data");
        if (!dataArray.isArray() || dataArray.isEmpty()) {
            throw new RuntimeException("Embedding API returned no data");
        }

        List<double[]> embeddings = new ArrayList<>();
        for (JsonNode item : dataArray) {
            JsonNode embeddingArray = item.path("embedding");
            double[] vec = new double[embeddingArray.size()];
            for (int i = 0; i < embeddingArray.size(); i++) {
                vec[i] = embeddingArray.get(i).asDouble();
            }
            embeddings.add(vec);
        }
        return embeddings;
    }

    public static double cosineSimilarity(double[] a, double[] b) {
        double dotProduct = 0;
        double normA = 0;
        double normB = 0;
        for (int i = 0; i < a.length; i++) {
            dotProduct += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }
        if (normA == 0 || normB == 0) {
            return 0;
        }
        return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
    }
}
