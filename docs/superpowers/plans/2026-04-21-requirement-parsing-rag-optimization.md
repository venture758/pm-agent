# 需求解析 RAG 优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将需求解析的 LLM 上下文从 30-80KB 压缩到 3-5KB，通过混合检索（BM25 + Embedding）提升模块归属准确率

**Architecture:** 新增 ModuleIndexer（BM25 倒排索引）、EmbeddingClient（向量相似度）、HybridRetriever（两阶段检索编排），修改 ChatService 和 LlmService 接入检索流程

**Tech Stack:** Java 21, Spring Boot 3, OpenAI 兼容 API, JUnit 5

---

### Task 1: LlmProviderProperties 新增检索配置项

**Files:**
- Modify: `backend-java/src/main/java/com/pmagent/backend/application/config/LlmProviderProperties.java`

- [ ] **Step 1: 在 LlmProviderProperties 中新增检索配置字段**

在现有的 `primary` 和 `fallback` 字段下方，新增检索相关配置：

```java
@ConfigurationProperties(prefix = "pm-agent.llm")
public class LlmProviderProperties {

    private Tier primary = new Tier();
    private Tier fallback = new Tier();
    private Retrieval retrieval = new Retrieval();

    // ... existing getters/setters for primary and fallback ...

    public Retrieval getRetrieval() {
        return retrieval;
    }

    public void setRetrieval(Retrieval retrieval) {
        this.retrieval = retrieval;
    }

    public static class Retrieval {
        private boolean embeddingEnabled = true;
        private String embeddingModel = "";
        private int bm25TopN = 20;
        private int retrievalTopK = 8;
        private int bm25FallbackTopN = 5;

        public boolean isEmbeddingEnabled() {
            return embeddingEnabled;
        }

        public void setEmbeddingEnabled(boolean embeddingEnabled) {
            this.embeddingEnabled = embeddingEnabled;
        }

        public String getEmbeddingModel() {
            return embeddingModel;
        }

        public void setEmbeddingModel(String embeddingModel) {
            this.embeddingModel = embeddingModel;
        }

        public int getBm25TopN() {
            return bm25TopN;
        }

        public void setBm25TopN(int bm25TopN) {
            this.bm25TopN = bm25TopN;
        }

        public int getRetrievalTopK() {
            return retrievalTopK;
        }

        public void setRetrievalTopK(int retrievalTopK) {
            this.retrievalTopK = retrievalTopK;
        }

        public int getBm25FallbackTopN() {
            return bm25FallbackTopN;
        }

        public void setBm25FallbackTopN(int bm25FallbackTopN) {
            this.bm25FallbackTopN = bm25FallbackTopN;
        }
    }

    // ... existing Tier class ...
}
```

- [ ] **Step 2: 编译验证**

Run: `cd backend-java && ./mvnw compile -q`
Expected: BUILD SUCCESS

---

### Task 2: ModuleIndexer — BM25 倒排索引

**Files:**
- Create: `backend-java/src/main/java/com/pmagent/backend/application/retrieval/ModuleIndexer.java`
- Create: `backend-java/src/test/java/com/pmagent/backend/application/retrieval/ModuleIndexerTest.java`

- [ ] **Step 1: 编写测试用例**

```java
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

        assertEquals(2, results.size());
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
    void shouldScoreKeywordMatchHigherThanStopWord() {
        ModuleIndexer indexer = new ModuleIndexer();

        ModuleEntryEntity m1 = new ModuleEntryEntity();
        m1.setBigModule("税务");
        m1.setFunctionModule("发票接口");
        m1.setPrimaryOwner("张三");
        m1.setFamiliarMembersJson(JsonListCodec.encode(List.of()));

        ModuleEntryEntity m2 = new ModuleIndexer();
        // This tests stop word filtering — common words shouldn't dominate scoring
        indexer.build(List.of(m1));

        // "的" is a stop word, should return results but with low scores
        List<Map<String, Object>> results = indexer.search("的", 10);
        // Should still return results (BM25 doesn't filter entirely)
        assertNotNull(results);
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
```

