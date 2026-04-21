package com.pmagent.backend.application.retrieval;

import com.pmagent.backend.application.config.LlmProviderProperties;
import com.pmagent.backend.infrastructure.entity.ModuleEntryEntity;
import com.pmagent.backend.infrastructure.entity.StoryRecordEntity;
import com.pmagent.backend.infrastructure.entity.TaskRecordEntity;
import com.pmagent.backend.infrastructure.llm.EmbeddingClient;
import com.pmagent.backend.infrastructure.support.JsonListCodec;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class HybridRetrieverTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void shouldReturnRetrievedContext() {
        ModuleEntryEntity m1 = new ModuleEntryEntity();
        m1.setWorkspaceId("ws-1");
        m1.setBigModule("税务");
        m1.setFunctionModule("发票接口");
        m1.setPrimaryOwner("李祥");
        m1.setFamiliarMembersJson(JsonListCodec.encode(List.of("李祥")));

        ModuleEntryEntity m2 = new ModuleEntryEntity();
        m2.setWorkspaceId("ws-1");
        m2.setBigModule("采购");
        m2.setFunctionModule("结算管理");
        m2.setPrimaryOwner("王五");
        m2.setFamiliarMembersJson(JsonListCodec.encode(List.of("王五")));

        TaskRecordEntity task = new TaskRecordEntity();
        task.setName("发票接口改造");

        StoryRecordEntity story = new StoryRecordEntity();
        story.setUserStoryName("发票开具优化");

        ModuleIndexer indexer = new ModuleIndexer();
        indexer.build(List.of(m1, m2));

        EmbeddingClient embeddingClient = new EmbeddingClient(objectMapper);
        LlmProviderProperties.Retrieval retrieval = new LlmProviderProperties.Retrieval();
        retrieval.setEmbeddingEnabled(false); // disable embedding for unit test

        HybridRetriever retriever = new HybridRetriever(
            indexer, embeddingClient, createLlmProperties(retrieval),
            () -> "", () -> "", () -> ""
        );

        Map<String, Object> context = retriever.retrieve("ws-1", "发票接口改造",
            List.of(m1, m2), List.of(task), List.of(story));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> candidates = (List<Map<String, Object>>) context.get("module_candidates");
        assertFalse(candidates.isEmpty());
        assertEquals("税务", candidates.get(0).get("big_module"));

        @SuppressWarnings("unchecked")
        List<String> taskSignals = (List<String>) context.get("task_name_signals");
        assertFalse(taskSignals.isEmpty());
    }

    @Test
    void shouldReturnEmptyContextWhenNoModules() {
        ModuleIndexer indexer = new ModuleIndexer();
        indexer.build(List.of());

        EmbeddingClient embeddingClient = new EmbeddingClient(objectMapper);
        LlmProviderProperties.Retrieval retrieval = new LlmProviderProperties.Retrieval();
        retrieval.setEmbeddingEnabled(false);

        HybridRetriever retriever = new HybridRetriever(
            indexer, embeddingClient, createLlmProperties(retrieval),
            () -> "", () -> "", () -> ""
        );

        Map<String, Object> context = retriever.retrieve("ws-1", "任何消息",
            List.of(), List.of(), List.of());

        assertTrue(((List<?>) context.get("module_candidates")).isEmpty());
        assertTrue(((List<?>) context.get("task_name_signals")).isEmpty());
        assertTrue(((List<?>) context.get("story_name_signals")).isEmpty());
    }

    private LlmProviderProperties createLlmProperties(LlmProviderProperties.Retrieval retrieval) {
        LlmProviderProperties props = new LlmProviderProperties();
        props.setRetrieval(retrieval);
        return props;
    }
}
