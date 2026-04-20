package com.pmagent.backend.application.llm;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

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

    @Test
    void shouldKeepMatchedModuleWhenInKnownCandidates() {
        Map<String, Object> raw = Map.of(
            "requirement_id", "REQ-1",
            "title", "发票接口改造",
            "priority", "高",
            "raw_text", "改造发票接口",
            "big_module", "税务",
            "function_module", "发票接口",
            "abstract_summary", "统一发票接口能力",
            "match_evidence", List.of("命中关键词: 发票", "参考任务: 发票接口重构"),
            "match_status", "matched"
        );
        List<Map<String, Object>> moduleCandidates = List.of(
            Map.of("big_module", "税务", "function_module", "发票接口")
        );

        Map<String, Object> normalized = LlmService.normalizeRequirementItem(raw, "改造发票接口", moduleCandidates);

        assertEquals("matched", normalized.get("match_status"));
        assertEquals("税务", normalized.get("big_module"));
        assertEquals("发票接口", normalized.get("function_module"));
        assertEquals(List.of("税务::发票接口"), normalized.get("matched_module_keys"));
    }

    @Test
    void shouldDowngradeToNeedsConfirmationWhenModuleNotInCandidates() {
        Map<String, Object> raw = Map.of(
            "title", "未知模块需求",
            "big_module", "不存在模块",
            "function_module", "未知功能",
            "match_status", "matched"
        );
        List<Map<String, Object>> moduleCandidates = List.of(
            Map.of("big_module", "税务", "function_module", "发票接口"),
            Map.of("big_module", "采购", "function_module", "结算管理")
        );

        Map<String, Object> normalized = LlmService.normalizeRequirementItem(raw, "用户原文", moduleCandidates);

        assertEquals("needs_confirmation", normalized.get("match_status"));
        assertEquals("", normalized.get("big_module"));
        assertEquals("", normalized.get("function_module"));
        assertTrue(((List<?>) normalized.get("candidate_modules")).size() > 0);
    }

    @Test
    void shouldProvideFallbackCandidatesForLowConfidenceItem() {
        Map<String, Object> raw = Map.of(
            "title", "报表优化",
            "priority", "未知",
            "match_status", "needs_confirmation",
            "match_evidence", "语义信息不足"
        );
        List<Map<String, Object>> moduleCandidates = List.of(
            Map.of("big_module", "财务", "function_module", "报表中心")
        );

        Map<String, Object> normalized = LlmService.normalizeRequirementItem(raw, "报表优化", moduleCandidates);

        assertEquals("中", normalized.get("priority"));
        assertEquals("needs_confirmation", normalized.get("match_status"));
        assertEquals("报表优化", normalized.get("abstract_summary"));
        assertEquals(List.of(), normalized.get("matched_module_keys"));
        assertEquals(1, ((List<?>) normalized.get("candidate_modules")).size());
    }
}
