import pytest
from utils import actions, utils


def test_clone(
    vault,
    strategy,
    token,
    amount,
    strategist,
    rewards,
    keeper,
    gov,
    user,
    RELATIVE_APPROX,
    Strategy,
    chain
):
    user_balance_before = token.balanceOf(user)
    actions.user_deposit(user, vault, token, amount)

    # harvest
    utils.sleep(1)
    strategy.harvest({"from": strategist})
    assert strategy.estimatedTotalAssets() >= amount

    # Sleep for 10 days to unlock stkAave
    utils.sleep(int(10.1 * 24 * 3600))

    cloned_strategy = strategy.clone(
        vault, strategist, rewards, keeper, {"from": strategist}
    ).return_value
    cloned_strategy = Strategy.at(cloned_strategy)

    # free funds from old strategy
    vault.revokeStrategy(strategy, {"from": gov})
    utils.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.estimatedTotalAssets() == 0

    # take funds to new strategy
    vault.addStrategy(cloned_strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    utils.sleep(1)

    cloned_strategy.harvest({"from": gov})
    assert cloned_strategy.estimatedTotalAssets() >= amount
