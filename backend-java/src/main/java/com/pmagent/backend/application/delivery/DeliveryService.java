package com.pmagent.backend.application.delivery;

import com.pmagent.backend.api.common.PageResult;
import com.pmagent.backend.infrastructure.entity.ModuleEntryEntity;
import com.pmagent.backend.infrastructure.entity.StoryRecordEntity;
import com.pmagent.backend.infrastructure.entity.TaskRecordEntity;
import com.pmagent.backend.infrastructure.mapper.ModuleEntryMapper;
import com.pmagent.backend.infrastructure.mapper.StoryRecordMapper;
import com.pmagent.backend.infrastructure.mapper.TaskRecordMapper;
import com.pmagent.backend.infrastructure.support.JsonListCodec;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.DataFormatter;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

@Service
public class DeliveryService {

    private static final DataFormatter FORMATTER = new DataFormatter(Locale.CHINA);

    private static final String STORY_CODE = "用户故事编码";
    private static final String STORY_NAME = "用户故事名称";
    private static final String STORY_STATUS = "状态";
    private static final String STORY_OWNER = "负责人";
    private static final String STORY_TESTER = "测试人员名称";
    private static final String STORY_PRIORITY = "优先级";
    private static final String STORY_URL = "详细说明（URL）";
    private static final String STORY_PROJECT = "所属项目";
    private static final String STORY_DEVELOPER = "开发人员名称";

    private static final String TASK_CODE = "任务编号";
    private static final String TASK_RELATED_STORY = "关联用户故事";
    private static final String TASK_NAME = "任务名称";
    private static final String TASK_TYPE = "任务类型";
    private static final String TASK_OWNER = "负责人";
    private static final String TASK_STATUS = "状态";
    private static final String TASK_EST_START = "预计开始时间";
    private static final String TASK_EST_END = "预计结束时间";
    private static final String TASK_PLAN_DAYS = "计划人天";
    private static final String TASK_ACTUAL_DAYS = "实际人天";
    private static final String TASK_DEFECT = "缺陷总数";
    private static final String TASK_PROJECT = "所属项目";

    private static final String MODULE_BIG = "大模块";
    private static final String MODULE_FUNCTION = "功能模块";
    private static final String MODULE_OWNER = "主要负责人";
    private static final String MODULE_BACKUP = "B角";
    private static final String MODULE_FAMILIAR = "熟悉成员";
    private static final String MODULE_AWARE = "了解成员";
    private static final String MODULE_UNFAMILIAR = "不了解成员";

    private final StoryRecordMapper storyRecordMapper;
    private final TaskRecordMapper taskRecordMapper;
    private final ModuleEntryMapper moduleEntryMapper;

    public DeliveryService(StoryRecordMapper storyRecordMapper,
                           TaskRecordMapper taskRecordMapper,
                           ModuleEntryMapper moduleEntryMapper) {
        this.storyRecordMapper = storyRecordMapper;
        this.taskRecordMapper = taskRecordMapper;
        this.moduleEntryMapper = moduleEntryMapper;
    }

    public PageResult<Map<String, Object>> listStories(String workspaceId, int page, int pageSize, String keyword) {
        int validatedPage = Math.max(page, 1);
        int validatedPageSize = Math.max(pageSize, 1);
        int offset = (validatedPage - 1) * validatedPageSize;
        long total = storyRecordMapper.countByWorkspace(workspaceId, normalize(keyword));
        List<Map<String, Object>> items = storyRecordMapper.listByWorkspace(workspaceId, normalize(keyword), offset, validatedPageSize)
            .stream()
            .map(this::toStoryResponse)
            .toList();
        return new PageResult<>(validatedPage, validatedPageSize, total, items);
    }

    public PageResult<Map<String, Object>> listTasks(String workspaceId, int page, int pageSize, String owner, String status, String projectName) {
        int validatedPage = Math.max(page, 1);
        int validatedPageSize = Math.max(pageSize, 1);
        int offset = (validatedPage - 1) * validatedPageSize;
        long total = taskRecordMapper.countByWorkspace(workspaceId, normalize(owner), normalize(status), normalize(projectName));
        List<Map<String, Object>> items = taskRecordMapper
            .listByWorkspace(workspaceId, normalize(owner), normalize(status), normalize(projectName), offset, validatedPageSize)
            .stream()
            .map(this::toTaskResponse)
            .toList();
        return new PageResult<>(validatedPage, validatedPageSize, total, items);
    }

