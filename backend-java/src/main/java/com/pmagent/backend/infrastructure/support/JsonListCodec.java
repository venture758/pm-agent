package com.pmagent.backend.infrastructure.support;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.Collections;
import java.util.List;

public final class JsonListCodec {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private JsonListCodec() {
    }

    public static String encode(List<String> values) {
        try {
            return MAPPER.writeValueAsString(values == null ? List.of() : values);
        } catch (Exception ex) {
            throw new IllegalArgumentException("failed to encode list json", ex);
        }
    }

    public static List<String> decode(String json) {
        if (json == null || json.isBlank()) {
            return Collections.emptyList();
        }
        try {
            return MAPPER.readValue(json, new TypeReference<>() {
            });
        } catch (Exception ex) {
            throw new IllegalArgumentException("failed to decode list json", ex);
        }
    }
}
