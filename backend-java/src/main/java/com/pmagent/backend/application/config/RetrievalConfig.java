package com.pmagent.backend.application.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pmagent.backend.infrastructure.llm.EmbeddingClient;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.function.Supplier;

@Configuration
public class RetrievalConfig {

    private final LlmProviderProperties llmProviderProperties;
    private final ObjectMapper objectMapper;

    public RetrievalConfig(LlmProviderProperties llmProviderProperties, ObjectMapper objectMapper) {
        this.llmProviderProperties = llmProviderProperties;
        this.objectMapper = objectMapper;
    }

    @Bean
    public EmbeddingClient embeddingClient() {
        return new EmbeddingClient(objectMapper);
    }

    @Bean
    public Supplier<String> embeddingBaseUrl() {
        return () -> llmProviderProperties.getPrimary().getBaseUrl();
    }

    @Bean
    public Supplier<String> embeddingApiKey() {
        return () -> llmProviderProperties.getPrimary().getApiKey();
    }

    @Bean
    public Supplier<String> embeddingModel() {
        return () -> llmProviderProperties.getRetrieval().getEmbeddingModel();
    }
}
