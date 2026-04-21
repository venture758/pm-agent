package com.pmagent.backend.application.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.function.Supplier;

@Configuration
public class RetrievalConfig {

    private final LlmProviderProperties llmProviderProperties;

    public RetrievalConfig(LlmProviderProperties llmProviderProperties) {
        this.llmProviderProperties = llmProviderProperties;
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
