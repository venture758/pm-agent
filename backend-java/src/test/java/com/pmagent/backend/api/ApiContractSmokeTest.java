package com.pmagent.backend.api;

import com.pmagent.backend.api.common.ApiResponse;
import com.pmagent.backend.api.common.PageResult;
import com.pmagent.backend.api.controller.HealthController;
import com.pmagent.backend.api.web.GlobalExceptionHandler;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = HealthController.class)
@Import({
    GlobalExceptionHandler.class,
    ApiContractSmokeTest.ContractProbeController.class
})
class ApiContractSmokeTest {

    @Autowired
    private MockMvc mockMvc;

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
    }
}
