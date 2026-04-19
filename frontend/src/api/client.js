const DEFAULT_HEADERS = {
  Accept: "application/json",
};
const API_PREFIX = "/api/v2";

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function toSnakeCaseKey(value) {
  return value.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();
}

function toSnakeCaseDeep(value) {
  if (Array.isArray(value)) {
    return value.map((item) => toSnakeCaseDeep(item));
  }
  if (!isPlainObject(value)) {
    return value;
  }
  const result = {};
  Object.entries(value).forEach(([key, item]) => {
    result[toSnakeCaseKey(key)] = toSnakeCaseDeep(item);
  });
  return result;
}

function splitNames(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item || "").trim()).filter(Boolean);
  }
  return String(value || "")
    .split(/[\n,，;；、/]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeMemberPayload(payload = {}) {
  return {
    name: payload.name || "",
    role: payload.role || "developer",
    skills: splitNames(payload.skills),
    experienceLevel: payload.experience_level || payload.experience || "中",
    workload: Number(payload.workload ?? 0),
    capacity: Number(payload.capacity ?? 1),
    constraints: splitNames(payload.constraints),
  };
}

function normalizeModulePayload(payload = {}) {
  return {
    bigModule: payload.big_module || payload.bigModule || "",
    functionModule: payload.function_module || payload.functionModule || "",
    primaryOwner: payload.primary_owner || payload.primaryOwner || "",
    backupOwners: splitNames(payload.backup_owners || payload.backupOwners),
    familiarMembers: splitNames(payload.familiar_members || payload.familiarMembers),
    awareMembers: splitNames(payload.aware_members || payload.awareMembers),
    unfamiliarMembers: splitNames(payload.unfamiliar_members || payload.unfamiliarMembers),
  };
}

function normalizeModuleQuery(query = {}) {
  return {
    page: query.page,
    pageSize: query.page_size ?? query.pageSize,
    bigModule: query.big_module ?? query.bigModule,
    functionModule: query.function_module ?? query.functionModule,
    primaryOwner: query.primary_owner ?? query.primaryOwner,
  };
}

function buildQuery(params = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined) {
      return;
    }
    const text = String(value).trim();
    if (!text) {
      return;
    }
    searchParams.set(key, text);
  });
  const encoded = searchParams.toString();
  return encoded ? `?${encoded}` : "";
}

async function handleResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    const message = typeof payload === "string" ? payload : payload.message || payload.error || "请求失败";
    throw new Error(message);
  }
  if (typeof payload === "object" && payload !== null && "code" in payload && "data" in payload) {
    if (payload.code !== 0) {
      throw new Error(payload.message || "请求失败");
    }
    return toSnakeCaseDeep(payload.data);
  }
  return toSnakeCaseDeep(payload);
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...DEFAULT_HEADERS,
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
  });
  return handleResponse(response);
}

