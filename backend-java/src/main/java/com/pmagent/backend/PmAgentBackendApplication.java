package com.pmagent.backend;

import com.pmagent.backend.application.config.LlmProviderProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties({LlmProviderProperties.class})
public class PmAgentBackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(PmAgentBackendApplication.class, args);
    }
}
