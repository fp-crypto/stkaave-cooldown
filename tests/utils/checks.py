import brownie
from brownie import interface
import pytest

# This file is reserved for standard checks
def check_vault_empty(vault):
    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0


def check_strategy_empty(strategy):
    assert strategy.estimatedTotalAssets() == 0
    vault = interface.VaultAPI(strategy.vault())
    assert vault.strategies(strategy).dict()["totalDebt"] == 0


def check_revoked_strategy(vault, strategy):
    status = vault.strategies(strategy).dict()
    assert status["debtRatio"] == 0
    assert status["totalDebt"] == 0
    return


def check_harvest_profit(tx, profit_amount, rel_approx=1e-5):
    assert (
        pytest.approx(tx.events["Harvested"]["profit"], rel=rel_approx) == profit_amount
    )


def check_harvest_profitable(tx):
    assert tx.events["Harvested"]["profit"] > 0
    assert tx.events["Harvested"]["loss"] == 0


def check_harvest_loss(tx, loss_amount, rel_approx=1e-5):
    assert pytest.approx(tx.events["Harvested"]["loss"], rel=rel_approx) == loss_amount


def check_accounting(vault, strategy, totalGain, totalLoss, totalDebt, rel_approx=1e-5):
    # inputs have to be manually calculated then checked
    status = vault.strategies(strategy).dict()
    assert pytest.approx(status["totalGain"], rel=rel_approx) == totalGain
    assert pytest.approx(status["totalLoss"], rel=rel_approx) == totalLoss
    assert pytest.approx(status["totalDebt"], rel=rel_approx) == totalDebt
    return
