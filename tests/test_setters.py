import brownie
import pytest


def test_setters(strategy, management):
    with brownie.reverts("< MAX_BPS"):
        strategy.setDiscount(2 ** 256 - 1, {"from": management})
