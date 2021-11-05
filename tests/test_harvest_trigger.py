from brownie import Wei, chain
import pytest


def test_harvest_trigger(vault, strategy, token, stkaave, token_whale, management):
    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(Wei("10 ether"), {"from": token_whale})
    strategy.harvest({"from": management})

    assert strategy.harvestTrigger(1) == False

    # Sleep for 10 days + 1sec
    chain.sleep(3600 * 24 * 10 + 1)
    chain.mine()

    # After the 10 days, trigger should be true
    assert strategy.harvestTrigger(1) == True
