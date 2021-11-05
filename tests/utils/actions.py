import pytest
from brownie import accounts, chain, interface, Contract

# This file is reserved for standard actions like deposits
def user_deposit(user, vault, token, amount):
    if token.allowance(user, vault) < amount:
        token.approve(vault, 2 ** 256 - 1, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount


def generate_profit(strategy, token_whale, amount):
    token = Contract(strategy.want())
    token.transfer(strategy, amount, {"from": token_whale})
    return


def generate_loss(strategy, amount):
    strategy_account = accounts.at(strategy, force=True)
    stkAave = interface.IERC20("0x4da27a545c0c5B758a6BA100e3a049001de870f5")
    stkAave.transfer(stkAave, amount, {"from": strategy_account})
    return


def first_deposit_and_harvest(
    vault, strategy, token, user, gov, amount, RELATIVE_APPROX
):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    utils.sleep(1)
    strategy.harvest({"from": gov})
    utils.sleep(1)
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount
