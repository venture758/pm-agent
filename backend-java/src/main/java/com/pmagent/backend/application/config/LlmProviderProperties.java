package com.pmagent.backend.application.config;

import jakarta.validation.constraints.Min;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "pm-agent.llm")
public class LlmProviderProperties {

    private Tier primary = new Tier();
    private Tier fallback = new Tier();
    private Retrieval retrieval = new Retrieval();

    public Tier getPrimary() {
        return primary;
    }

    public void setPrimary(Tier primary) {
        this.primary = primary;
    }

    public Tier getFallback() {
        return fallback;
    }

    public void setFallback(Tier fallback) {
        this.fallback = fallback;
    }

    public Retrieval getRetrieval() {
        return retrieval;
    }

    public void setRetrieval(Retrieval retrieval) {
        this.retrieval = retrieval;
    }

    public static class Tier {
        private String baseUrl = "";
        private String model = "";
        private String apiKey = "";
        @Min(1)
        private int timeoutSeconds = 30;
        @Min(0)
        private int retryTimes = 1;

        public String getBaseUrl() {
            return baseUrl;
        }

        public void setBaseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
        }

        public String getModel() {
            return model;
        }

        public void setModel(String model) {
            this.model = model;
        }

        public String getApiKey() {
            return apiKey;
        }

        public void setApiKey(String apiKey) {
            this.apiKey = apiKey;
        }

        public int getTimeoutSeconds() {
            return timeoutSeconds;
        }

        public void setTimeoutSeconds(int timeoutSeconds) {
            this.timeoutSeconds = timeoutSeconds;
        }

        public int getRetryTimes() {
            return retryTimes;
        }

        public void setRetryTimes(int retryTimes) {
            this.retryTimes = retryTimes;
        }
    }

    public static class Retrieval {
        private boolean embeddingEnabled = true;
        private String embeddingModel = "";
        private int bm25TopN = 20;
        private int retrievalTopK = 8;
        private int bm25FallbackTopN = 5;

        public boolean isEmbeddingEnabled() {
            return embeddingEnabled;
        }

        public void setEmbeddingEnabled(boolean embeddingEnabled) {
            this.embeddingEnabled = embeddingEnabled;
        }

        public String getEmbeddingModel() {
            return embeddingModel;
        }

        public void setEmbeddingModel(String embeddingModel) {
            this.embeddingModel = embeddingModel;
        }

        public int getBm25TopN() {
            return bm25TopN;
        }

        public void setBm25TopN(int bm25TopN) {
            this.bm25TopN = bm25TopN;
        }

        public int getRetrievalTopK() {
            return retrievalTopK;
        }

        public void setRetrievalTopK(int retrievalTopK) {
            this.retrievalTopK = retrievalTopK;
        }

        public int getBm25FallbackTopN() {
            return bm25FallbackTopN;
        }

        public void setBm25FallbackTopN(int bm25FallbackTopN) {
            this.bm25FallbackTopN = bm25FallbackTopN;
        }
    }
}
