from brownie import Wei, chain
import pytest


def test_airdrop_stkaave(
    vault,
    strategy,
    token,
    stkaave,
    token_whale,
    stkaave_whale,
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
    assert strategy.harvestTrigger(1)

    # Sending staked aave pushes the cooldown
    stake_balance = stkaave.balanceOf(strategy)
    stkaave.transfer(strategy, stake_balance * .1, {"from": stkaave_whale})
    assert strategy.harvestTrigger(1) == False

    # Sleep for one more day since we sent 10%
    chain.sleep(3600 * 24 * 1 + 1)
    chain.mine()

    assert strategy.harvestTrigger(1)
