package com.pmagent.backend.application.retrieval;

import com.pmagent.backend.infrastructure.entity.ModuleEntryEntity;
import com.pmagent.backend.infrastructure.support.JsonListCodec;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class ModuleIndexerTest {

    @Test
    void shouldReturnTopModulesWhenQueryMatchesModuleName() {
        ModuleIndexer indexer = new ModuleIndexer();

        ModuleEntryEntity m1 = new ModuleEntryEntity();
        m1.setBigModule("税务");
        m1.setFunctionModule("发票接口");
        m1.setPrimaryOwner("李祥");
        m1.setFamiliarMembersJson(JsonListCodec.encode(List.of("李祥")));

        ModuleEntryEntity m2 = new ModuleEntryEntity();
        m2.setBigModule("采购");
        m2.setFunctionModule("结算管理");
        m2.setPrimaryOwner("王五");
        m2.setFamiliarMembersJson(JsonListCodec.encode(List.of("王五")));

        indexer.build(List.of(m1, m2));

        List<Map<String, Object>> results = indexer.search("发票接口", 10);

        assertEquals(1, results.size());
        assertEquals("税务", results.get(0).get("big_module"));
        assertEquals("发票接口", results.get(0).get("function_module"));
    }

    @Test
    void shouldReturnEmptyWhenNoModulesIndexed() {
        ModuleIndexer indexer = new ModuleIndexer();
        List<Map<String, Object>> results = indexer.search("任何查询", 10);
        assertTrue(results.isEmpty());
    }

    @Test
    void shouldRespectTopNLimit() {
        ModuleIndexer indexer = new ModuleIndexer();
        List<ModuleEntryEntity> modules = new java.util.ArrayList<>();
        for (int i = 0; i < 50; i++) {
            ModuleEntryEntity m = new ModuleEntryEntity();
            m.setBigModule("测试模块" + i);
            m.setFunctionModule("功能" + i);
            m.setPrimaryOwner("负责人" + i);
            m.setFamiliarMembersJson(JsonListCodec.encode(List.of()));
            modules.add(m);
        }
        indexer.build(modules);

        List<Map<String, Object>> results = indexer.search("功能", 5);
        assertTrue(results.size() <= 5);
    }
}
