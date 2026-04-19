package com.pmagent.backend.application.monitoring;

import com.pmagent.backend.infrastructure.entity.ManagedMemberEntity;
import com.pmagent.backend.infrastructure.entity.TaskRecordEntity;
import com.pmagent.backend.infrastructure.mapper.ManagedMemberMapper;
import com.pmagent.backend.infrastructure.mapper.TaskRecordMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class MonitoringService {

    private final TaskRecordMapper taskRecordMapper;
    private final ManagedMemberMapper managedMemberMapper;

    public MonitoringService(TaskRecordMapper taskRecordMapper, ManagedMemberMapper managedMemberMapper) {
        this.taskRecordMapper = taskRecordMapper;
        this.managedMemberMapper = managedMemberMapper;
    }

    public Map<String, Object> getMonitoring(String workspaceId) {
        List<Map<String, Object>> alerts = new ArrayList<>();
        LocalDate today = LocalDate.now();
        for (TaskRecordEntity task : taskRecordMapper.listAllByWorkspace(workspaceId)) {
            String status = normalize(task.getStatus());
            if ("已完成".equals(status) || "完成".equals(status) || "closed".equalsIgnoreCase(status)) {
                continue;
            }
            LocalDate endDate = tryParseDate(task.getEstimatedEnd());
            if (endDate != null && endDate.isBefore(today)) {
                alerts.add(Map.of(
                    "type", "deadline_overdue",
                    "taskCode", task.getTaskCode(),
                    "owner", normalize(task.getOwner()),
                    "estimatedEnd", task.getEstimatedEnd(),
                    "severity", "high",
                    "message", "任务预计结束时间已逾期"
                ));
            }
        }

        for (ManagedMemberEntity member : managedMemberMapper.listByWorkspaceId(workspaceId)) {
            double workload = member.getWorkload() == null ? 0.0 : member.getWorkload().doubleValue();
            if (workload >= 0.9D) {
                alerts.add(Map.of(
                    "type", "member_overload",
                    "memberName", member.getMemberName(),
                    "workload", workload,
                    "severity", workload >= 1.0D ? "high" : "medium",
                    "message", "成员负载过高"
                ));
            }
        }

        Map<String, Object> summary = new HashMap<>();
        alerts.sort(Comparator
            .comparing((Map<String, Object> alert) -> String.valueOf(alert.getOrDefault("severity", "")))
            .thenComparing(alert -> String.valueOf(alert.getOrDefault("type", "")))
            .thenComparing(alert -> String.valueOf(alert.getOrDefault("taskCode", "")))
            .thenComparing(alert -> String.valueOf(alert.getOrDefault("memberName", ""))));
        summary.put("workspaceId", workspaceId);
        summary.put("alertCount", alerts.size());
        summary.put("highSeverityCount", alerts.stream().filter(it -> "high".equals(it.get("severity"))).count());
        summary.put("alerts", alerts);
        return summary;
    }

    private String normalize(String text) {
        return text == null ? "" : text.trim();
    }

    private LocalDate tryParseDate(String text) {
        if (text == null || text.isBlank()) {
            return null;
        }
        String normalized = text.trim();
        try {
            if (normalized.length() >= 10) {
                return LocalDate.parse(normalized.substring(0, 10));
            }
            return LocalDate.parse(normalized);
        } catch (Exception ignore) {
            return null;
        }
    }
}
