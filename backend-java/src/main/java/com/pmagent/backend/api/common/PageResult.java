package com.pmagent.backend.api.common;

import java.util.List;

public record PageResult<T>(int page, int pageSize, long total, List<T> items) {
}
