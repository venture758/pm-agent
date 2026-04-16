const DEFAULT_HEADERS = {
  Accept: "application/json",
};

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
    const message = typeof payload === "string" ? payload : payload.error || "请求失败";
    throw new Error(message);
  }
  return payload;
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
    return request(`/api/workspaces/${workspaceId}`);
  },
  getModules(workspaceId, query = {}) {
    return request(`/api/workspaces/${workspaceId}/modules${buildQuery(query)}`);
  },
  createModule(workspaceId, payload) {
    return request(`/api/workspaces/${workspaceId}/modules`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  updateModule(workspaceId, moduleKey, payload) {
    return request(`/api/workspaces/${workspaceId}/modules/${encodeURIComponent(moduleKey)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
  deleteModule(workspaceId, moduleKey) {
    return request(`/api/workspaces/${workspaceId}/modules/${encodeURIComponent(moduleKey)}`, {
      method: "DELETE",
    });
  },
  getMembers(workspaceId) {
    return request(`/api/workspaces/${workspaceId}/members`);
  },
  createMember(workspaceId, payload) {
    return request(`/api/workspaces/${workspaceId}/members`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  updateMember(workspaceId, memberName, payload) {
    return request(`/api/workspaces/${workspaceId}/members/${encodeURIComponent(memberName)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
  deleteMember(workspaceId, memberName) {
    return request(`/api/workspaces/${workspaceId}/members/${encodeURIComponent(memberName)}`, {
      method: "DELETE",
    });
  },
  saveDraft(workspaceId, payload) {
    return request(`/api/workspaces/${workspaceId}/draft`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
  generateRecommendations(workspaceId) {
    return request(`/api/workspaces/${workspaceId}/recommendations`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  deleteRecommendation(workspaceId, requirementId) {
    return request(`/api/workspaces/${workspaceId}/recommendations/${encodeURIComponent(requirementId)}`, {
      method: "DELETE",
    });
  },
  batchDeleteRecommendations(workspaceId, requirementIds = []) {
    return request(`/api/workspaces/${workspaceId}/recommendations/batch-delete`, {
      method: "POST",
      body: JSON.stringify({ requirement_ids: requirementIds }),
    });
  },
  confirmAssignments(workspaceId, actions) {
    return request(`/api/workspaces/${workspaceId}/confirmations`, {
      method: "POST",
      body: JSON.stringify({ actions }),
    });
  },
  listConfirmationRecords(workspaceId, page = 1, pageSize = 20) {
    return request(`/api/workspaces/${workspaceId}/confirmations${buildQuery({ page, pageSize })}`);
  },
  getKnowledgeUpdateModuleDiffs(workspaceId, sessionId, requirementId) {
    return request(
      `/api/workspaces/${workspaceId}/confirmations/${encodeURIComponent(sessionId)}/requirements/${encodeURIComponent(requirementId)}/knowledge-update-modules`,
    );
  },
  listStories(workspaceId, page = 1, pageSize = 20, keyword = null) {
    return request(`/api/workspaces/${workspaceId}/stories${buildQuery({ page, pageSize, keyword })}`);
  },
  uploadModuleKnowledge(workspaceId, file) {
    const formData = new FormData();
    formData.append("file", file);
    return request(`/api/workspaces/${workspaceId}/uploads/module-knowledge`, {
      method: "POST",
      body: formData,
    });
  },
  syncPlatformExports(workspaceId, storyFile, taskFile) {
    const formData = new FormData();
    formData.append("story_file", storyFile);
    formData.append("task_file", taskFile);
    return request(`/api/workspaces/${workspaceId}/uploads/platform-sync`, {
      method: "POST",
      body: formData,
    });
  },
  uploadStoryOnly(workspaceId, storyFile) {
    const formData = new FormData();
    formData.append("story_file", storyFile);
    return request(`/api/workspaces/${workspaceId}/uploads/story-only`, {
      method: "POST",
      body: formData,
    });
  },
  uploadTaskOnly(workspaceId, taskFile) {
    const formData = new FormData();
    formData.append("task_file", taskFile);
    return request(`/api/workspaces/${workspaceId}/uploads/task-only`, {
      method: "POST",
      body: formData,
    });
  },
  getTasks(workspaceId, query = {}) {
    return request(`/api/workspaces/${workspaceId}/tasks${buildQuery(query)}`);
  },
  getMonitoring(workspaceId) {
    return request(`/api/workspaces/${workspaceId}/monitoring`);
  },
  getInsights(workspaceId) {
    return request(`/api/workspaces/${workspaceId}/insights`);
  },
  getInsightHistory(workspaceId) {
    return request(`/api/workspaces/${workspaceId}/insights/history`);
  },
  sendChatMessage(workspaceId, message, sessionId = null) {
    const body = { message };
    if (sessionId) {
      body.session_id = sessionId;
    }
    return request(`/api/workspaces/${workspaceId}/chat`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  createChatSession(workspaceId, payload = {}) {
    return request(`/api/workspaces/${workspaceId}/chat/sessions`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  listChatSessions(workspaceId) {
    return request(`/api/workspaces/${workspaceId}/chat/sessions`);
  },
  getChatSession(workspaceId, sessionId) {
    return request(`/api/workspaces/${workspaceId}/chat/sessions/${sessionId}`);
  },
  deleteChatSession(workspaceId, sessionId) {
    return request(`/api/workspaces/${workspaceId}/chat/sessions/${sessionId}`, { method: "DELETE" });
  },
};
