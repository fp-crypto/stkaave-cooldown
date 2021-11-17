from brownie import Wei, chain
import pytest


def test_harvest_trigger(vault, strategy, token, token_whale, management):
    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(Wei("10 ether"), {"from": token_whale})
    strategy.harvest({"from": management})

    assert strategy.harvestTrigger(1) == False

    # Sleep for 10 days + 1sec
    chain.sleep(3600 * 24 * 10 + 1)
    chain.mine()

    # After the 10 days, trigger should be true
    assert strategy.harvestTrigger(1) == True

    strategy.setMaxAcceptableBaseFee(Wei("100 gwei"), {"from": management})
    # With baseFee max exceeded, trigger should be false
    assert strategy.harvestTrigger(1) == False

    # Sleep for 1 day
    chain.sleep(3600 * 24 * 1)
    chain.mine()

    # With less than 24 hours to claim, harvest trigger should be true
    assert strategy.harvestTrigger(1) == True

    # Sleep for 1 day
    chain.sleep(3600 * 24 * 1)
    chain.mine()

    # we missed the claim period and baseFee is too high should be false
    assert strategy.harvestTrigger(1) == False

    strategy.setMaxAcceptableBaseFee(Wei("1000 gwei"), {"from": management})
    # we missed the claim period and baseFee is acceptable should be true
    assert strategy.harvestTrigger(1) == True
