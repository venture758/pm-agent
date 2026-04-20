package com.pmagent.backend.application.chat;

import com.pmagent.backend.infrastructure.entity.ModuleEntryEntity;
import com.pmagent.backend.infrastructure.entity.StoryRecordEntity;
import com.pmagent.backend.infrastructure.entity.TaskRecordEntity;
import com.pmagent.backend.infrastructure.support.JsonListCodec;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RequirementParseContextBuilderTest {

    private final RequirementParseContextBuilder builder = new RequirementParseContextBuilder();

    @Test
    void shouldBuildContextWithModuleCandidatesAndHistorySignals() {
        ModuleEntryEntity module = new ModuleEntryEntity();
        module.setBigModule("税务");
        module.setFunctionModule("发票接口");
        module.setPrimaryOwner("李祥");
        module.setBackupOwnersJson(JsonListCodec.encode(List.of("王海林")));
        module.setFamiliarMembersJson(JsonListCodec.encode(List.of("李祥")));

        TaskRecordEntity task = new TaskRecordEntity();
        task.setName("发票接口重构");
        task.setRelatedStory("发票开具流程优化");

        StoryRecordEntity story = new StoryRecordEntity();
        story.setUserStoryName("电子发票红冲支持");

        Map<String, Object> context = builder.build(List.of(module), List.of(task), List.of(story));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> moduleCandidates = (List<Map<String, Object>>) context.get("module_candidates");
        assertEquals(1, moduleCandidates.size());
        assertEquals("税务", moduleCandidates.get(0).get("big_module"));
        assertEquals("发票接口", moduleCandidates.get(0).get("function_module"));
        assertTrue(((List<?>) moduleCandidates.get(0).get("keywords")).contains("发票接口"));

        @SuppressWarnings("unchecked")
        List<String> taskSignals = (List<String>) context.get("task_name_signals");
        @SuppressWarnings("unchecked")
        List<String> storySignals = (List<String>) context.get("story_name_signals");
        assertEquals(List.of("发票接口重构"), taskSignals);
        assertTrue(storySignals.contains("电子发票红冲支持"));
        assertTrue(storySignals.contains("发票开具流程优化"));
    }

    @Test
    void shouldExcludeModulePathFromContextEvenIfHistoryContainsNoise() {
        TaskRecordEntity task = new TaskRecordEntity();
        task.setName("修复开票任务 module_path=错误路径");

        Map<String, Object> context = builder.build(List.of(), List.of(task), List.of());

        assertFalse(context.containsKey("module_path"));
        assertEquals(List.of("module_path"), context.get("excluded_fields"));
        @SuppressWarnings("unchecked")
        List<String> taskSignals = (List<String>) context.get("task_name_signals");
        assertEquals(1, taskSignals.size());
    }
}
