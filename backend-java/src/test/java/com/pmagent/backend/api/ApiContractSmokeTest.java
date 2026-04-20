package com.pmagent.backend.api;

import com.pmagent.backend.api.common.ApiResponse;
import com.pmagent.backend.api.common.PageResult;
import com.pmagent.backend.api.controller.HealthController;
import com.pmagent.backend.api.web.GlobalExceptionHandler;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class ApiContractSmokeTest {

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders
            .standaloneSetup(new HealthController(), new ContractProbeController())
            .setControllerAdvice(new GlobalExceptionHandler())
            .build();
    }

    @Test
    void healthEndpointUsesUnifiedEnvelope() throws Exception {
        mockMvc.perform(get("/api/v2/health"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(0))
            .andExpect(jsonPath("$.message").value("ok"))
            .andExpect(jsonPath("$.data.status").value("ok"));
    }

    @Test
    void pagedContractUsesUnifiedPaginationFields() throws Exception {
        mockMvc.perform(get("/api/v2/contract/paged").accept(MediaType.APPLICATION_JSON))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(0))
            .andExpect(jsonPath("$.data.page").value(2))
            .andExpect(jsonPath("$.data.pageSize").value(5))
            .andExpect(jsonPath("$.data.total").value(11))
            .andExpect(jsonPath("$.data.items[0].id").value("item-1"));
    }

    @Test
    void badRequestUsesFailureEnvelope() throws Exception {
        mockMvc.perform(get("/api/v2/contract/bad-request").accept(MediaType.APPLICATION_JSON))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.code").value(40000))
            .andExpect(jsonPath("$.message").value("bad_input"))
            .andExpect(jsonPath("$.data").doesNotExist());
    }

    @Test
    void chatContractSupportsModuleAttributionFields() throws Exception {
        mockMvc.perform(get("/api/v2/contract/chat").accept(MediaType.APPLICATION_JSON))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(0))
            .andExpect(jsonPath("$.data.messages[1].parsed_requirements[0].big_module").value("税务"))
            .andExpect(jsonPath("$.data.messages[1].parsed_requirements[0].function_module").value("发票接口"))
            .andExpect(jsonPath("$.data.messages[1].parsed_requirements[0].abstract_summary").value("统一发票接口能力"))
            .andExpect(jsonPath("$.data.messages[1].parsed_requirements[0].match_status").value("needs_confirmation"))
            .andExpect(jsonPath("$.data.messages[1].parsed_requirements[0].match_evidence[0]").value("命中关键词: 发票"))
            .andExpect(jsonPath("$.data.messages[1].parsed_requirements[0].candidate_modules[0].big_module").value("税务"));
    }

    @RestController
    public static class ContractProbeController {

        @GetMapping("/api/v2/contract/paged")
        public ApiResponse<PageResult<Map<String, Object>>> paged() {
            return ApiResponse.success(
                new PageResult<>(2, 5, 11, List.of(Map.of("id", "item-1")))
            );
        }

        @GetMapping("/api/v2/contract/bad-request")
        public ApiResponse<Void> badRequest() {
            throw new IllegalArgumentException("bad_input");
        }

        @GetMapping("/api/v2/contract/chat")
        public ApiResponse<Map<String, Object>> chat() {
            return ApiResponse.success(
                Map.of(
                    "messages", List.of(
                        Map.of("role", "user", "content", "新增发票需求"),
                        Map.of(
                            "role", "assistant",
                            "content", "已解析需求",
                            "parsed_requirements", List.of(
                                Map.of(
                                    "requirement_id", "REQ-1",
                                    "title", "发票接口改造",
                                    "big_module", "税务",
                                    "function_module", "发票接口",
                                    "abstract_summary", "统一发票接口能力",
                                    "match_status", "needs_confirmation",
                                    "match_evidence", List.of("命中关键词: 发票"),
                                    "candidate_modules", List.of(
                                        Map.of(
                                            "big_module", "税务",
                                            "function_module", "发票接口",
                                            "reason", "历史任务名称高度相关"
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            );
        }
    }
}
