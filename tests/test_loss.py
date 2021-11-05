from brownie import Wei, chain
import pytest


def test_loss(vault, strategy, token, stkaave, token_whale, management):
    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(Wei("10 ether"), {"from": token_whale})

    strategy.harvest({"from": management})

    assert stkaave.balanceOf(strategy) > 0

    # Mimic sending stkaave to mgmt like if it was a loss
    stkaave.transfer(
        management, int(stkaave.balanceOf(strategy) * 0.3), {"from": strategy}
    )

    # Sleep for 10 days + 1sec
    chain.sleep(3600 * 24 * 10 + 1)
    chain.mine()

    vault.updateStrategyDebtRatio(strategy, 0, {"from": management})
    tx = strategy.harvest({"from": management})
    assert tx.events["Harvested"]["loss"] > 0
    assert vault.strategies(strategy).dict()["debtRatio"] == 0
    assert vault.strategies(strategy).dict()["totalDebt"] == 0
