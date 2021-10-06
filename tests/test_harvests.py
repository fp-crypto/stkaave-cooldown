from utils import actions, checks, utils
import pytest

# tests harvesting a strategy that returns profits correctly
def test_profitable_harvest(
    chain,
    accounts,
    token,
    token_whale,
    vault,
    strategy,
    user,
    strategist,
    amount,
    RELATIVE_APPROX,
):
    # Deposit to the vault
    actions.user_deposit(user, vault, token, amount)

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": strategist})
    total_assets = strategy.estimatedTotalAssets()
    assert total_assets >= amount

    profit_amount = amount * 0.05
    actions.generate_profit(strategy, token_whale, profit_amount)

    # check that estimatedTotalAssets estimates correctly
    assert (
        pytest.approx(total_assets + profit_amount, rel=RELATIVE_APPROX)
        == strategy.estimatedTotalAssets()
    )

    before_pps = vault.pricePerShare()
    # Harvest 2: Realize profit
    chain.sleep(1)
    tx = strategy.harvest({"from": strategist})
    checks.check_harvest_profit(tx, profit_amount)

    utils.sleep(3600 * 6)  # 6 hrs needed for profits to unlock
    profit = token.balanceOf(vault.address)  # Profits go to vault

    assert strategy.estimatedTotalAssets() + profit > amount
    assert vault.pricePerShare() > before_pps


# tests harvesting a strategy that reports losses
def test_lossy_harvest(
    chain, accounts, token, vault, strategy, user, strategist, amount, RELATIVE_APPROX
):
    # Deposit to the vault
    actions.user_deposit(user, vault, token, amount)

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": strategist})
    total_assets = strategy.estimatedTotalAssets()
    assert total_assets >= amount

    loss_amount = amount * 0.05
    actions.generate_loss(strategy, loss_amount)

    # check that estimatedTotalAssets estimates correctly
    assert (
        pytest.approx(total_assets - loss_amount, rel=RELATIVE_APPROX)
        == strategy.estimatedTotalAssets()
    )

    # Harvest 2: Realize loss
    chain.sleep(1)
    tx = strategy.harvest({"from": strategist})
    checks.check_harvest_loss(tx, loss_amount)
    chain.mine(1)

    # User will withdraw accepting losses
    vault.withdraw(vault.balanceOf(user), user, 10_000, {"from": user})
    assert (
        pytest.approx(token.balanceOf(user) + loss_amount, rel=RELATIVE_APPROX)
        == amount
    )


# tests harvesting a strategy twice, once with loss and another with profit
# it checks that even with previous profit and losses, accounting works as expected
def test_choppy_harvest(
    chain,
    accounts,
    token,
    token_whale,
    vault,
    strategy,
    user,
    strategist,
    amount,
    RELATIVE_APPROX,
):
    # Deposit to the vault
    actions.user_deposit(user, vault, token, amount)

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": strategist})

    assert strategy.estimatedTotalAssets() >= amount

    loss_amount = amount * 0.05
    actions.generate_loss(strategy, loss_amount)

    # Harvest 2: Realize loss
    chain.sleep(1)
    tx = strategy.harvest({"from": strategist})
    checks.check_harvest_loss(tx, loss_amount)

    profit_amount = amount * 0.1  # 10% profit
    actions.generate_profit(strategy, token_whale, profit_amount)

    chain.sleep(1)
    chain.mine(1)
    tx = strategy.harvest({"from": strategist})
    checks.check_harvest_profit(tx, profit_amount)

    chain.sleep(3600 * 6)
    chain.mine(1)

    # User will withdraw accepting losses
    vault.withdraw({"from": user})

    # User will take 100% losses and 100% profits
    # assert (
    #    pytest.approx(token.balanceOf(user), rel=RELATIVE_APPROX)
    #    == amount + profit_amount - loss_amount
    # )
