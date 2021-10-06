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
    weth,
    RELATIVE_APPROX,
):
    # Deposit to the vault and harvest
    actions.user_deposit(user, vault, token, amount)

    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    pre_want_balance = token.balanceOf(strategy)

    new_strategy = strategist.deploy(Strategy, vault)
    weth.transfer(
        new_strategy, 1e6, {"from": "0xBA12222222228d8Ba445958a75a0704d566BF2C8"}
    )

    # mirgration with more than dust reverts, there is no way to transfer the debt position
    with brownie.reverts():
        vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    vault.revokeStrategy(strategy, {"from": gov})
    strategy.harvest({"from": gov})

    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    vault.updateStrategyDebtRatio(new_strategy, 10_000, {"from": gov})
    new_strategy.harvest({"from": gov})

    assert (
        pytest.approx(new_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX)
        == amount
    )

    assert pre_want_balance == token.balanceOf(new_strategy)

    # check that harvest work as expected
    new_strategy.harvest({"from": gov})
