package com.pmagent.backend.infrastructure.llm;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class EmbeddingClientTest {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final EmbeddingClient client = new EmbeddingClient(objectMapper);

    @Test
    void shouldReturnEmptyWhenBaseUrlIsBlank() {
        List<Map<String, Object>> results = client.embedAndRank(
            "", "", "text-embedding-3-small", "测试查询",
            List.of("候选1", "候选2")
        );
        assertTrue(results.isEmpty());
    }

    @Test
    void shouldReturnEmptyWhenModelIsBlank() {
        List<Map<String, Object>> results = client.embedAndRank(
            "http://localhost:8080", "", "", "测试查询",
            List.of("候选1", "候选2")
        );
        assertTrue(results.isEmpty());
    }

    @Test
    void shouldReturnEmptyWhenEmbeddingFails() {
        List<Map<String, Object>> results = client.embedAndRank(
            "http://localhost:9999", "", "invalid-model", "测试查询",
            List.of("候选1", "候选2")
        );
        assertTrue(results.isEmpty());
    }

    @Test
    void shouldComputeCosineSimilarityCorrectly() {
        double[] a = {1.0, 0.0, 0.0};
        double[] b = {1.0, 0.0, 0.0};
        double[] c = {0.0, 1.0, 0.0};

        assertEquals(1.0, EmbeddingClient.cosineSimilarity(a, b), 0.001);
        assertEquals(0.0, EmbeddingClient.cosineSimilarity(a, c), 0.001);
    }

    @Test
    void shouldComputeCosineSimilarityForIdenticalVectors() {
        double[] a = {0.5, 0.5, 0.707};
        assertEquals(1.0, EmbeddingClient.cosineSimilarity(a, a), 0.001);
    }
}
