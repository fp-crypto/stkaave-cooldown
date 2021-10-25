from brownie import Wei, chain
import pytest


def test_happy_path(
    vault,
    strategy,
    token,
    stkaave,
    token_whale,
    management
):
    token.approve(vault, 2**256-1, {"from": token_whale})
    vault.deposit(Wei("10 ether"), {"from": token_whale})
    strategy.harvest({"from": management})

    assert stkaave.balanceOf(strategy) > 0
    assert token.balanceOf(strategy) == 0

    # Sleep for 10 days + 1sec
    chain.sleep(3600 * 24 * 10 + 1)
    chain.mine()

    tx = strategy.harvest({"from": management})
    first_profit = tx.events['Harvested']['profit']
    assert  first_profit > 0
    assert vault.strategies(strategy).dict()['totalLoss'] == 0

    # Sleep for 10 days + 1sec
    chain.sleep(3600 * 24 * 10 + 1)
    chain.mine()

    vault.updateStrategyDebtRatio(strategy, 0, {"from": management})
    tx = strategy.harvest({"from": management})
    second_profit = tx.events['Harvested']['profit']
    assert  second_profit > 0

    assert vault.strategies(strategy).dict()['totalLoss'] == 0
    assert vault.strategies(strategy).dict()['debtRatio'] == 0
    assert vault.strategies(strategy).dict()['totalDebt'] == 0
    assert vault.strategies(strategy).dict()['totalGain'] == first_profit + second_profit
