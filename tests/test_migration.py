import pytest
from utils import actions
import brownie


def test_migration(
    chain,
    token,
    vault,
    strategy,
    amount,
    Strategy,
    strategist,
    gov,
    user,
):
    # Deposit to the vault and harvest
    actions.user_deposit(user, vault, token, amount)

    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.estimatedTotalAssets() >= amount

    pre_want_balance = token.balanceOf(strategy)

    new_strategy = strategist.deploy(Strategy, vault)

    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    vault.updateStrategyDebtRatio(new_strategy, 10_000, {"from": gov})
    chain.sleep(1)
    chain.mine()
    new_strategy.harvest({"from": gov})

    assert strategy.estimatedTotalAssets() == 0
    assert new_strategy.estimatedTotalAssets() >= amount

    assert pre_want_balance == token.balanceOf(new_strategy)

    # check that harvest work as expected
    chain.sleep(1)
    chain.mine()
    new_strategy.harvest({"from": gov})
