import pytest
from brownie import config, Contract, network

# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture(scope="session")
def gov(accounts):
    yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)


@pytest.fixture(scope="session")
def strat_ms(accounts):
    yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)


@pytest.fixture(scope="session")
def user(accounts):
    yield accounts[0]


@pytest.fixture(scope="session")
def rewards(accounts):
    yield accounts[1]


@pytest.fixture(scope="session")
def guardian(accounts):
    yield accounts[2]


@pytest.fixture(scope="session")
def management(accounts):
    yield accounts[3]


@pytest.fixture(scope="session")
def strategist(accounts):
    yield accounts[4]


@pytest.fixture(scope="session")
def keeper(accounts):
    yield accounts[5]


token_addresses = {
    "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9" #AAVE
}

@pytest.fixture(
    params=[
        "AAVE"
    ],
    scope="session",
    autouse=True,
)
def token(request):
    yield Contract(token_addresses[request.param])



whale_addresses = {
    "AAVE": "0x25F2226B597E8F9514B3F68F00f494cF4f286491",
}


@pytest.fixture(scope="session", autouse=True)
def token_whale(token):
    yield whale_addresses[token.symbol()]


token_prices = {
    "AAVE": 300,
}

@pytest.fixture
def stkaave():
    yield Contract("0x4da27a545c0c5B758a6BA100e3a049001de870f5")


@pytest.fixture(autouse=True, scope="function")
def amount(token, token_whale, user):
    # this will get the number of tokens (around $1m worth of token)
    base_amount = round(15_000 / token_prices[token.symbol()])
    amount = base_amount * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate a whale address
    if amount > token.balanceOf(token_whale):
        amount = token.balanceOf(token_whale)
    token.transfer(user, amount, {"from": token_whale})
    yield amount


@pytest.fixture(scope="function")
def big_amount(token, token_whale, user):
    # this will get the number of tokens (around $49m worth of token)
    fifty_minus_one_million = round(49_000_000 / token_prices[token.symbol()])
    amount = fifty_minus_one_million * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate a whale address
    if amount > token.balanceOf(token_whale):
        amount = token.balanceOf(token_whale)
    token.transfer(user, amount, {"from": token_whale})
    yield token.balanceOf(user)


@pytest.fixture
def weth():
    token_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    yield Contract(token_address)


@pytest.fixture
def weth_amount(user, weth):
    weth_amount = 10 ** weth.decimals()
    user.transfer(weth, weth_amount)
    yield weth_amount


@pytest.fixture(scope="function", autouse=True)
def vault(pm, gov, rewards, guardian, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "", "", guardian, management)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    vault.setManagementFee(0, {"from": gov})
    yield vault


@pytest.fixture(scope="session")
def registry():
    yield Contract("0x50c1a2eA0a861A967D9d0FFE2AE4012c2E053804")


@pytest.fixture(scope="session")
def live_vault(registry, token):
    yield registry.latestVault(token)


@pytest.fixture(scope="function")
def strategy(chain, strategist, keeper, vault, Strategy, gov, weth):
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})

    yield strategy


@pytest.fixture()
def enable_healthcheck(strategy, gov):
    strategy.setHealthCheck("0xDDCea799fF1699e98EDF118e0629A974Df7DF012", {"from": gov})
    strategy.setDoHealthCheck(True, {"from": gov})
    yield True


@pytest.fixture(scope="session", autouse=True)
def RELATIVE_APPROX():
    yield 1e-5
