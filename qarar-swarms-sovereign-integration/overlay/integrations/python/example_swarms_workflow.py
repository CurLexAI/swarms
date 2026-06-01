# SPDX-License-Identifier: MIT
# Licensed under MIT
from __future__ import annotations

from qarar_swarms import create_qarar_tool

legal_reasoning_tool = create_qarar_tool(
    task_type="LEGAL_REASONING",
    agent_id="swarms.legal-reasoning-agent",
    data_class="INTERNAL",
    contains_pii=False,
    context={"authority": "SAMA"},
)

local_context_tool = create_qarar_tool(
    task_type="LOCAL_CONTEXT",
    agent_id="swarms.local-context-agent",
    data_class="INTERNAL",
    contains_pii=False,
    context={"jurisdiction": "KSA"},
)

arabic_drafting_tool = create_qarar_tool(
    task_type="ARABIC_DRAFTING",
    agent_id="swarms.arabic-drafting-agent",
    data_class="INTERNAL",
    contains_pii=False,
    context={"language": "ar-SA"},
)


def run_minimal_sequence(question: str) -> str:
    local_context = local_context_tool(question)
    legal_analysis = legal_reasoning_tool(f"السؤال: {question}\nالسياق المحلي: {local_context}")
    return arabic_drafting_tool(f"صغ الناتج العربي النهائي بناء على التحليل التالي:\n{legal_analysis}")


if __name__ == "__main__":
    print(run_minimal_sequence("ما ضوابط مشاركة بيانات عميل مصرفي مع مزود خارجي؟"))