export const apiClient = {
  getWorkspace(workspaceId) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}`);
  },
  getModules(workspaceId, query = {}) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/modules${buildQuery(normalizeModuleQuery(query))}`);
  },
  createModule(workspaceId, payload) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/modules`, {
      method: "POST",
      body: JSON.stringify(normalizeModulePayload(payload)),
    });
  },
  updateModule(workspaceId, moduleKey, payload) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/modules/${encodeURIComponent(moduleKey)}`, {
      method: "PUT",
      body: JSON.stringify(normalizeModulePayload(payload)),
    });
  },
  deleteModule(workspaceId, moduleKey) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/modules/${encodeURIComponent(moduleKey)}`, {
      method: "DELETE",
    });
  },
  getMembers(workspaceId) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/members`);
  },
  createMember(workspaceId, payload) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/members`, {
      method: "POST",
      body: JSON.stringify(normalizeMemberPayload(payload)),
    });
  },
  updateMember(workspaceId, memberName, payload) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/members/${encodeURIComponent(memberName)}`, {
      method: "PUT",
      body: JSON.stringify(normalizeMemberPayload(payload)),
    });
  },
  deleteMember(workspaceId, memberName) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/members/${encodeURIComponent(memberName)}`, {
      method: "DELETE",
    });
  },
  saveDraft(workspaceId, payload) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/draft`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
  generateRecommendations(workspaceId) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/recommendations`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  deleteRecommendation(workspaceId, requirementId) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/recommendations/${encodeURIComponent(requirementId)}`, {
      method: "DELETE",
    });
  },
  batchDeleteRecommendations(workspaceId, requirementIds = []) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/recommendations/batch-delete`, {
      method: "POST",
      body: JSON.stringify({ requirement_ids: requirementIds }),
    });
  },
  confirmAssignments(workspaceId, actions) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/confirmations`, {
      method: "POST",
      body: JSON.stringify({ actions }),
    });
  },
  listConfirmationRecords(workspaceId, page = 1, pageSize = 20) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/confirmations${buildQuery({ page, pageSize })}`);
  },
  getKnowledgeUpdateModuleDiffs(workspaceId, sessionId, requirementId) {
    return request(
      `${API_PREFIX}/workspaces/${workspaceId}/confirmations/${encodeURIComponent(sessionId)}/requirements/${encodeURIComponent(requirementId)}/knowledge-update-modules`,
    );
  },
  listStories(workspaceId, page = 1, pageSize = 20, keyword = null) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/stories${buildQuery({ page, pageSize, keyword })}`);
  },
  uploadModuleKnowledge(workspaceId, file) {
    const formData = new FormData();
    formData.append("file", file);
    return request(`${API_PREFIX}/workspaces/${workspaceId}/uploads/module-knowledge`, {
      method: "POST",
      body: formData,
    });
  },
  syncPlatformExports(workspaceId, storyFile, taskFile) {
    const formData = new FormData();
    formData.append("story_file", storyFile);
    formData.append("task_file", taskFile);
    return request(`${API_PREFIX}/workspaces/${workspaceId}/uploads/platform-sync`, {
      method: "POST",
      body: formData,
    });
  },
  uploadStoryOnly(workspaceId, storyFile) {
    const formData = new FormData();
    formData.append("story_file", storyFile);
    return request(`${API_PREFIX}/workspaces/${workspaceId}/uploads/story-only`, {
      method: "POST",
      body: formData,
    });
  },
  uploadTaskOnly(workspaceId, taskFile) {
    const formData = new FormData();
    formData.append("task_file", taskFile);
    return request(`${API_PREFIX}/workspaces/${workspaceId}/uploads/task-only`, {
      method: "POST",
      body: formData,
    });
  },
  getTasks(workspaceId, query = {}) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/tasks${buildQuery(query)}`);
  },
  getMonitoring(workspaceId) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/monitoring`);
  },
  getInsights(workspaceId) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/insights`);
  },
  getInsightHistory(workspaceId) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/insights/history`);
  },
  sendChatMessage(workspaceId, message, sessionId = null) {
    const body = { message };
    if (sessionId) {
      body.session_id = sessionId;
    }
    return request(`${API_PREFIX}/workspaces/${workspaceId}/chat`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  createChatSession(workspaceId, payload = {}) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/chat/sessions`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  listChatSessions(workspaceId) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/chat/sessions`);
  },
  getChatSession(workspaceId, sessionId) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/chat/sessions/${encodeURIComponent(sessionId)}`);
  },
  deleteChatSession(workspaceId, sessionId) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/chat/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
  },

  // Pipeline API
  startPipeline(workspaceId, message = "") {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/pipeline/start`, {
      method: "POST",
      body: JSON.stringify({ message }),
    });
  },
  getPipelineState(workspaceId) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/pipeline/state`);
  },
  confirmPipelineStep(workspaceId, action, options = {}) {
    return request(`${API_PREFIX}/workspaces/${workspaceId}/pipeline/confirm`, {
      method: "POST",
      body: JSON.stringify({
        action,
        modifications: options.modifications,
        feedback: options.feedback,
      }),
    });
  },
};
