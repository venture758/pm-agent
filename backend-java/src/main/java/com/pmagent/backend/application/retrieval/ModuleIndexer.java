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
