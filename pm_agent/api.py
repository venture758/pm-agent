from __future__ import annotations

import cgi
import json
import logging
import mimetypes
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote


def _json_default(obj: Any) -> Any:
    """自定义 JSON 序列化默认值，处理 MySQL 返回的 Decimal 等类型。"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def _unquote_utf8(text: str) -> str:
    """WSGI PATH_INFO 以 ISO-8859-1 解码，URL 编码的 UTF-8 字节会变成乱码。
    先 unquote 得到带百分号的原始串，再 encode('iso-8859-1') 还原字节，最后 decode('utf-8')。
    """
    raw = unquote(text)
    return raw.encode("iso-8859-1").decode("utf-8")


from .api_service import WorkspaceService
from .utils import normalize_text

logger = logging.getLogger(__name__)


class ApiApplication:
    def __init__(
        self,
        static_root: str | Path = "frontend/dist",
        database_url: str | None = None,
        dashscope_api_key: str = "",
    ) -> None:
        self.service = WorkspaceService(
            database_url=database_url,
            dashscope_api_key=dashscope_api_key,
        )
        self.static_root = Path(static_root)

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        if method == "OPTIONS":
            return self._send(start_response, 204, b"", "text/plain")
        try:
            if path.startswith("/api/"):
                status, payload = self._dispatch_api(method, path, environ)
                body = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
                return self._send(start_response, status, body, "application/json; charset=utf-8")
            return self._serve_static(path, start_response)
        except ValueError as exc:
            logger.warning("[chat.api] 请求错误 %s", exc)
            body = json.dumps({"error": str(exc)}, ensure_ascii=False, default=_json_default).encode("utf-8")
            return self._send(start_response, 400, body, "application/json; charset=utf-8")
        except Exception as exc:  # pragma: no cover - defensive API boundary
            logger.exception("[chat.api] 内部错误")
            body = json.dumps({"error": f"internal_error: {exc}"}, ensure_ascii=False, default=_json_default).encode("utf-8")
            return self._send(start_response, 500, body, "application/json; charset=utf-8")

    def _dispatch_api(self, method: str, path: str, environ: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        segments = [segment for segment in path.split("/") if segment]
        if segments == ["api", "health"] and method == "GET":
            return 200, {"status": "ok"}
        if len(segments) < 3 or segments[1] != "workspaces":
            raise ValueError("未知 API 路径")
        workspace_id = segments[2]
        if len(segments) == 3 and method == "GET":
            return 200, self.service.get_workspace(workspace_id)
        if len(segments) == 4 and segments[3] == "draft" and method == "PUT":
            return 200, self.service.update_draft(workspace_id, self._read_json_body(environ))
        if len(segments) == 4 and segments[3] == "modules" and method == "GET":
            return 200, self.service.list_module_entries(workspace_id, self._read_query(environ))
        if len(segments) == 4 and segments[3] == "modules" and method == "POST":
            return 200, self.service.create_module_entry(workspace_id, self._read_json_body(environ))
        if len(segments) == 5 and segments[3] == "modules" and method == "PUT":
            return 200, self.service.update_module_entry(workspace_id, _unquote_utf8(segments[4]), self._read_json_body(environ))
        if len(segments) == 5 and segments[3] == "modules" and method == "DELETE":
            return 200, self.service.delete_module_entry(workspace_id, _unquote_utf8(segments[4]))
        if len(segments) == 4 and segments[3] == "members" and method == "GET":
            return 200, self.service.list_managed_members(workspace_id)
        if len(segments) == 4 and segments[3] == "members" and method == "POST":
            return 200, self.service.create_managed_member(workspace_id, self._read_json_body(environ))
        if len(segments) == 5 and segments[3] == "members" and method == "PUT":
            return 200, self.service.update_managed_member(workspace_id, _unquote_utf8(segments[4]), self._read_json_body(environ))
        if len(segments) == 5 and segments[3] == "members" and method == "DELETE":
            return 200, self.service.delete_managed_member(workspace_id, _unquote_utf8(segments[4]))
        if len(segments) == 4 and segments[3] == "recommendations" and method == "POST":
            return 200, self.service.generate_recommendations(workspace_id)
        if len(segments) == 5 and segments[3] == "recommendations" and segments[4] == "batch-delete" and method == "POST":
            payload = self._read_json_body(environ)
            return 200, self.service.batch_delete_recommendations(workspace_id, payload.get("requirement_ids") or [])
        if len(segments) == 5 and segments[3] == "recommendations" and method == "DELETE":
            return 200, self.service.delete_recommendation(workspace_id, _unquote_utf8(segments[4]))
        if len(segments) == 4 and segments[3] == "confirmations" and method == "GET":
            page = int(self._read_query(environ).get("page") or 1)
            page_size = int(self._read_query(environ).get("pageSize") or 20)
            return 200, self.service.list_confirmation_records(workspace_id, page, page_size)
        if len(segments) == 4 and segments[3] == "stories" and method == "GET":
            page = int(self._read_query(environ).get("page") or 1)
            page_size = int(self._read_query(environ).get("pageSize") or 20)
            keyword = normalize_text(self._read_query(environ).get("keyword")) or None
            return 200, self.service.list_stories(workspace_id, page, page_size, keyword=keyword)
        if len(segments) == 4 and segments[3] == "tasks" and method == "GET":
            return 200, self.service.get_tasks(workspace_id, self._read_query(environ))
        if len(segments) == 4 and segments[3] == "confirmations" and method == "POST":
            payload = self._read_json_body(environ)
            return 200, self.service.confirm_assignments(workspace_id, payload.get("actions") or {})
        if len(segments) == 5 and segments[3] == "uploads" and segments[4] == "module-knowledge" and method == "POST":
            _, files = self._read_multipart(environ)
            upload = files.get("file")
            if not upload:
                raise ValueError("缺少模块知识库文件")
            return 200, self.service.upload_module_knowledge(
                workspace_id,
                upload["filename"],
                upload["content"],
            )
        if len(segments) == 5 and segments[3] == "uploads" and segments[4] == "platform-sync" and method == "POST":
            _, files = self._read_multipart(environ)
            story_file = files.get("story_file")
            task_file = files.get("task_file")
            if not story_file or not task_file:
                raise ValueError("缺少 story_file 或 task_file")
            return 200, self.service.sync_platform_files(
                workspace_id,
                (story_file["filename"], story_file["content"]),
                (task_file["filename"], task_file["content"]),
            )
        if len(segments) == 5 and segments[3] == "uploads" and segments[4] == "story-only" and method == "POST":
            _, files = self._read_multipart(environ)
            story_file = files.get("story_file")
            if not story_file:
                raise ValueError("缺少 story_file")
            return 200, self.service.upload_story_file(
                workspace_id,
                (story_file["filename"], story_file["content"]),
            )
        if len(segments) == 5 and segments[3] == "uploads" and segments[4] == "task-only" and method == "POST":
            _, files = self._read_multipart(environ)
            task_file = files.get("task_file")
            if not task_file:
                raise ValueError("缺少 task_file")
            return 200, self.service.upload_task_file(
                workspace_id,
                (task_file["filename"], task_file["content"]),
            )
        if len(segments) == 4 and segments[3] == "monitoring" and method == "GET":
            return 200, self.service.get_monitoring(workspace_id)
        if len(segments) == 4 and segments[3] == "insights" and method == "GET":
            return 200, self.service.get_insights(workspace_id)
        if len(segments) == 5 and segments[3] == "insights" and segments[4] == "history" and method == "GET":
            return 200, self.service.get_insight_history(workspace_id)
        if len(segments) == 4 and segments[3] == "chat" and method == "POST":
            payload = self._read_json_body(environ)
            logger.info("[chat.api] 收到 chat 请求 workspace_id=%s msg_len=%d", workspace_id, len(payload.get("message", "")))
            result = self.service.send_chat_message(workspace_id, payload)
            logger.info("[chat.api] chat 响应完成 workspace_id=%s", workspace_id)
            return 200, result
        if len(segments) == 5 and segments[3] == "chat" and segments[4] == "sessions" and method == "POST":
            payload = self._read_json_body(environ)
            return 200, self.service.create_chat_session(workspace_id, payload)
        if len(segments) == 5 and segments[3] == "chat" and segments[4] == "sessions" and method == "GET":
            return 200, self.service.list_chat_sessions(workspace_id)
        if len(segments) == 6 and segments[3] == "chat" and segments[4] == "sessions" and method == "GET":
            return 200, self.service.get_chat_session_messages(workspace_id, segments[5])
        if len(segments) == 6 and segments[3] == "chat" and segments[4] == "sessions" and method == "DELETE":
            return 200, self.service.delete_chat_session(workspace_id, segments[5])
        raise ValueError("不支持的 API 请求")

    def _read_json_body(self, environ: dict[str, Any]) -> dict[str, Any]:
        content_length = int(environ.get("CONTENT_LENGTH") or 0)
        raw = environ["wsgi.input"].read(content_length) if content_length else b""
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _read_query(self, environ: dict[str, Any]) -> dict[str, Any]:
        raw_query = str(environ.get("QUERY_STRING") or "")
        parsed = parse_qs(raw_query, keep_blank_values=True)
        return {key: values[0] if values else "" for key, values in parsed.items()}

    def _read_multipart(self, environ: dict[str, Any]) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
        form = cgi.FieldStorage(fp=environ["wsgi.input"], environ=environ, keep_blank_values=True)
        fields: dict[str, str] = {}
        files: dict[str, dict[str, Any]] = {}
        for item in form.list or []:
            if item.filename:
                files[item.name] = {
                    "filename": item.filename,
                    "content": item.file.read(),
                }
            else:
                fields[item.name] = item.value
        return fields, files

    def _serve_static(self, path: str, start_response: Callable[..., Any]):
        if self.static_root.joinpath("index.html").exists():
            if path == "/":
                return self._send_file(self.static_root / "index.html", start_response)
            candidate = (self.static_root / path.lstrip("/")).resolve()
            if candidate.exists() and candidate.is_file() and self.static_root.resolve() in candidate.parents:
                return self._send_file(candidate, start_response)
            return self._send_file(self.static_root / "index.html", start_response)
        candidate = (self.static_root / path.lstrip("/")).resolve()
        if self.static_root.exists() and candidate.exists() and candidate.is_file() and self.static_root.resolve() in candidate.parents:
            return self._send_file(candidate, start_response)
        body = b"pm-agent api ready"
        return self._send(start_response, 200, body, "text/plain; charset=utf-8")

    def _send_file(self, path: Path, start_response: Callable[..., Any]):
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return self._send(start_response, 200, path.read_bytes(), content_type)

    def _send(self, start_response: Callable[..., Any], status: int, body: bytes, content_type: str):
        headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Headers", "Content-Type"),
            ("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS"),
        ]
        start_response(f"{status} {self._status_text(status)}", headers)
        return [body]

    def _status_text(self, status: int) -> str:
        return {
            200: "OK",
            204: "No Content",
            400: "Bad Request",
            404: "Not Found",
            500: "Internal Server Error",
        }.get(status, "OK")


def create_api_app(
    static_root: str | Path = "frontend/dist",
    database_url: str | None = None,
    dashscope_api_key: str = "",
) -> ApiApplication:
    return ApiApplication(
        static_root=static_root,
        database_url=database_url,
        dashscope_api_key=dashscope_api_key,
    )
