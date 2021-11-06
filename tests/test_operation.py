import brownie
from brownie import Contract, test
import pytest
from utils import actions, checks, utils


def test_operation(
    chain, gov, token, vault, strategy, user, strategist, amount, RELATIVE_APPROX
):
    # Deposit to the vault
    user_balance_before = token.balanceOf(user)
    actions.user_deposit(user, vault, token, amount)

    # harvest
    chain.sleep(1)
    strategy.harvest({"from": strategist})
    assert strategy.estimatedTotalAssets() >= amount

    utils.strategy_status(vault, strategy)

    # tend()
    strategy.tend({"from": strategist})

    utils.strategy_status(vault, strategy)

    utils.sleep(10 * 24 * 3600)
    vault.revokeStrategy(strategy.address, {"from": gov})
    strategy.harvest({"from": strategist})

    # withdrawal
    vault.withdraw({"from": user})
    assert (
        pytest.approx(token.balanceOf(user), rel=RELATIVE_APPROX) == user_balance_before
    )


def test_apr(
    chain,
    gov,
    token,
    vault,
    strategy,
    user,
    strategist,
    amount,
):
    # Deposit to the vault
    actions.user_deposit(user, vault, token, amount)

    # harvest
    chain.sleep(1)
    strategy.harvest({"from": strategist})
    assert strategy.estimatedTotalAssets() >= amount

    utils.sleep(int(10 * 24 * 3600) + 1)

    vault.revokeStrategy(strategy.address, {"from": gov})
    strategy.harvest({"from": strategist})
    print(
        f"APR: {(token.balanceOf(vault)-amount)*(365/10)*100/amount:.2f}% on {amount/10**token.decimals():,.2f}"
    )


def test_withdraw(
    chain, gov, token, vault, strategy, user, strategist, amount, RELATIVE_APPROX
):
    # Deposit to the vault
    user_balance_before = token.balanceOf(user)
    actions.user_deposit(user, vault, token, amount)

    vault.updateStrategyDebtRatio(strategy, 5000, {"from": gov})

    # harvest
    chain.sleep(1)
    strategy.harvest({"from": strategist})
    assert strategy.estimatedTotalAssets() >= amount * 0.5
    utils.strategy_status(vault, strategy)

    vault.updateStrategyDebtRatio(strategy, 10000, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": strategist})
    assert strategy.estimatedTotalAssets() >= amount
    utils.strategy_status(vault, strategy)

    vault.withdraw({"from": user})
    assert (
        pytest.approx(token.balanceOf(user), rel=RELATIVE_APPROX)
        == user_balance_before * 0.5
    )
    utils.strategy_status(vault, strategy)

    utils.sleep(10 * 24 * 3600 + 1)
    vault.revokeStrategy(strategy.address, {"from": gov})
    strategy.harvest({"from": strategist})
    utils.strategy_status(vault, strategy)

    # withdrawal
    vault.withdraw({"from": user})
    assert token.balanceOf(user) > user_balance_before


def test_harvest_after_long_idle_period(
    chain, token, vault, strategy, user, strategist, amount
):
    # Deposit to the vault
    actions.user_deposit(user, vault, token, amount)

    # harvest
    chain.sleep(1)
    strategy.harvest({"from": strategist})
    assert strategy.estimatedTotalAssets() >= amount

    utils.strategy_status(vault, strategy)

    utils.sleep(26 * 7 * 24 * 3600)
    utils.strategy_status(vault, strategy)
    strategy.harvest({"from": strategist})
    utils.strategy_status(vault, strategy)

    utils.sleep((10 * 24 * 3600) + 1)
    utils.strategy_status(vault, strategy)
    strategy.harvest({"from": strategist})
    utils.strategy_status(vault, strategy)


def test_emergency_exit(
    chain, accounts, token, vault, strategy, user, strategist, amount, RELATIVE_APPROX
):
    # Deposit to the vault
    actions.user_deposit(user, vault, token, amount)
    chain.sleep(1)
    strategy.harvest({"from": strategist})
    strategy.estimatedTotalAssets() >= amount

    # set emergency and exit
    strategy.setEmergencyExit()
    chain.sleep(1)
    strategy.harvest({"from": strategist})
    # assert strategy.estimatedTotalAssets() < amount


@pytest.mark.parametrize(
    "starting_debt_ratio", [100, 500, 1_000, 2_500, 5_000, 7_500, 9_500, 9_900]
)
def test_increase_debt_ratio(
    chain,
    gov,
    token,
    vault,
    strategy,
    user,
    strategist,
    amount,
    starting_debt_ratio,
    RELATIVE_APPROX,
):
    # Deposit to the vault and harvest
    actions.user_deposit(user, vault, token, amount)
    vault.updateStrategyDebtRatio(strategy.address, starting_debt_ratio, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": strategist})
    part_amount = int(amount * starting_debt_ratio / 10_000)

    utils.strategy_status(vault, strategy)

    assert (
        pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX)
        == part_amount
        or strategy.estimatedTotalAssets() > part_amount
    )

    vault.updateStrategyDebtRatio(strategy.address, 10_000, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": strategist})

    utils.strategy_status(vault, strategy)

    assert (
        pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount
        or strategy.estimatedTotalAssets() > amount
    )


@pytest.mark.parametrize(
    "ending_debt_ratio", [100, 500, 1_000, 2_500, 5_000, 7_500, 9_500, 9_900]
)
def test_decrease_debt_ratio(
    chain,
    gov,
    token,
    vault,
    strategy,
    user,
    strategist,
    amount,
    ending_debt_ratio,
    RELATIVE_APPROX,
):
    # Deposit to the vault and harvest
    actions.user_deposit(user, vault, token, amount)
    vault.updateStrategyDebtRatio(strategy.address, 10_000, {"from": gov})
    utils.sleep(1)
    strategy.harvest({"from": strategist})

    utils.strategy_status(vault, strategy)

    assert (
        pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount
        or strategy.estimatedTotalAssets() > amount
    )

    # Two harvests needed to unlock
    vault.updateStrategyDebtRatio(strategy.address, ending_debt_ratio, {"from": gov})
    utils.sleep(1)
    strategy.harvest({"from": strategist})

    utils.strategy_status(vault, strategy)

    part_amount = int(amount * ending_debt_ratio / 10_000)
    assert (
        pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX)
        == part_amount
        or strategy.estimatedTotalAssets() > part_amount
    )


def test_sweep(gov, vault, strategy, token, user, amount, weth, weth_amount):
    # Strategy want token doesn't work
    token.transfer(strategy, amount, {"from": user})
    assert token.address == strategy.want()
    assert token.balanceOf(strategy) > 0
    with brownie.reverts("!want"):
        strategy.sweep(token, {"from": gov})

    # Vault share token doesn't work
    with brownie.reverts("!shares"):
        strategy.sweep(vault.address, {"from": gov})

    before_balance = weth.balanceOf(gov) + weth.balanceOf(
        strategy
    )  # strategy has some weth to pay for flashloans
    weth.transfer(strategy, weth_amount, {"from": user})
    assert weth.address != strategy.want()
    assert weth.balanceOf(user) == 0
    strategy.sweep(weth, {"from": gov})
    assert weth.balanceOf(gov) == weth_amount + before_balance


def test_triggers(chain, gov, vault, strategy, token, amount, user, strategist):
    # Deposit to the vault and harvest
    actions.user_deposit(user, vault, token, amount)
    vault.updateStrategyDebtRatio(strategy.address, 5_000, {"from": gov})
    chain.sleep(1)
    strategy.harvest()

    strategy.harvestTrigger(0)
    strategy.tendTrigger(0)
