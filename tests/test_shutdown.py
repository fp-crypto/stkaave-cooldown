import pytest
from utils import checks, actions, utils

# TODO: Add tests that show proper operation of this strategy through "emergencyExit"
#       Make sure to demonstrate the "worst case losses" as well as the time it takes


def test_shutdown(
    chain, token, token_whale, vault, strategy, amount, gov, user, RELATIVE_APPROX
):
    # Deposit to the vault and harvest
    actions.user_deposit(user, vault, token, amount)
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # Generate profit
    profit_amount = amount * 0.1  # 10% profit
    actions.generate_profit(strategy, token_whale, profit_amount)

    strategy.harvest({"from": gov})
    utils.sleep()

    totalGain = profit_amount
    totalLoss = 0
    totalDebt = amount
    checks.check_accounting(vault, strategy, totalGain, totalLoss, totalDebt)
