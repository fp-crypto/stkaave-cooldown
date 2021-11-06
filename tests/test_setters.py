import brownie
import pytest


def test_set_discount(strategy, management):
    with brownie.reverts():
        strategy.setDiscount(2 ** 256 - 1, {"from": management})
    strategy.setDiscount(1, {"from": management})
    assert strategy.stkAaveDiscountBps() == 1


def test_set_swap_fee(strategy, management):
    with brownie.reverts():
        strategy.setSwapFee(1, {"from": management})
    strategy.setSwapFee(500, {"from": management})
    assert strategy.aaveToStkAaveSwapFee() == 500


def test_set_force_cooldown(strategy, management):
    strategy.setForceCooldown(True, {"from": management})
    assert strategy.forceCooldown()


def test_set_dust_threshold(strategy, management):
    strategy.setDustThreshold(0, {"from": management})
    assert strategy.dustThreshold() == 0
