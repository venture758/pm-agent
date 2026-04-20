import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";

import ChatMessageBubble from "../ChatMessageBubble.vue";

describe("ChatMessageBubble", () => {
  it("renders module attribution, abstract summary and fallback candidates", () => {
    const wrapper = mount(ChatMessageBubble, {
      props: {
        isUser: false,
        message: {
          role: "assistant",
          content: "已解析需求",
          parsed_requirements: [
            {
              requirement_id: "REQ-1",
              title: "发票接口改造",
              priority: "高",
              big_module: "税务",
              function_module: "发票接口",
              abstract_summary: "统一发票接口协议并补齐校验逻辑",
              match_status: "needs_confirmation",
              match_evidence: ["命中关键词: 发票", "参考任务: 发票接口重构"],
              candidate_modules: [
                {
                  big_module: "税务",
                  function_module: "发票接口",
                  reason: "历史任务名称相似",
                },
              ],
            },
          ],
        },
      },
    });

    const text = wrapper.text();
    expect(text).toContain("模块: 税务 / 发票接口");
    expect(text).toContain("统一发票接口协议并补齐校验逻辑");
    expect(text).toContain("待确认模块归属");
    expect(text).toContain("匹配依据");
    expect(text).toContain("候选模块");
    expect(text).toContain("历史任务名称相似");
  });
});
