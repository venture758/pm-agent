package com.pmagent.backend.application.config;

import jakarta.validation.constraints.Min;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "pm-agent.llm")
public class LlmProviderProperties {

    private Tier primary = new Tier();
    private Tier fallback = new Tier();

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
}
