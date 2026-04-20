package com.pmagent.backend.application.chat;

import com.pmagent.backend.infrastructure.entity.ModuleEntryEntity;
import com.pmagent.backend.infrastructure.entity.StoryRecordEntity;
import com.pmagent.backend.infrastructure.entity.TaskRecordEntity;
import com.pmagent.backend.infrastructure.support.JsonListCodec;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Component
public class RequirementParseContextBuilder {

    private static final int MAX_MODULE_CANDIDATES = 80;
    private static final int MAX_HISTORY_SIGNALS = 120;
    private static final int MAX_KEYWORDS_PER_MODULE = 8;
    private static final int MAX_SIGNAL_LENGTH = 80;

    public Map<String, Object> build(List<ModuleEntryEntity> moduleEntries,
                                     List<TaskRecordEntity> taskRecords,
                                     List<StoryRecordEntity> storyRecords) {
        List<Map<String, Object>> moduleCandidates = buildModuleCandidates(moduleEntries);
        List<String> taskSignals = collectTaskSignals(taskRecords);
        List<String> storySignals = collectStorySignals(storyRecords, taskRecords);

        Map<String, Object> context = new LinkedHashMap<>();
        context.put("module_candidates", moduleCandidates);
        context.put("task_name_signals", taskSignals);
        context.put("story_name_signals", storySignals);
        context.put("excluded_fields", List.of("module_path"));
        return context;
    }

    private List<Map<String, Object>> buildModuleCandidates(List<ModuleEntryEntity> moduleEntries) {
        if (moduleEntries == null || moduleEntries.isEmpty()) {
            return List.of();
        }
        Map<String, Map<String, Object>> dedup = new LinkedHashMap<>();
        for (ModuleEntryEntity entry : moduleEntries) {
            if (entry == null) {
                continue;
            }
            String bigModule = normalize(entry.getBigModule());
            String functionModule = normalize(entry.getFunctionModule());
            if (bigModule.isEmpty() || functionModule.isEmpty()) {
                continue;
            }
            String moduleKey = bigModule + "::" + functionModule;
            if (dedup.containsKey(moduleKey)) {
                continue;
            }
            Map<String, Object> candidate = new LinkedHashMap<>();
            candidate.put("module_key", moduleKey);
            candidate.put("big_module", bigModule);
            candidate.put("function_module", functionModule);
            candidate.put("keywords", collectModuleKeywords(entry));
            dedup.put(moduleKey, candidate);
            if (dedup.size() >= MAX_MODULE_CANDIDATES) {
                break;
            }
        }
        return new ArrayList<>(dedup.values());
    }

    private List<String> collectModuleKeywords(ModuleEntryEntity entry) {
        Set<String> keywords = new LinkedHashSet<>();
        addKeywordTokens(keywords, entry.getBigModule());
        addKeywordTokens(keywords, entry.getFunctionModule());
        addKeywordTokens(keywords, entry.getPrimaryOwner());
        JsonListCodec.decode(entry.getBackupOwnersJson()).forEach(value -> addKeywordTokens(keywords, value));
        JsonListCodec.decode(entry.getFamiliarMembersJson()).forEach(value -> addKeywordTokens(keywords, value));

        List<String> result = new ArrayList<>();
        for (String keyword : keywords) {
            result.add(keyword);
            if (result.size() >= MAX_KEYWORDS_PER_MODULE) {
                break;
            }
        }
        return result;
    }

    private List<String> collectTaskSignals(List<TaskRecordEntity> taskRecords) {
        Set<String> signals = new LinkedHashSet<>();
        if (taskRecords != null) {
            for (TaskRecordEntity task : taskRecords) {
                if (task == null) {
                    continue;
                }
                addSignal(signals, task.getName());
            }
        }
        return limitSignals(signals);
    }

    private List<String> collectStorySignals(List<StoryRecordEntity> storyRecords, List<TaskRecordEntity> taskRecords) {
        Set<String> signals = new LinkedHashSet<>();
        if (storyRecords != null) {
            for (StoryRecordEntity story : storyRecords) {
                if (story == null) {
                    continue;
                }
                addSignal(signals, story.getUserStoryName());
            }
        }
        if (taskRecords != null) {
            for (TaskRecordEntity task : taskRecords) {
                if (task == null) {
                    continue;
                }
                addSignal(signals, task.getRelatedStory());
            }
        }
        return limitSignals(signals);
    }

    private List<String> limitSignals(Set<String> signals) {
        if (signals.isEmpty()) {
            return List.of();
        }
        List<String> result = new ArrayList<>();
        for (String signal : signals) {
            result.add(signal);
            if (result.size() >= MAX_HISTORY_SIGNALS) {
                break;
            }
        }
        return result;
    }

    private void addSignal(Set<String> signals, String value) {
        String normalized = normalize(value);
        if (normalized.isEmpty()) {
            return;
        }
        if (normalized.length() > MAX_SIGNAL_LENGTH) {
            normalized = normalized.substring(0, MAX_SIGNAL_LENGTH);
        }
        signals.add(normalized);
    }

    private void addKeywordTokens(Set<String> keywords, String value) {
        String normalized = normalize(value);
        if (normalized.isEmpty()) {
            return;
        }
        for (String token : normalized.split("[\\s,，;；、/|]+")) {
            String candidate = normalize(token);
            if (!candidate.isEmpty()) {
                keywords.add(candidate);
            }
        }
    }

    private String normalize(String text) {
        if (text == null) {
            return "";
        }
        return text.trim().replaceAll("\\s+", " ");
    }
}
