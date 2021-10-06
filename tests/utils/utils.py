import brownie
from brownie import interface, chain, Contract


def vault_status(vault):
    print(f"--- Vault {vault.name()} ---")
    print(f"API: {vault.apiVersion()}")
    print(f"TotalAssets: {to_units(vault, vault.totalAssets())}")
    print(f"PricePerShare: {to_units(vault, vault.pricePerShare())}")
    print(f"TotalSupply: {to_units(vault, vault.totalSupply())}")


def strategy_status(vault, strategy):
    status = vault.strategies(strategy).dict()
    (lend, borrow) = strategy.getCurrentPosition()
    ratio = strategy.getCurrentCollatRatio()
    print(f"--- Strategy {strategy.name()} ---")
    print(f"Performance fee {status['performanceFee']}")
    print(f"Debt Ratio {status['debtRatio']}")
    print(f"Total Debt {to_units(vault, status['totalDebt'])}")
    print(f"Total Gain {to_units(vault, status['totalGain'])}")
    print(f"Total Loss {to_units(vault, status['totalLoss'])}")
    print(f"Estimated Total Assets {to_units(vault, strategy.estimatedTotalAssets())}")
    print(
        f"Estimated Total Rewards {to_units(vault, strategy.estimatedRewardsInWant())}"
    )
    print(
        f"Loose Want {to_units(vault, Contract(strategy.want()).balanceOf(strategy))}"
    )
    print(f"Current Lend {to_units(vault, lend)}")
    print(f"Current Borrow {to_units(vault, borrow)}")
    print(f"Current LTV Ratio {ratio/1e18:.4f}")
    print(f"Target LTV Ratio {strategy.targetCollatRatio()/1e18:.4f}")
    print(f"Max LTV Ratio {strategy.maxCollatRatio()/1e18:.4f}")


def to_units(token, amount):
    return amount / (10 ** token.decimals())


def from_units(token, amount):
    return amount * (10 ** token.decimals())


# default: 6 hours (sandwich protection)
def sleep(seconds=6 * 60 * 60):
    chain.sleep(seconds)
    chain.mine(1)
