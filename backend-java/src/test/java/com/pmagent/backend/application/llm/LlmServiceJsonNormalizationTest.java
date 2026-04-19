package com.pmagent.backend.application.llm;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LlmServiceJsonNormalizationTest {

    @Test
    void shouldStripMarkdownFenceWrappedJson() {
        String raw = """
            ```json
            {"summary":"ok","constraints":[]}
            ```
            """;

        String normalized = LlmService.normalizeJsonPayload(raw);

        assertEquals("{\"summary\":\"ok\",\"constraints\":[]}", normalized);
    }

    @Test
    void shouldStripLeadingAndTrailingNoise() {
        String raw = "这里是说明文本\n{\"summary\":\"ok\"}\n这是尾部说明";

        String normalized = LlmService.normalizeJsonPayload(raw);

        assertEquals("{\"summary\":\"ok\"}", normalized);
    }

    @Test
    void shouldStripTrailingNoiseWhenJsonStartsAtFirstChar() {
        String raw = "{\"summary\":\"ok\"}\n解析完成";

        String normalized = LlmService.normalizeJsonPayload(raw);

        assertEquals("{\"summary\":\"ok\"}", normalized);
    }

    @Test
    void shouldKeepPlainJsonUnchanged() {
        String raw = "{\"summary\":\"ok\"}";

        String normalized = LlmService.normalizeJsonPayload(raw);

        assertEquals("{\"summary\":\"ok\"}", normalized);
    }
}