    public Map<String, Object> importStories(String workspaceId, MultipartFile file) {
        return importWorkbook(workspaceId, file, true);
    }

    public Map<String, Object> importTasks(String workspaceId, MultipartFile file) {
        return importWorkbook(workspaceId, file, false);
    }

    public Map<String, Object> syncPlatform(String workspaceId, MultipartFile storyFile, MultipartFile taskFile) {
        Map<String, Object> storyResult = importStories(workspaceId, storyFile);
        Map<String, Object> taskResult = importTasks(workspaceId, taskFile);
        return Map.of(
            "workspaceId", workspaceId,
            "storyResult", storyResult,
            "taskResult", taskResult
        );
    }

    public Map<String, Object> importModuleKnowledge(String workspaceId, MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("file is required");
        }
        int totalRows = 0;
        int successRows = 0;
        List<Map<String, Object>> errors = new ArrayList<>();
        String now = Instant.now().toString();
        try (InputStream inputStream = file.getInputStream();
             Workbook workbook = new XSSFWorkbook(inputStream)) {
            Sheet sheet = workbook.getSheetAt(0);
            if (sheet == null) {
                throw new IllegalArgumentException("excel sheet is empty");
            }
            Map<String, Integer> headerIndex = buildHeaderIndex(sheet.getRow(0));
            if (!headerIndex.containsKey(MODULE_BIG) || !headerIndex.containsKey(MODULE_FUNCTION) || !headerIndex.containsKey(MODULE_OWNER)) {
                throw new IllegalArgumentException("missing required header: 大模块/功能模块/主要负责人");
            }

            for (int i = 1; i <= sheet.getLastRowNum(); i++) {
                Row row = sheet.getRow(i);
                if (row == null || isBlankRow(row)) {
                    continue;
                }
                totalRows++;
                try {
                    ModuleEntryEntity entry = buildModuleEntryEntity(workspaceId, row, headerIndex, now);
                    if (entry == null) {
                        errors.add(Map.of("row", i + 1, "reason", "缺少大模块或功能模块"));
                        continue;
                    }
                    moduleEntryMapper.upsert(entry);
                    successRows++;
                } catch (Exception ex) {
                    errors.add(Map.of("row", i + 1, "reason", ex.getMessage()));
                }
            }
        } catch (Exception ex) {
            throw new IllegalArgumentException("failed_to_parse_module_excel: " + ex.getMessage(), ex);
        }

