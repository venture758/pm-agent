package com.pmagent.backend.api.common;

public record ApiResponse<T>(int code, String message, T data) {

    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(ApiErrorCode.SUCCESS.getCode(), ApiErrorCode.SUCCESS.getDefaultMessage(), data);
    }

    public static <T> ApiResponse<T> failure(ApiErrorCode errorCode, String message) {
        String resolved = (message == null || message.isBlank()) ? errorCode.getDefaultMessage() : message;
        return new ApiResponse<>(errorCode.getCode(), resolved, null);
    }
}
