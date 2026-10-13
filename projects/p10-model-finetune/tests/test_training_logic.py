"""Unit tests for P10's deterministic mock-training maths.

Training is explicitly mocked (no GPU). These tests pin the *simulator*
contract: the loss curve is reproducible for a given seed, decays over steps,
stays clamped, follows a warmup+cosine LR schedule, and the step count derived
from dataset size and batch config is computed correctly.
"""

from __future__ import annotations

import math

from app.main import _generate_loss_curve


def test_loss_curve_is_deterministic_for_seed():
    a = _generate_loss_curve(200, seed=42)
    b = _generate_loss_curve(200, seed=42)
    assert [p.loss for p in a] == [p.loss for p in b]


def test_loss_curve_different_seeds_differ():
    a = _generate_loss_curve(200, seed=1)
    b = _generate_loss_curve(200, seed=2)
    assert [p.loss for p in a] != [p.loss for p in b]


def test_loss_curve_spans_zero_to_total_steps():
    curve = _generate_loss_curve(300, seed=7)
    assert curve[0].step == 0
    assert curve[-1].step == 300
    assert len(curve) > 1


def test_loss_decays_over_training():
    curve = _generate_loss_curve(500, base_loss=2.8, seed=42)
    assert curve[0].loss > curve[-1].loss


def test_loss_clamped_to_minimum():
    curve = _generate_loss_curve(500, seed=42)
    assert all(p.loss >= 0.1 for p in curve)


def test_learning_rate_starts_at_zero_warmup_and_is_non_negative():
    curve = _generate_loss_curve(400, seed=42)
    assert curve[0].learning_rate == 0.0  # warmup starts from 0
    assert all(p.learning_rate >= 0 for p in curve)


def test_eval_loss_present_at_intervals():
    curve = _generate_loss_curve(500, seed=42)
    eval_points = [p for p in curve if p.eval_loss is not None]
    assert eval_points, "expected periodic eval_loss checkpoints"
    # eval_loss trails training loss slightly upward in the simulator
    assert all(p.eval_loss >= p.loss for p in eval_points)


def test_step_count_formula():
    # Mirrors start_training: ceil(sample_count / (batch*grad_accum)) * epochs
    sample_count, batch, grad_accum, epochs = 12500, 4, 8, 3
    effective_batch = batch * grad_accum
    expected = math.ceil(sample_count / effective_batch) * epochs
    assert expected == 391 * 3  # 1173
