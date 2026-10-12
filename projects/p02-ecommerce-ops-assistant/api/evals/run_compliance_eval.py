"""广告法合规检测评测脚本。

用 api/evals/compliance_cases.jsonl 跑评测，输出拦截率（召回）与误报率（精确率）。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.compliance import ComplianceChecker

EVAL_PATH = Path(__file__).parent / "compliance_cases.jsonl"


def load_cases() -> list[dict]:
    cases = []
    with open(EVAL_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def evaluate() -> None:
    checker = ComplianceChecker()
    cases = load_cases()

    total = len(cases)
    verdict_correct = 0
    verdict_total = 0
    label_tp = 0
    label_fp = 0
    label_fn = 0

    block_cases = [c for c in cases if c["gold"]["verdict"] == "block"]
    pass_cases = [c for c in cases if c["gold"]["verdict"] == "pass"]
    review_cases = [c for c in cases if c["gold"]["verdict"] == "review"]

    adversarial_cases = [c for c in cases if c.get("difficulty") == "adversarial"]
    adversarial_bypass = 0

    details: list[dict] = []

    for case in cases:
        cid = case["id"]
        text = case["text"]
        gold_verdict = case["gold"]["verdict"]
        gold_labels = set(case["gold"].get("labels", []))
        difficulty = case.get("difficulty", "unknown")

        result = checker.check_text(text)
        pred_verdict = result.verdict
        pred_surfaces = {h.surface for h in result.hits}

        verdict_match = pred_verdict == gold_verdict
        if verdict_match:
            verdict_correct += 1
        verdict_total += 1

        for label in gold_labels:
            if label in pred_surfaces:
                label_tp += 1
            else:
                label_fn += 1

        for surface in pred_surfaces:
            if surface not in gold_labels:
                gold_normalized = set()
                for gl in gold_labels:
                    gold_normalized.add(gl)
                if surface not in gold_normalized:
                    is_partial = any(gl in surface or surface in gl for gl in gold_labels)
                    if not is_partial:
                        label_fp += 1

        if difficulty == "adversarial" and gold_verdict == "block" and pred_verdict != "block":
            adversarial_bypass += 1

        status = "OK" if verdict_match else "FAIL"
        details.append({
            "id": cid,
            "difficulty": difficulty,
            "gold_verdict": gold_verdict,
            "pred_verdict": pred_verdict,
            "gold_labels": sorted(gold_labels),
            "pred_labels": sorted(pred_surfaces),
            "status": status,
        })

    print("=" * 70)
    print("广告法合规检测评测报告")
    print("=" * 70)
    print(f"\n评测集规模：{total} 条")
    print(f"  block: {len(block_cases)}  pass: {len(pass_cases)}  review: {len(review_cases)}")
    print(f"  adversarial: {len(adversarial_cases)}")

    print(f"\n── 判定准确率 ──")
    print(f"  verdict 准确率: {verdict_correct}/{verdict_total} = {verdict_correct/verdict_total*100:.1f}%")

    print(f"\n── 标签召回与精确率 ──")
    precision = label_tp / (label_tp + label_fp) if (label_tp + label_fp) > 0 else 0
    recall = label_tp / (label_tp + label_fn) if (label_tp + label_fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    print(f"  TP={label_tp}  FP={label_fp}  FN={label_fn}")
    print(f"  精确率 (Precision): {precision*100:.1f}%")
    print(f"  召回率 (Recall):    {recall*100:.1f}%")
    print(f"  F1:                 {f1*100:.1f}%")

    print(f"\n── 高危拦截率 ──")
    block_correct = sum(1 for c in cases if c["gold"]["verdict"] == "block" and checker.check_text(c["text"]).verdict == "block")
    print(f"  block 召回: {block_correct}/{len(block_cases)} = {block_correct/len(block_cases)*100:.1f}%")

    print(f"\n── 误报率 ──")
    pass_correct = sum(1 for c in cases if c["gold"]["verdict"] == "pass" and checker.check_text(c["text"]).verdict == "pass")
    pass_false_positive = len(pass_cases) - pass_correct
    print(f"  pass 用例误报: {pass_false_positive}/{len(pass_cases)} = {pass_false_positive/len(pass_cases)*100:.1f}%")

    print(f"\n── 对抗绕过率 ──")
    adv_block = sum(1 for c in adversarial_cases if c["gold"]["verdict"] == "block")
    adv_blocked = sum(1 for c in adversarial_cases if c["gold"]["verdict"] == "block" and checker.check_text(c["text"]).verdict == "block")
    adv_bypass = adv_block - adv_blocked
    print(f"  adversarial block 绕过: {adv_bypass}/{adv_block} = {adv_bypass/adv_block*100:.1f}%" if adv_block > 0 else "  无 adversarial block 用例")

    print(f"\n── 逐条详情 ──")
    for d in details:
        marker = "  " if d["status"] == "OK" else "!!"
        print(f"  {marker} {d['id']:8s} [{d['difficulty']:11s}] gold={d['gold_verdict']:6s} pred={d['pred_verdict']:6s} | gold_labels={d['gold_labels']} | pred_labels={d['pred_labels']}")

    print(f"\n{'=' * 70}")
    print("达标判定：")
    targets = {
        "高危召回 >= 98%": block_correct / len(block_cases) >= 0.98 if block_cases else True,
        "整体误报率 <= 5%": pass_false_positive / len(pass_cases) <= 0.05 if pass_cases else True,
        "变体绕过率 < 5%": adv_bypass / adv_block < 0.05 if adv_block > 0 else True,
    }
    for name, passed in targets.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")


if __name__ == "__main__":
    evaluate()
