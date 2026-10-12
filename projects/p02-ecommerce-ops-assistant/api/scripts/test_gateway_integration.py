"""Verification script for shared/llm-gateway integration with P02.

Tests 3 scenarios:
  1. Normal call via primary endpoint → success
  2. Primary broken → automatic failover to backup → success
  3. No API key → mock response with clear marker
"""

import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from llm_gateway import chat_completion_json, get_cost_report

REAL_BASE = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
REAL_KEY = "sk-sp-H.DPXRMP.tPFm.MEUCIQCHWQK_lWs_md3EB8wjk8aK12Rghe85CucGtLXQ_mi3mAIgJolVqV7L9LlazsVZbpEalyfkPo9sFlKbvBrGEv6bVC4"
REAL_MODEL = "qwen3.8-flash"
BROKEN_BASE = "https://this-host-does-not-exist.invalid/v1"

MESSAGES = [
    {"role": "system", "content": "你是一个测试助手，只返回 JSON。"},
    {"role": "user", "content": '返回 {"ok": true, "test": "hello"}'},
]


def test_scenario_1():
    """Primary endpoint works, fallback is broken → should succeed via primary."""
    print("\n" + "=" * 60)
    print("SCENARIO 1: Normal call via primary endpoint")
    print("=" * 60)
    parsed, raw = chat_completion_json(
        MESSAGES,
        base_url=REAL_BASE,
        api_key=REAL_KEY,
        model=REAL_MODEL,
        fallback_base_url=BROKEN_BASE,
        max_tokens=100,
        temperature=0,
    )
    assert parsed.get("ok") is True, f"Expected ok=true, got {parsed}"
    assert "__mock__" not in parsed, "Should NOT be mock"
    usage = raw.get("usage", {})
    print(f"  parsed: {parsed}")
    print(f"  model:  {raw.get('model')}")
    print(f"  tokens: prompt={usage.get('prompt_tokens')}, completion={usage.get('completion_tokens')}, total={usage.get('total_tokens')}")
    print("  RESULT: PASS")
    return True


def test_scenario_2():
    """Primary is broken, fallback works → should succeed via failover."""
    print("\n" + "=" * 60)
    print("SCENARIO 2: Primary broken → failover to backup")
    print("=" * 60)
    parsed, raw = chat_completion_json(
        MESSAGES,
        base_url=BROKEN_BASE,
        api_key=REAL_KEY,
        model=REAL_MODEL,
        fallback_base_url=REAL_BASE,
        max_tokens=100,
        temperature=0,
    )
    assert parsed.get("ok") is True, f"Expected ok=true, got {parsed}"
    assert "__mock__" not in parsed, "Should NOT be mock"
    usage = raw.get("usage", {})
    print(f"  parsed: {parsed}")
    print(f"  model:  {raw.get('model')}")
    print(f"  tokens: prompt={usage.get('prompt_tokens')}, completion={usage.get('completion_tokens')}, total={usage.get('total_tokens')}")
    print("  RESULT: PASS (failover succeeded)")
    return True


def test_scenario_3():
    """No API key → mock response with clear marker."""
    print("\n" + "=" * 60)
    print("SCENARIO 3: No API key → mock degradation")
    print("=" * 60)
    parsed, raw = chat_completion_json(
        MESSAGES,
        base_url=REAL_BASE,
        api_key=None,
        model=REAL_MODEL,
        max_tokens=100,
        temperature=0,
    )
    assert parsed.get("__mock__") is True, f"Expected __mock__=true, got {parsed}"
    assert parsed.get("mock_reason") == "not_configured"
    usage = raw.get("usage", {})
    assert usage.get("total_tokens") == 0, "Mock should have 0 tokens"
    print(f"  parsed: {parsed}")
    print(f"  raw.choices[0].message.content: {raw['choices'][0]['message']['content'][:100]}")
    print(f"  tokens: all 0 (mock)")
    print("  RESULT: PASS (mock returned, no exception)")
    return True


def test_scenario_4_all_endpoints_fail():
    """Both primary and fallback broken → mock with all_endpoints_failed."""
    print("\n" + "=" * 60)
    print("SCENARIO 4: All endpoints fail → mock degradation")
    print("=" * 60)
    parsed, raw = chat_completion_json(
        MESSAGES,
        base_url=BROKEN_BASE,
        api_key=REAL_KEY,
        model=REAL_MODEL,
        fallback_base_url="https://also-broken.invalid/v1",
        max_tokens=100,
        temperature=0,
    )
    assert parsed.get("__mock__") is True, f"Expected __mock__=true, got {parsed}"
    assert parsed.get("mock_reason") == "all_endpoints_failed"
    print(f"  parsed: {parsed}")
    print("  RESULT: PASS (mock returned after all endpoints failed)")
    return True


def main():
    results = []
    for test_fn in [test_scenario_1, test_scenario_2, test_scenario_3, test_scenario_4_all_endpoints_fail]:
        try:
            results.append((test_fn.__name__, test_fn()))
        except Exception as exc:
            print(f"  RESULT: FAIL — {exc}")
            results.append((test_fn.__name__, False))

    print("\n" + "=" * 60)
    print("COST REPORT (after all scenarios)")
    print("=" * 60)
    report = get_cost_report()
    print(f"  total_calls:              {report.total_calls}")
    print(f"  total_tokens:             {report.total_tokens}")
    print(f"  total_latency_ms:         {report.total_latency_ms:.0f}")
    print(f"  mock_calls:               {report.mock_calls}")
    print(f"  calls_by_model:           {report.calls_by_model}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\nAll scenarios passed.")
    else:
        print("\nSome scenarios FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