        return Map.of(
            "workspaceId", workspaceId,
            "totalRows", totalRows,
            "successRows", successRows,
            "failedRows", totalRows - successRows,
            "errors", errors,
            "importedCount", successRows
        );
    }

    private Map<String, Object> importWorkbook(String workspaceId, MultipartFile file, boolean isStory) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("file is required");
        }
        String now = Instant.now().toString();
        List<Map<String, Object>> errors = new ArrayList<>();
        int totalRows = 0;
        int successRows = 0;
        try (InputStream inputStream = file.getInputStream();
             Workbook workbook = new XSSFWorkbook(inputStream)) {
            Sheet sheet = workbook.getSheetAt(0);
            if (sheet == null) {
                throw new IllegalArgumentException("excel sheet is empty");
            }
            Map<String, Integer> headerIndex = buildHeaderIndex(sheet.getRow(0));
            if (isStory && !headerIndex.containsKey(STORY_CODE)) {
                throw new IllegalArgumentException("missing required header: 用户故事编码");
            }
            if (!isStory && !headerIndex.containsKey(TASK_CODE)) {
                throw new IllegalArgumentException("missing required header: 任务编号");
            }

            for (int i = 1; i <= sheet.getLastRowNum(); i++) {
                Row row = sheet.getRow(i);
                if (row == null) {
                    continue;
                }
                if ("合计".equals(normalize(readCell(row, 0)))) {
                    break;
                }
                if (isBlankRow(row)) {
                    continue;
                }
                totalRows++;
                try {
                    if (isStory) {
                        StoryRecordEntity entity = buildStoryEntity(workspaceId, row, headerIndex, now);
                        if (entity == null) {
                            errors.add(Map.of("row", i + 1, "reason", "缺少用户故事编码"));
                            continue;
                        }
                        storyRecordMapper.upsert(entity);
                    } else {
                        TaskRecordEntity entity = buildTaskEntity(workspaceId, row, headerIndex, now);
                        if (entity == null) {
                            errors.add(Map.of("row", i + 1, "reason", "缺少任务编号"));
                            continue;
                        }
                        taskRecordMapper.upsert(entity);
                    }
                    successRows++;
                } catch (Exception ex) {
                    errors.add(Map.of("row", i + 1, "reason", ex.getMessage()));
                }
            }
        } catch (Exception ex) {
            throw new IllegalArgumentException("failed_to_parse_excel: " + ex.getMessage(), ex);
        }

        return Map.of(
            "workspaceId", workspaceId,
            "totalRows", totalRows,
            "successRows", successRows,
            "failedRows", totalRows - successRows,
            "errors", errors
        );
    }

    private StoryRecordEntity buildStoryEntity(String workspaceId, Row row, Map<String, Integer> headerIndex, String now) {
        String code = normalize(readCell(row, headerIndex.get(STORY_CODE)));
        if (code.isEmpty()) {
            return null;
        }
        StoryRecordEntity entity = new StoryRecordEntity();
        entity.setWorkspaceId(workspaceId);
        entity.setUserStoryCode(code);
        entity.setUserStoryName(normalize(readCell(row, headerIndex.get(STORY_NAME))));
        entity.setStatus(normalize(readCell(row, headerIndex.get(STORY_STATUS))));
        entity.setOwnerNames(normalize(readCell(row, headerIndex.get(STORY_OWNER))));
        entity.setTesterNames(normalize(readCell(row, headerIndex.get(STORY_TESTER))));
        entity.setPriority(normalize(readCell(row, headerIndex.get(STORY_PRIORITY))));
        entity.setDetailUrl(normalize(readCell(row, headerIndex.get(STORY_URL))));
        entity.setProjectName(normalize(readCell(row, headerIndex.get(STORY_PROJECT))));
        entity.setDeveloperNames(normalize(readCell(row, headerIndex.get(STORY_DEVELOPER))));
        entity.setImportedAt(now);
        entity.setUpdatedAt(now);
        return entity;
    }

    private TaskRecordEntity buildTaskEntity(String workspaceId, Row row, Map<String, Integer> headerIndex, String now) {
        String code = normalize(readCell(row, headerIndex.get(TASK_CODE)));
        if (code.isEmpty()) {
            return null;
        }
        TaskRecordEntity entity = new TaskRecordEntity();
        entity.setWorkspaceId(workspaceId);
        entity.setTaskCode(code);
        entity.setRelatedStory(normalize(readCell(row, headerIndex.get(TASK_RELATED_STORY))));
        entity.setName(normalize(readCell(row, headerIndex.get(TASK_NAME))));
        entity.setTaskType(normalize(readCell(row, headerIndex.get(TASK_TYPE))));
        entity.setOwner(normalize(readCell(row, headerIndex.get(TASK_OWNER))));
        entity.setStatus(normalize(readCell(row, headerIndex.get(TASK_STATUS))));
        entity.setEstimatedStart(normalize(readCell(row, headerIndex.get(TASK_EST_START))));
        entity.setEstimatedEnd(normalize(readCell(row, headerIndex.get(TASK_EST_END))));
        entity.setPlannedPersonDays(parseDecimal(readCell(row, headerIndex.get(TASK_PLAN_DAYS))));
        entity.setActualPersonDays(parseDecimal(readCell(row, headerIndex.get(TASK_ACTUAL_DAYS))));
        entity.setDefectCount(parseDecimal(readCell(row, headerIndex.get(TASK_DEFECT))));
        entity.setProjectName(normalize(readCell(row, headerIndex.get(TASK_PROJECT))));
        entity.setImportedAt(now);
        entity.setUpdatedAt(now);
        return entity;
    }

    private ModuleEntryEntity buildModuleEntryEntity(String workspaceId, Row row, Map<String, Integer> headerIndex, String now) {
        String bigModule = normalize(readCell(row, headerIndex.get(MODULE_BIG)));
        String functionModule = normalize(readCell(row, headerIndex.get(MODULE_FUNCTION)));
        if (bigModule.isEmpty() || functionModule.isEmpty()) {
            return null;
        }
        ModuleEntryEntity entity = new ModuleEntryEntity();
        entity.setWorkspaceId(workspaceId);
        entity.setBigModule(bigModule);
        entity.setFunctionModule(functionModule);
        entity.setModuleKey(bigModule + "::" + functionModule);
        entity.setPrimaryOwner(normalize(readCell(row, headerIndex.get(MODULE_OWNER))));
        entity.setBackupOwnersJson(JsonListCodec.encode(splitNames(readCell(row, headerIndex.get(MODULE_BACKUP)))));
        entity.setFamiliarMembersJson(JsonListCodec.encode(splitNames(readCell(row, headerIndex.get(MODULE_FAMILIAR)))));
        entity.setAwareMembersJson(JsonListCodec.encode(splitNames(readCell(row, headerIndex.get(MODULE_AWARE)))));
        entity.setUnfamiliarMembersJson(JsonListCodec.encode(splitNames(readCell(row, headerIndex.get(MODULE_UNFAMILIAR)))));
        entity.setUpdatedAt(now);
        return entity;
    }

    private Map<String, Integer> buildHeaderIndex(Row headerRow) {
        Map<String, Integer> result = new HashMap<>();
        if (headerRow == null) {
            return result;
        }
        for (Cell cell : headerRow) {
            String text = normalize(FORMATTER.formatCellValue(cell));
            if (!text.isEmpty()) {
                result.put(text, cell.getColumnIndex());
            }
        }
        return result;
    }

    private boolean isBlankRow(Row row) {
        for (Cell cell : row) {
            if (!normalize(FORMATTER.formatCellValue(cell)).isEmpty()) {
                return false;
            }
        }
        return true;
    }

    private String readCell(Row row, Integer index) {
        if (row == null || index == null) {
            return "";
        }
        Cell cell = row.getCell(index);
        return cell == null ? "" : FORMATTER.formatCellValue(cell);
    }

    private String readCell(Row row, int index) {
        return readCell(row, Integer.valueOf(index));
    }

    private BigDecimal parseDecimal(String text) {
        String value = normalize(text);
        if (value.isEmpty()) {
            return null;
        }
        try {
            return new BigDecimal(value);
        } catch (Exception ex) {
            return null;
        }
    }

    private List<String> splitNames(String text) {
        String normalized = normalize(text);
        if (normalized.isEmpty()) {
            return List.of();
        }
        return java.util.Arrays.stream(normalized.split("[\\n,，;；、/]+"))
            .map(String::trim)
            .filter(it -> !it.isEmpty())
            .distinct()
            .toList();
    }

    private String normalize(String text) {
        return text == null ? "" : text.trim();
    }

    private Map<String, Object> toStoryResponse(StoryRecordEntity entity) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("userStoryCode", entity.getUserStoryCode());
        payload.put("userStoryName", entity.getUserStoryName());
        payload.put("status", entity.getStatus());
        payload.put("ownerNames", entity.getOwnerNames());
        payload.put("testerNames", entity.getTesterNames());
        payload.put("priority", entity.getPriority());
        payload.put("detailUrl", entity.getDetailUrl());
        payload.put("projectName", entity.getProjectName());
        payload.put("developerNames", entity.getDeveloperNames());
        payload.put("updatedAt", entity.getUpdatedAt());
        return payload;
    }

    private Map<String, Object> toTaskResponse(TaskRecordEntity entity) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("taskCode", entity.getTaskCode());
        payload.put("relatedStory", entity.getRelatedStory());
        payload.put("name", entity.getName());
        payload.put("taskType", entity.getTaskType());
        payload.put("owner", entity.getOwner());
        payload.put("status", entity.getStatus());
        payload.put("estimatedStart", entity.getEstimatedStart());
        payload.put("estimatedEnd", entity.getEstimatedEnd());
        payload.put("plannedPersonDays", entity.getPlannedPersonDays());
        payload.put("actualPersonDays", entity.getActualPersonDays());
        payload.put("defectCount", entity.getDefectCount());
        payload.put("projectName", entity.getProjectName());
        payload.put("updatedAt", entity.getUpdatedAt());
        return payload;
    }
}
