package com.pmagent.backend.api.common;

public enum ApiErrorCode {
    SUCCESS(0, "ok"),
    BAD_REQUEST(40000, "bad_request"),
    VALIDATION_ERROR(40001, "validation_error"),
    NOT_FOUND(40400, "not_found"),
    LLM_UNAVAILABLE(50301, "llm_unavailable"),
    NOT_IMPLEMENTED(50100, "not_implemented"),
    INTERNAL_ERROR(50000, "internal_error");

    private final int code;
    private final String defaultMessage;

    ApiErrorCode(int code, String defaultMessage) {
        this.code = code;
        this.defaultMessage = defaultMessage;
    }

    public int getCode() {
        return code;
    }

    public String getDefaultMessage() {
        return defaultMessage;
    }
}
