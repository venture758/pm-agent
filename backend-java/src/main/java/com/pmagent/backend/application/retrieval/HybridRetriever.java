package com.pmagent.backend.application.retrieval;

import com.pmagent.backend.application.config.LlmProviderProperties;
import com.pmagent.backend.infrastructure.entity.ModuleEntryEntity;
import com.pmagent.backend.infrastructure.entity.StoryRecordEntity;
import com.pmagent.backend.infrastructure.entity.TaskRecordEntity;
import com.pmagent.backend.infrastructure.llm.EmbeddingClient;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.function.Supplier;

@Component
public class HybridRetriever {

    private static final int MAX_SIGNAL_LENGTH = 80;

    private final ModuleIndexer moduleIndexer;
    private final EmbeddingClient embeddingClient;
    private final LlmProviderProperties.Retrieval retrieval;
    private final Supplier<String> embeddingBaseUrl;
    private final Supplier<String> embeddingApiKey;
    private final Supplier<String> embeddingModel;

    public HybridRetriever(ModuleIndexer moduleIndexer,
                           EmbeddingClient embeddingClient,
                           LlmProviderProperties llmProperties,
                           Supplier<String> embeddingBaseUrl,
                           Supplier<String> embeddingApiKey,
                           Supplier<String> embeddingModel) {
        this.moduleIndexer = moduleIndexer;
        this.embeddingClient = embeddingClient;
        this.retrieval = llmProperties.getRetrieval();
        this.embeddingBaseUrl = embeddingBaseUrl;
        this.embeddingApiKey = embeddingApiKey;
        this.embeddingModel = embeddingModel;
    }

    public Map<String, Object> retrieve(String workspaceId,
                                        String message,
                                        List<ModuleEntryEntity> moduleEntries,
                                        List<TaskRecordEntity> taskRecords,
                                        List<StoryRecordEntity> storyRecords) {

        if (moduleEntries == null || moduleEntries.isEmpty()) {
            var result = new LinkedHashMap<String, Object>();
            result.put("module_candidates", List.of());
            result.put("task_name_signals", List.of());
            result.put("story_name_signals", List.of());
            result.put("excluded_fields", List.of("module_path"));
            return result;
        }

        moduleIndexer.build(moduleEntries);

        // Step 1: BM25 recall
        List<Map<String, Object>> bm25Results = moduleIndexer.search(message, retrieval.getBm25TopN());
        if (bm25Results.isEmpty()) {
            bm25Results = moduleIndexer.search("", retrieval.getBm25FallbackTopN());
        }

        // Step 2: Embedding re-rank (if enabled and model configured)
        List<Map<String, Object>> topK;
        if (retrieval.isEmbeddingEnabled() && !retrieval.getEmbeddingModel().isBlank()) {
            List<String> candidateTexts = new ArrayList<>();
            for (Map<String, Object> m : bm25Results) {
                String bigModule = String.valueOf(m.get("big_module"));
                String functionModule = String.valueOf(m.get("function_module"));
                @SuppressWarnings("unchecked")
                List<String> keywords = (List<String>) m.getOrDefault("keywords", List.of());
                candidateTexts.add(bigModule + " " + functionModule + " " + String.join(" ", keywords));
            }

            List<Map<String, Object>> embeddingScores = embeddingClient.embedAndRank(
                embeddingBaseUrl.get(),
                embeddingApiKey.get(),
                embeddingModel.get(),
                message,
                candidateTexts
            );

            if (!embeddingScores.isEmpty() && embeddingScores.size() == bm25Results.size()) {
                // Merge embedding score into BM25 results
                for (int i = 0; i < bm25Results.size(); i++) {
                    bm25Results.get(i).put("embedding_score", embeddingScores.get(i).get("embedding_score"));
                }
                // Sort by embedding score
                bm25Results.sort(Comparator.<Map<String, Object>>comparingDouble(
                    m -> (Double) m.getOrDefault("embedding_score", 0.0)).reversed());
            }
            // If embedding failed, fall back to BM25 results

            topK = bm25Results.stream().limit(retrieval.getRetrievalTopK()).toList();
        } else {
            topK = bm25Results.stream().limit(retrieval.getRetrievalTopK()).toList();
        }

        // Step 3: Associate task/story signals with top-K modules
        Set<String> topModuleKeys = new HashSet<>();
        for (Map<String, Object> m : topK) {
            String bigModule = String.valueOf(m.get("big_module"));
            String functionModule = String.valueOf(m.get("function_module"));
            topModuleKeys.add(bigModule + "::" + functionModule);
        }

        List<String> taskSignals = filterSignalsByModules(taskRecords, topModuleKeys);
        List<String> storySignals = filterSignalsByModules(storyRecords, topModuleKeys);

        Map<String, Object> context = new LinkedHashMap<>();
        context.put("module_candidates", topK);
        context.put("task_name_signals", taskSignals);
        context.put("story_name_signals", storySignals);
        context.put("excluded_fields", List.of("module_path"));
        return context;
    }

    private List<String> filterSignalsByModules(List<?> records, Set<String> moduleKeys) {
        Set<String> keywords = new HashSet<>();
        for (String key : moduleKeys) {
            String[] parts = key.split("::");
            if (parts.length == 2) {
                keywords.add(parts[0]);
                keywords.add(parts[1]);
            }
        }

        Set<String> signals = new LinkedHashSet<>();
        if (records != null) {
            for (Object record : records) {
                String text = extractSignalText(record);
                if (text != null && !text.isBlank() && matchesAnyModule(text, keywords)) {
                    if (text.length() > MAX_SIGNAL_LENGTH) {
                        text = text.substring(0, MAX_SIGNAL_LENGTH);
                    }
                    signals.add(text);
                }
            }
        }
        return new ArrayList<>(signals);
    }

    private String extractSignalText(Object record) {
        if (record instanceof TaskRecordEntity task) {
            return task.getName();
        }
        if (record instanceof StoryRecordEntity story) {
            return story.getUserStoryName();
        }
        return null;
    }

    private boolean matchesAnyModule(String text, Set<String> keywords) {
        for (String kw : keywords) {
            if (text.contains(kw)) {
                return true;
            }
        }
        return false;
    }
}