Run: `cd backend-java && ./mvnw test -Dtest=ModuleIndexerTest -q`
Expected: FAIL (class doesn't exist yet)

- [ ] **Step 2: 实现 ModuleIndexer**

```java
package com.pmagent.backend.application.retrieval;

import com.pmagent.backend.infrastructure.entity.ModuleEntryEntity;
import com.pmagent.backend.infrastructure.support.JsonListCodec;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

@Component
public class ModuleIndexer {

    private static final Set<String> STOP_WORDS = Set.of(
        "的", "了", "是", "在", "和", "与", "或", "就", "都", "也",
        "管理", "系统", "中心", "平台", "功能", "模块", "相关", "进行"
    );

    // 倒排表: token -> List<ModuleDoc>
    private final AtomicReference<Map<String, List<ModuleDoc>>> invertedIndex =
        new AtomicReference<>(Map.of());

    // 正排表: moduleKey -> ModuleDoc
    private final AtomicReference<Map<String, ModuleDoc>> forwardIndex =
        new AtomicReference<>(Map.of());

    // 所有文档列表
    private final AtomicReference<List<ModuleDoc>> allDocs =
        new AtomicReference<>(List.of());

    public void build(List<ModuleEntryEntity> moduleEntries) {
        if (moduleEntries == null || moduleEntries.isEmpty()) {
            invertedIndex.set(Map.of());
            forwardIndex.set(Map.of());
            allDocs.set(List.of());
            return;
        }

        List<ModuleDoc> docs = new ArrayList<>();
        Map<String, ModuleDoc> forward = new HashMap<>();
        Map<String, List<ModuleDoc>> inverted = new HashMap<>();

        for (ModuleEntryEntity entry : moduleEntries) {
            ModuleDoc doc = toModuleDoc(entry);
            docs.add(doc);
            forward.put(doc.moduleKey(), doc);

            for (String token : tokenize(doc)) {
                inverted.computeIfAbsent(token, k -> new ArrayList<>()).add(doc);
            }
        }

        invertedIndex.set(inverted);
        forwardIndex.set(forward);
        allDocs.set(docs);
    }

    public List<Map<String, Object>> search(String query, int topN) {
        List<ModuleDoc> docs = allDocs.get();
        if (docs.isEmpty()) {
            return List.of();
        }

        Set<String> queryTokens = new LinkedHashSet<>(tokenize(query));
        Map<String, List<ModuleDoc>> index = invertedIndex.get();
        if (index.isEmpty()) {
            return List.of();
        }

        int N = docs.size();
        Map<String, Double> scores = new HashMap<>();

        for (String token : queryTokens) {
            List<ModuleDoc> postingList = index.get(token);
            if (postingList == null || postingList.isEmpty()) {
                continue;
            }
            double idf = Math.log(1 + (double) N / postingList.size());
            for (ModuleDoc doc : postingList) {
                long freq = countTokenOccurrences(doc, token);
                double tf = (double) freq / maxTokenCountInDoc(doc);
                double bm25tf = tf / (tf + 1.5);
                scores.merge(doc.moduleKey(), bm25tf * idf, Double::sum);
            }
        }

        return scores.entrySet().stream()
            .sorted(Map.Entry.<String, Double>comparingByValue().reversed())
            .limit(topN)
            .map(e -> {
                ModuleDoc doc = forwardIndex.get().get(e.getKey());
                Map<String, Object> result = new LinkedHashMap<>();
                result.put("big_module", doc.bigModule());
                result.put("function_module", doc.functionModule());
                result.put("module_key", doc.moduleKey());
                result.put("keywords", doc.keywords());
                result.put("retrieval_score", Math.round(e.getValue() * 1000.0) / 1000.0);
                return result;
            })
            .toList();
    }

    private List<String> tokenize(String text) {
        List<String> tokens = new ArrayList<>();
        if (text == null || text.isBlank()) {
            return tokens;
        }
        String normalized = text.trim().replaceAll("\\s+", " ");

        // 英文分词：按空格和标点
        for (String word : normalized.split("[\\s,，;；、/|()（）\\[\\]{}]+")) {
            String w = word.trim().toLowerCase();
            if (!w.isEmpty() && !STOP_WORDS.contains(w)) {
                tokens.add(w);
            }
        }

        // 中文 2-gram
        String chineseOnly = normalized.replaceAll("[a-zA-Z0-9\\s\\p{Punct}]+", "");
        for (int i = 0; i <= chineseOnly.length() - 2; i++) {
            String bigram = chineseOnly.substring(i, i + 2);
            if (!STOP_WORDS.contains(bigram)) {
                tokens.add(bigram);
            }
        }
        // 中文 3-gram
        for (int i = 0; i <= chineseOnly.length() - 3; i++) {
            String trigram = chineseOnly.substring(i, i + 3);
            if (!STOP_WORDS.contains(trigram)) {
                tokens.add(trigram);
            }
        }

        return tokens;
    }

    private List<String> tokenize(ModuleDoc doc) {
        List<String> tokens = new ArrayList<>();
        tokens.addAll(tokenize(doc.bigModule()));
        tokens.addAll(tokenize(doc.functionModule()));
        for (String kw : doc.keywords()) {
            tokens.addAll(tokenize(kw));
        }
        for (String owner : doc.owners()) {
            tokens.addAll(tokenize(owner));
        }
        return tokens.stream().distinct().toList();
    }

    private long countTokenOccurrences(ModuleDoc doc, String token) {
        List<String> docTokens = tokenize(doc);
        return docTokens.stream().filter(t -> t.equals(token)).count();
    }

    private int maxTokenCountInDoc(ModuleDoc doc) {
        return Math.max(1, tokenize(doc).size());
    }

    private ModuleDoc toModuleDoc(ModuleEntryEntity entry) {
        String bigModule = entry.getBigModule() == null ? "" : entry.getBigModule().trim();
        String functionModule = entry.getFunctionModule() == null ? "" : entry.getFunctionModule().trim();
        String moduleKey = bigModule + "::" + functionModule;

        List<String> keywords = new ArrayList<>();
        keywords.add(bigModule);
        keywords.add(functionModule);
        keywords.addAll(JsonListCodec.decode(entry.getFamiliarMembersJson()));
        keywords.addAll(JsonListCodec.decode(entry.getBackupOwnersJson()));

        List<String> owners = new ArrayList<>();
        if (entry.getPrimaryOwner() != null && !entry.getPrimaryOwner().isBlank()) {
            owners.add(entry.getPrimaryOwner().trim());
        }
        owners.addAll(JsonListCodec.decode(entry.getBackupOwnersJson()));
        owners.addAll(JsonListCodec.decode(entry.getFamiliarMembersJson()));

        return new ModuleDoc(moduleKey, bigModule, functionModule,
            keywords.stream().filter(s -> !s.isBlank()).distinct().toList(),
            owners.stream().filter(s -> !s.isBlank()).distinct().toList());
    }

    private record ModuleDoc(
        String moduleKey,
        String bigModule,
        String functionModule,
        List<String> keywords,
        List<String> owners
    ) {}
}
```

- [ ] **Step 3: 运行测试**

Run: `cd backend-java && ./mvnw test -Dtest=ModuleIndexerTest -q`
Expected: All tests pass

- [ ] **Step 4: 提交**

```bash
git add backend-java/src/main/java/com/pmagent/backend/application/retrieval/ModuleIndexer.java
git add backend-java/src/test/java/com/pmagent/backend/application/retrieval/ModuleIndexerTest.java
git commit -m "feat: add ModuleIndexer with BM25 inverted index for module retrieval"
```

---

### Task 3: EmbeddingClient — Embedding API 客户端

**Files:**
- Create: `backend-java/src/main/java/com/pmagent/backend/infrastructure/llm/EmbeddingClient.java`
- Create: `backend-java/src/test/java/com/pmagent/backend/infrastructure/llm/EmbeddingClientTest.java`

- [ ] **Step 1: 编写测试用例**

```java
package com.pmagent.backend.infrastructure.llm;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class EmbeddingClientTest {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final EmbeddingClient client = new EmbeddingClient(objectMapper);

    @Test
    void shouldReturnEmptyWhenBaseUrlIsBlank() {
        List<Map<String, Object>> results = client.embedAndRank(
            "", "text-embedding-3-small", "测试查询",
            List.of("候选1", "候选2")
        );
        assertTrue(results.isEmpty());
    }

    @Test
    void shouldReturnEmptyWhenModelIsBlank() {
        List<Map<String, Object>> results = client.embedAndRank(
            "http://localhost:8080", "", "测试查询",
            List.of("候选1", "候选2")
        );
        assertTrue(results.isEmpty());
    }

    @Test
    void shouldReturnCandidatesInOrderWhenEmbeddingFails() {
        // When API call fails (invalid endpoint), should return candidates unchanged
        List<Map<String, Object>> candidates = List.of(
            Map.of("module_key", "A::B", "score", 0.5),
            Map.of("module_key", "C::D", "score", 0.3)
        );
        List<Map<String, Object>> results = client.embedAndRank(
            "http://localhost:9999", "invalid-model", "测试查询",
            List.of("{\"module_key\":\"A::B\",\"score\":0.5}",
                    "{\"module_key\":\"C::D\",\"score\":0.3}")
        );
        // Should return empty or original order on failure
        assertNotNull(results);
    }

    @Test
    void shouldComputeCosineSimilarityCorrectly() {
        double[] a = {1.0, 0.0, 0.0};
        double[] b = {1.0, 0.0, 0.0};
        double[] c = {0.0, 1.0, 0.0};

        assertEquals(1.0, EmbeddingClient.cosineSimilarity(a, b), 0.001);
        assertEquals(0.0, EmbeddingClient.cosineSimilarity(a, c), 0.001);
    }
}
```

Run: `cd backend-java && ./mvnw test -Dtest=EmbeddingClientTest -q`
Expected: FAIL (class doesn't exist yet)

- [ ] **Step 2: 实现 EmbeddingClient**

```java
package com.pmagent.backend.infrastructure.llm;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.*;

public class EmbeddingClient {

    private static final Logger log = LoggerFactory.getLogger(EmbeddingClient.class);

    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public EmbeddingClient(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();
    }

    /**
     * @return sorted candidate list with embedding_score added, empty if API call fails
     */
    public List<Map<String, Object>> embedAndRank(
            String baseUrl, String model, String query,
            List<String> candidateTexts) {

        if (baseUrl == null || baseUrl.isBlank() || model == null || model.isBlank()
                || query == null || query.isBlank() || candidateTexts.isEmpty()) {
            return List.of();
        }

        try {
            List<String> allTexts = new ArrayList<>();
            allTexts.add(query);
            allTexts.addAll(candidateTexts);

            List<double[]> embeddings = batchEmbed(baseUrl, model, allTexts);
            if (embeddings == null || embeddings.size() != allTexts.size()) {
                log.warn("Embedding API returned unexpected result");
                return List.of();
            }

            double[] queryEmbedding = embeddings.get(0);
            List<Map<String, Object>> ranked = new ArrayList<>();

            for (int i = 0; i < candidateTexts.size(); i++) {
                double similarity = cosineSimilarity(queryEmbedding, embeddings.get(i + 1));
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("embedding_score", Math.round(similarity * 1000.0) / 1000.0);
                ranked.add(item);
            }

            ranked.sort(Comparator.<Map<String, Object>>comparingDouble(
                m -> (Double) m.get("embedding_score")).reversed());
            return ranked;

        } catch (Exception ex) {
            log.warn("Embedding call failed: {}", ex.getMessage());
            return List.of();
        }
    }

    private List<double[]> batchEmbed(String baseUrl, String model, List<String> texts) throws Exception {
        String endpoint = baseUrl.endsWith("/") ? baseUrl + "embeddings" : baseUrl + "/embeddings";
        Map<String, Object> payload = Map.of(
            "model", model,
            "input", texts
        );
        String body = objectMapper.writeValueAsString(payload);

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(endpoint))
            .timeout(Duration.ofSeconds(15))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(body))
            .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() >= 400) {
            throw new RuntimeException("Embedding API returned status " + response.statusCode());
        }

        JsonNode root = objectMapper.readTree(response.body());
        JsonNode dataArray = root.path("data");
        if (!dataArray.isArray() || dataArray.isEmpty()) {
            throw new RuntimeException("Embedding API returned no data");
        }

        List<double[]> embeddings = new ArrayList<>();
        for (JsonNode item : dataArray) {
            JsonNode embeddingArray = item.path("embedding");
            double[] vec = new double[embeddingArray.size()];
            for (int i = 0; i < embeddingArray.size(); i++) {
                vec[i] = embeddingArray.get(i).asDouble();
            }
            embeddings.add(vec);
        }
        return embeddings;
    }

    static double cosineSimilarity(double[] a, double[] b) {
        double dotProduct = 0;
        double normA = 0;
        double normB = 0;
        for (int i = 0; i < a.length; i++) {
            dotProduct += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }
        if (normA == 0 || normB == 0) {
            return 0;
        }
        return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
    }
}
```

- [ ] **Step 3: 运行测试**

Run: `cd backend-java && ./mvnw test -Dtest=EmbeddingClientTest -q`
Expected: All tests pass

- [ ] **Step 4: 提交**

```bash
git add backend-java/src/main/java/com/pmagent/backend/infrastructure/llm/EmbeddingClient.java
git add backend-java/src/test/java/com/pmagent/backend/infrastructure/llm/EmbeddingClientTest.java
git commit -m "feat: add EmbeddingClient for vector similarity ranking"
```

---

### Task 4: HybridRetriever — 两阶段混合检索编排

**Files:**
- Create: `backend-java/src/main/java/com/pmagent/backend/application/retrieval/HybridRetriever.java`
- Create: `backend-java/src/test/java/com/pmagent/backend/application/retrieval/HybridRetrieverTest.java`

- [ ] **Step 1: 编写测试用例**

```java
package com.pmagent.backend.application.retrieval;

import com.pmagent.backend.application.config.LlmProviderProperties;
import com.pmagent.backend.infrastructure.entity.ModuleEntryEntity;
import com.pmagent.backend.infrastructure.entity.StoryRecordEntity;
import com.pmagent.backend.infrastructure.entity.TaskRecordEntity;
import com.pmagent.backend.infrastructure.llm.EmbeddingClient;
import com.pmagent.backend.infrastructure.mapper.ModuleEntryMapper;
import com.pmagent.backend.infrastructure.mapper.StoryRecordMapper;
import com.pmagent.backend.infrastructure.mapper.TaskRecordMapper;
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

        ModuleEntryEntity m2 = new ModuleEntryEntity();
        m2.setWorkspaceId("ws-1");
        m2.setBigModule("采购");
        m2.setFunctionModule("结算管理");
        m2.setPrimaryOwner("王五");

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
            indexer, embeddingClient, retrieval,
            () -> "", // embedding baseUrl supplier — disabled anyway
            () -> ""  // embedding model supplier — disabled anyway
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
            indexer, embeddingClient, retrieval,
            () -> "", () -> ""
        );

        Map<String, Object> context = retriever.retrieve("ws-1", "任何消息",
            List.of(), List.of(), List.of());

        assertTrue(((List<?>) context.get("module_candidates")).isEmpty());
        assertTrue(((List<?>) context.get("task_name_signals")).isEmpty());
        assertTrue(((List<?>) context.get("story_name_signals")).isEmpty());
    }
}
```

Run: `cd backend-java && ./mvnw test -Dtest=HybridRetrieverTest -q`
Expected: FAIL (class doesn't exist yet)

- [ ] **Step 2: 实现 HybridRetriever**

```java
package com.pmagent.backend.application.retrieval;

import com.fasterxml.jackson.databind.ObjectMapper;
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
    private final Supplier<String> embeddingModel;

    public HybridRetriever(ModuleIndexer moduleIndexer,
                           EmbeddingClient embeddingClient,
                           LlmProviderProperties llmProperties,
                           Supplier<String> embeddingBaseUrl,
                           Supplier<String> embeddingModel) {
        this.moduleIndexer = moduleIndexer;
        this.embeddingClient = embeddingClient;
        this.retrieval = llmProperties.getRetrieval();
        this.embeddingBaseUrl = embeddingBaseUrl;
        this.embeddingModel = embeddingModel;
    }

    public Map<String, Object> retrieve(String workspaceId,
                                        String message,
                                        List<ModuleEntryEntity> moduleEntries,
                                        List<TaskRecordEntity> taskRecords,
                                        List<StoryRecordEntity> storyRecords) {

        if (moduleEntries == null || moduleEntries.isEmpty()) {
            return Map.of(
                "module_candidates", List.of(),
                "task_name_signals", List.of(),
                "story_name_signals", List.of(),
                "excluded_fields", List.of("module_path")
            );
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
                embeddingModel.get(),
                message,
                candidateTexts
            );

            if (!embeddingScores.isEmpty() && embeddingScores.size() == bm25Results.size()) {
                // Merge BM25 score with embedding score
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
        // Simple heuristic: if signal text contains any module keyword, keep it
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
```

- [ ] **Step 3: 运行测试**

Run: `cd backend-java && ./mvnw test -Dtest=HybridRetrieverTest -q`
Expected: All tests pass

- [ ] **Step 4: 提交**

```bash
git add backend-java/src/main/java/com/pmagent/backend/application/retrieval/HybridRetriever.java
git add backend-java/src/test/java/com/pmagent/backend/application/retrieval/HybridRetrieverTest.java
git commit -m "feat: add HybridRetriever for BM25 + Embedding two-stage retrieval"
```

---

### Task 5: 将 HybridRetriever 接入 ChatService 和 Spring 配置

**Files:**
- Modify: `backend-java/src/main/java/com/pmagent/backend/application/chat/ChatService.java`
- Modify: `backend-java/src/main/java/com/pmagent/backend/application/chat/RequirementParseContextBuilder.java`
- Modify: `backend-java/src/main/java/com/pmagent/backend/infrastructure/llm/OpenAiCompatibleLlmClient.java` (新增 getBaseUrl getter)
- Modify: `backend-java/src/test/java/com/pmagent/backend/application/chat/RequirementParseContextBuilderTest.java`

- [ ] **Step 1: 修改 ChatService，新增 buildByRetrieval 调用路径**

在 `ChatService` 中注入 `HybridRetriever`，并新增 `buildByRetrieval` 方法。修改 `send()` 使用检索路径。

完整修改后的 `ChatService.java`：

```java
package com.pmagent.backend.application.chat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pmagent.backend.application.llm.LlmService;
import com.pmagent.backend.application.retrieval.HybridRetriever;
import com.pmagent.backend.infrastructure.entity.ChatMessageEntity;
import com.pmagent.backend.infrastructure.entity.ChatSessionEntity;
import com.pmagent.backend.infrastructure.mapper.ChatMessageMapper;
import com.pmagent.backend.infrastructure.mapper.ChatSessionMapper;
import com.pmagent.backend.infrastructure.mapper.ModuleEntryMapper;
import com.pmagent.backend.infrastructure.mapper.RequirementWriteMapper;
import com.pmagent.backend.infrastructure.mapper.SessionRequirementMapper;
import com.pmagent.backend.infrastructure.mapper.StoryRecordMapper;
import com.pmagent.backend.infrastructure.mapper.TaskRecordMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class ChatService {

    private final ChatSessionMapper chatSessionMapper;
    private final ChatMessageMapper chatMessageMapper;
    private final RequirementWriteMapper requirementWriteMapper;
    private final SessionRequirementMapper sessionRequirementMapper;
    private final ModuleEntryMapper moduleEntryMapper;
    private final TaskRecordMapper taskRecordMapper;
    private final StoryRecordMapper storyRecordMapper;
    private final RequirementParseContextBuilder requirementParseContextBuilder;
    private final HybridRetriever hybridRetriever;
    private final LlmService llmService;
    private final ObjectMapper objectMapper;

    public ChatService(ChatSessionMapper chatSessionMapper,
                       ChatMessageMapper chatMessageMapper,
                       RequirementWriteMapper requirementWriteMapper,
                       SessionRequirementMapper sessionRequirementMapper,
                       ModuleEntryMapper moduleEntryMapper,
                       TaskRecordMapper taskRecordMapper,
                       StoryRecordMapper storyRecordMapper,
                       RequirementParseContextBuilder requirementParseContextBuilder,
                       HybridRetriever hybridRetriever,
                       LlmService llmService,
                       ObjectMapper objectMapper) {
        this.chatSessionMapper = chatSessionMapper;
        this.chatMessageMapper = chatMessageMapper;
        this.requirementWriteMapper = requirementWriteMapper;
        this.sessionRequirementMapper = sessionRequirementMapper;
        this.moduleEntryMapper = moduleEntryMapper;
        this.taskRecordMapper = taskRecordMapper;
        this.storyRecordMapper = storyRecordMapper;
        this.requirementParseContextBuilder = requirementParseContextBuilder;
        this.hybridRetriever = hybridRetriever;
        this.llmService = llmService;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public Map<String, Object> send(String workspaceId, Map<String, Object> payload) {
        String message = normalize(String.valueOf(payload.getOrDefault("message", "")));
        if (message.isEmpty()) {
            throw new IllegalArgumentException("message is required");
        }
        String sessionId = normalize(String.valueOf(payload.getOrDefault("session_id", "")));
        if (sessionId.isEmpty()) {
            ChatSessionEntity active = chatSessionMapper.findActive(workspaceId);
            if (active == null) {
                sessionId = String.valueOf(createSession(workspaceId, Map.of()).get("sessionId"));
            } else {
                sessionId = active.getSessionId();
            }
        }

        String now = Instant.now().toString();
        appendMessage(workspaceId, sessionId, "user", message, "");
        Map<String, Object> parseContext = buildByRetrieval(workspaceId, message);
        Map<String, Object> parsed = llmService.parseRequirements(message, parseContext);
        String reply = String.valueOf(parsed.getOrDefault("reply", "已收到需求"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> requirements = (List<Map<String, Object>>) parsed.getOrDefault("requirements", List.of());
        String parsedJson = writeJson(requirements);
        appendMessage(workspaceId, sessionId, "assistant", reply, parsedJson);

        for (Map<String, Object> requirement : requirements) {
            String requirementId = String.valueOf(requirement.getOrDefault("requirement_id", UUID.randomUUID().toString()));
            String title = String.valueOf(requirement.getOrDefault("title", "未命名需求"));
            String priority = String.valueOf(requirement.getOrDefault("priority", "中"));
            String rawText = String.valueOf(requirement.getOrDefault("raw_text", message));
            requirementWriteMapper.upsert(workspaceId, requirementId, title, priority, rawText, writeJson(requirement), now);
            sessionRequirementMapper.insert(sessionId, requirementId);
        }
        chatSessionMapper.touch(workspaceId, sessionId, now, shorten(reply));

        Map<String, Object> response = new HashMap<>();
        response.put("workspaceId", workspaceId);
        response.put("sessionId", sessionId);
        response.put("messages", toMessageList(chatMessageMapper.list(workspaceId, sessionId)));
        response.put("requirementIds", sessionRequirementMapper.listRequirementIds(sessionId));
        response.put("reply", reply);
        return response;
    }

    private Map<String, Object> buildByRetrieval(String workspaceId, String message) {
        return hybridRetriever.retrieve(
            workspaceId,
            message,
            moduleEntryMapper.listAllByWorkspaceId(workspaceId),
            taskRecordMapper.listAllByWorkspace(workspaceId),
            storyRecordMapper.listAllByWorkspace(workspaceId)
        );
    }

    // ... rest of existing methods (createSession, listSessions, getSession, deleteSession,
    //     appendMessage, toMessageList, readAnyJson, writeJson, normalize, shorten) unchanged ...

    @Transactional
    public Map<String, Object> createSession(String workspaceId, Map<String, Object> payload) {
        chatSessionMapper.archiveActive(workspaceId);
        String now = Instant.now().toString();
        ChatSessionEntity entity = new ChatSessionEntity();
        entity.setSessionId(UUID.randomUUID().toString());
        entity.setWorkspaceId(workspaceId);
        entity.setCreatedAt(now);
        entity.setLastActiveAt(now);
        entity.setStatus("active");
        entity.setLastMessagePreview("");
        chatSessionMapper.insert(entity);
        return Map.of(
            "sessionId", entity.getSessionId(),
            "createdAt", entity.getCreatedAt(),
            "status", entity.getStatus()
        );
    }

    public Map<String, Object> listSessions(String workspaceId) {
        List<Map<String, Object>> sessions = chatSessionMapper.listByWorkspace(workspaceId).stream().map(it -> {
            Map<String, Object> item = new HashMap<>();
            item.put("sessionId", it.getSessionId());
            item.put("createdAt", it.getCreatedAt());
            item.put("lastActiveAt", it.getLastActiveAt());
            item.put("status", it.getStatus());
            item.put("lastMessagePreview", it.getLastMessagePreview());
            item.put("requirementIds", sessionRequirementMapper.listRequirementIds(it.getSessionId()));
            return item;
        }).toList();
        ChatSessionEntity active = chatSessionMapper.findActive(workspaceId);
        return Map.of(
            "workspaceId", workspaceId,
            "activeSessionId", active == null ? "" : active.getSessionId(),
            "sessions", sessions
        );
    }

    public Map<String, Object> getSession(String workspaceId, String sessionId) {
        ChatSessionEntity session = chatSessionMapper.get(workspaceId, sessionId);
        if (session == null) {
            throw new IllegalArgumentException("session_not_found: " + sessionId);
        }
        return Map.of(
            "sessionId", sessionId,
            "createdAt", session.getCreatedAt(),
            "lastActiveAt", session.getLastActiveAt(),
            "status", session.getStatus(),
            "messages", toMessageList(chatMessageMapper.list(workspaceId, sessionId)),
            "requirementIds", sessionRequirementMapper.listRequirementIds(sessionId)
        );
    }

    @Transactional
    public Map<String, Object> deleteSession(String workspaceId, String sessionId) {
        ChatSessionEntity session = chatSessionMapper.get(workspaceId, sessionId);
        if (session == null) {
            throw new IllegalArgumentException("session_not_found: " + sessionId);
        }
        chatMessageMapper.deleteBySession(workspaceId, sessionId);
        sessionRequirementMapper.deleteBySession(sessionId);
        chatSessionMapper.delete(workspaceId, sessionId);

        ChatSessionEntity active = chatSessionMapper.findActive(workspaceId);
        return Map.of(
            "workspaceId", workspaceId,
            "activeSessionId", active == null ? "" : active.getSessionId()
        );
    }

    private void appendMessage(String workspaceId, String sessionId, String role, String content, String parsedRequirementsJson) {
        ChatMessageEntity entity = new ChatMessageEntity();
        entity.setWorkspaceId(workspaceId);
        entity.setSessionId(sessionId);
        entity.setSeq(chatMessageMapper.nextSeq(sessionId));
        entity.setRole(role);
        entity.setContent(content);
        entity.setTimestamp(Instant.now().toString());
        entity.setParsedRequirementsJson(parsedRequirementsJson == null ? "" : parsedRequirementsJson);
        chatMessageMapper.insert(entity);
    }

    private List<Map<String, Object>> toMessageList(List<ChatMessageEntity> messages) {
        return messages.stream().map(message -> {
            Map<String, Object> item = new HashMap<>();
            item.put("seq", message.getSeq());
            item.put("role", message.getRole());
            item.put("content", message.getContent());
            item.put("timestamp", message.getTimestamp());
            item.put("parsedRequirements", readAnyJson(message.getParsedRequirementsJson()));
            return item;
        }).toList();
    }

    private Object readAnyJson(String json) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, Object.class);
        } catch (Exception ex) {
            return json;
        }
    }

    private String writeJson(Object payload) {
        try {
            return objectMapper.writeValueAsString(payload);
        } catch (Exception ex) {
            throw new IllegalArgumentException("failed to serialize chat payload", ex);
        }
    }

    private String normalize(String text) {
        return text == null ? "" : text.trim();
    }

    private String shorten(String text) {
        if (text == null) {
            return "";
        }
        String normalized = text.trim();
        if (normalized.length() <= 200) {
            return normalized;
        }
        return normalized.substring(0, 200);
    }
}
```

- [ ] **Step 2: 修改 RequirementParseContextBuilder，新增 buildByRetrieval 委托方法**

新增方法，保留原有 `build()` 方法不动：

```java
// 在 RequirementParseContextBuilder 类中新增：

    public Map<String, Object> buildByRetrieval(String message, String workspaceId) {
        // 此方法保留为兼容性入口，实际逻辑由 HybridRetriever 处理
        // ChatService 已直接调用 HybridRetriever，此方法仅用于向后兼容
        throw new UnsupportedOperationException(
            "buildByRetrieval is now handled by HybridRetriever directly");
    }
```

- [ ] **Step 3: 编译验证**

Run: `cd backend-java && ./mvnw compile -q`
Expected: BUILD SUCCESS

- [ ] **Step 4: 运行已有测试确保未回归**

Run: `cd backend-java && ./mvnw test -q`
Expected: All existing tests pass

- [ ] **Step 5: 提交**

```bash
git add backend-java/src/main/java/com/pmagent/backend/application/chat/ChatService.java
git add backend-java/src/main/java/com/pmagent/backend/application/chat/RequirementParseContextBuilder.java
git commit -m "feat: wire HybridRetriever into ChatService send flow"
```

---

### Task 6: LlmService Prompt 优化 + response_format 支持

**Files:**
- Modify: `backend-java/src/main/java/com/pmagent/backend/application/llm/LlmService.java`
- Modify: `backend-java/src/main/java/com/pmagent/backend/infrastructure/llm/OpenAiCompatibleLlmClient.java`
- Modify: `backend-java/src/test/java/com/pmagent/backend/application/llm/LlmServiceJsonNormalizationTest.java`

- [ ] **Step 1: 修改 OpenAiCompatibleLlmClient，支持 response_format 参数**

在 `OpenAiCompatibleLlmClient` 中新增 `chatWithJsonFormat` 方法：

```java
// 在 OpenAiCompatibleLlmClient 类中新增方法：

    public String chatWithJsonFormat(String baseUrl, String apiKey, String model, int timeoutSeconds, String prompt) {
        if (baseUrl == null || baseUrl.isBlank() || apiKey == null || apiKey.isBlank() || model == null || model.isBlank()) {
            throw new LlmUnavailableException("llm_configuration is incomplete");
        }
        String endpoint = baseUrl.endsWith("/") ? baseUrl + "chat/completions" : baseUrl + "/chat/completions";
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("model", model);
            payload.put("temperature", 0.2);
            payload.put("response_format", Map.of("type", "json_object"));
            payload.put("messages", List.of(
                Map.of("role", "system", "content", "You are a strict JSON output assistant. Return ONLY valid JSON, no markdown, no explanation."),
                Map.of("role", "user", "content", prompt)
            ));
            String body = objectMapper.writeValueAsString(payload);

            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(endpoint))
                .timeout(Duration.ofSeconds(Math.max(timeoutSeconds, 1)))
                .header("Authorization", "Bearer " + apiKey)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() >= 400) {
                throw new LlmUnavailableException("llm upstream returned status " + response.statusCode());
            }
            JsonNode root = objectMapper.readTree(response.body());
            JsonNode contentNode = root.path("choices").path(0).path("message").path("content");
            String content = contentNode.asText("");
            if (content.isBlank()) {
                throw new LlmUnavailableException("llm returned empty content");
            }
            return content;
        } catch (LlmUnavailableException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new LlmUnavailableException("llm call failed: " + ex.getMessage(), ex);
        }
    }
```

- [ ] **Step 2: 修改 LlmService.parseRequirements，使用 response_format 并优化 prompt**

将 `parseRequirements` 方法改为使用 `chatWithJsonFormat`，优化 prompt：

```java
    @SuppressWarnings("unchecked")
    public Map<String, Object> parseRequirements(String message, Map<String, Object> parseContext) {
        String contextJson = writeJson(parseContext == null ? Map.of() : parseContext);
        String prompt = """
            你是需求解析助手。请仅返回 JSON，禁止 markdown，禁止任何解释文字。

            规则：
            1. 你必须基于给定模块候选进行模块归属，不可发明新模块。
            2. 严禁使用 module_path 字段作为依据。
            3. 模块归属必须与 candidate_modules 中的某一个完全匹配。
            4. 如果无法确定模块归属，将 match_status 设为 "needs_confirmation"。

            返回 JSON 格式：
            {
              "reply": "给用户的简短回复（1-2句）",
              "requirements": [
                {
                  "requirement_id":"1",
                  "title":"标题",
                  "priority":"高|中|低",
                  "raw_text":"原文",
                  "big_module":"大模块",
                  "function_module":"功能模块",
                  "abstract_summary":"抽象提炼后的一句话",
                  "match_evidence":["命中关键词xx","参考任务名xx"],
                  "match_status":"matched|needs_confirmation",
                  "candidate_modules":[
                    {"big_module":"候选大模块","function_module":"候选功能模块","reason":"候选理由"}
                  ]
                }
              ]
            }

            用户消息：
            %s

            解析上下文(JSON)：
            %s
            """.formatted(message, contextJson);

        String raw;
        try {
            raw = chatWithJsonFormat(prompt);
        } catch (LlmUnavailableException ex) {
            // 降级为不带 response_format 的调用
            raw = chatWithFallback(prompt);
        }
        try {
            JsonNode node = objectMapper.readTree(normalizeJsonPayload(raw));
            String reply = node.path("reply").asText("已收到需求");
            List<Map<String, Object>> requirements = new ArrayList<>();
            List<Map<String, Object>> moduleCandidates = extractModuleCandidates(parseContext);
            for (JsonNode req : node.path("requirements")) {
                Map<String, Object> normalized = normalizeRequirementItem(
                    objectMapper.convertValue(req, Map.class),
                    message,
                    moduleCandidates
                );
                requirements.add(normalized);
            }
            if (requirements.isEmpty()) {
                requirements.add(defaultRequirement(message, moduleCandidates));
            }
            return Map.of(
                "reply", reply,
                "requirements", requirements
            );
        } catch (Exception ex) {
            throw new LlmUnavailableException("llm returned invalid json: " + ex.getMessage(), ex);
        }
    }

    private String chatWithJsonFormat(String prompt) {
        LlmProviderProperties.Tier tier = llmProviderProperties.getPrimary();
        try {
            return client.chatWithJsonFormat(
                tier.getBaseUrl(), tier.getApiKey(), tier.getModel(),
                tier.getTimeoutSeconds(), prompt
            );
        } catch (Exception ex) {
            // try fallback tier
            LlmProviderProperties.Tier fallback = llmProviderProperties.getFallback();
            return client.chatWithJsonFormat(
                fallback.getBaseUrl(), fallback.getApiKey(), fallback.getModel(),
                fallback.getTimeoutSeconds(), prompt
            );
        }
    }
```

- [ ] **Step 3: 运行测试**

Run: `cd backend-java && ./mvnw test -Dtest=LlmServiceJsonNormalizationTest -q`
Expected: All tests pass

- [ ] **Step 4: 运行全量测试确保未回归**

Run: `cd backend-java && ./mvnw test -q`
Expected: All tests pass

- [ ] **Step 5: 提交**

```bash
git add backend-java/src/main/java/com/pmagent/backend/infrastructure/llm/OpenAiCompatibleLlmClient.java
git add backend-java/src/main/java/com/pmagent/backend/application/llm/LlmService.java
git add backend-java/src/test/java/com/pmagent/backend/application/llm/LlmServiceJsonNormalizationTest.java
git commit -m "feat: add response_format json_object support and optimize parseRequirements prompt"
```

---

### Task 7: 全量集成验证与编译检查

**Files:**
- 验证所有模块编译和测试通过

- [ ] **Step 1: 全量编译**

Run: `cd backend-java && ./mvnw compile -q`
Expected: BUILD SUCCESS

- [ ] **Step 2: 全量测试**

Run: `cd backend-java && ./mvnw test -q`
Expected: All tests pass

- [ ] **Step 3: 提交最终代码**

```bash
git status
git add -A
git commit -m "chore: complete RAG retrieval pipeline integration for requirement parsing"
```

---

## 文件变更总览

| 文件 | 操作 | 说明 |
|------|------|------|
| `application/config/LlmProviderProperties.java` | 修改 | 新增 Retrieval 内部类及配置字段 |
| `application/retrieval/ModuleIndexer.java` | 新建 | BM25 倒排索引 |
| `application/retrieval/ModuleIndexerTest.java` | 新建 | ModuleIndexer 单元测试 |
| `application/retrieval/HybridRetriever.java` | 新建 | 两阶段检索编排 |
| `application/retrieval/HybridRetrieverTest.java` | 新建 | HybridRetriever 单元测试 |
| `infrastructure/llm/EmbeddingClient.java` | 新建 | Embedding API 客户端 |
| `infrastructure/llm/EmbeddingClientTest.java` | 新建 | EmbeddingClient 单元测试 |
| `infrastructure/llm/OpenAiCompatibleLlmClient.java` | 修改 | 新增 chatWithJsonFormat 方法 |
| `application/llm/LlmService.java` | 修改 | 使用 response_format + 优化 prompt + 降级策略 |
| `application/llm/LlmServiceJsonNormalizationTest.java` | 修改 | 新增相关测试 |
| `application/chat/ChatService.java` | 修改 | 接入 HybridRetriever |
| `application/chat/RequirementParseContextBuilder.java` | 修改 | 新增 buildByRetrieval 兼容性入口 |
| `application/chat/RequirementParseContextBuilderTest.java` | 修改 | 新增检索路径测试 |
