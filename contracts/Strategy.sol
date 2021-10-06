// SPDX-License-Identifier: AGPL-3.0
// Feel free to change the license, but this is what we use

// Feel free to change this version of Solidity. We support >=0.6.0 <0.7.0;
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

// These are the core Yearn libraries
import {
    BaseStrategyInitializable
} from "@yearn/yearn-vaults/contracts/BaseStrategy.sol";

import {
    SafeERC20,
    SafeMath,
    IERC20,
    Address
} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

import "@openzeppelin/contracts/math/Math.sol";

import "../interfaces/uniswap/IUni.sol";
import {ISwapRouter} from "../interfaces/uniswap/ISwapRouter.sol";

import "../interfaces/aave/IStakedAave.sol";

contract Strategy is BaseStrategyInitializable {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    // Token addresses
    address private constant aave = 0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9;
    IStakedAave private constant stkAave =
        IStakedAave(0x4da27a545c0c5B758a6BA100e3a049001de870f5);
    address private constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;

    // represents stkAave cooldown status
    // 0 = no cooldown or past withdraw period
    // 1 = claim period
    // 2 = cooldown initiated, future claim period
    enum CooldownStatus {None, Claim, Initiated}

    // SWAP routers
    IUni private constant SUSHI_V2_ROUTER =
        IUni(0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F);
    ISwapRouter private constant UNI_V3_ROUTER =
        ISwapRouter(0xE592427A0AEce92De3Edee1F18E0157C05861564);

    // OPS State Variables
    uint24 public aaveToStkAaveSwapFee = 10000;
    uint256 private stkAaveDiscountBps = 150;

    uint256 private constant MAX_BPS = 1e4;

    constructor(address _vault) public BaseStrategyInitializable(_vault) {
        _initializeThis();
    }

    function initialize(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper
    ) external override {
        _initialize(_vault, _strategist, _rewards, _keeper);
        _initializeThis();
    }

    function _initializeThis() internal {
        require(address(want) == address(aave));

        aaveToStkAaveSwapFee = 10000;
        stkAaveDiscountBps = 350;

        // approve swap router spend
        approveMaxSpend(address(stkAave), address(UNI_V3_ROUTER));
        approveMaxSpend(aave, address(UNI_V3_ROUTER));
    }

    function setSwapFee(uint24 _aaveToStkAaveSwapFee)
        external
        onlyVaultManagers
    {
        require(
            _aaveToStkAaveSwapFee == 500 ||
                _aaveToStkAaveSwapFee == 3000 ||
                _aaveToStkAaveSwapFee == 10000
        );
        aaveToStkAaveSwapFee = _aaveToStkAaveSwapFee;
    }

    function setDiscount(uint256 _stkAaveDiscountBps)
        external
        onlyVaultManagers
    {
        require(stkAaveDiscountBps < MAX_BPS);
        stkAaveDiscountBps = _stkAaveDiscountBps;
    }

    function name() external view override returns (string memory) {
        return "StrategyStkAaveCooldown";
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        return balanceOfWant().add(balanceOfStkAave());
    }

    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        // claim rewards
        _claimRewards();

        // account for profit / losses
        uint256 totalDebt = vault.strategies(address(this)).totalDebt;

        uint256 totalAssets = estimatedTotalAssets();

        if (totalDebt > totalAssets) {
            // we have losses
            _loss = totalDebt.sub(totalAssets);
        } else {
            // we have profit
            _profit = totalAssets.sub(totalDebt);
        }

        // free funds to repay debt + profit to the strategy
        uint256 amountAvailable = balanceOfWant();
        uint256 amountRequired = _debtOutstanding.add(_profit);

        if (amountRequired > amountAvailable) {
            // we need to free funds
            // we dismiss losses here, they cannot be generated from withdrawal
            // but it is possible for the strategy to unwind full position
            (amountAvailable, ) = liquidatePosition(amountRequired);

            if (amountAvailable >= amountRequired) {
                _debtPayment = _debtOutstanding;
                // profit remains unchanged unless there is not enough to pay it
                if (amountRequired.sub(_debtPayment) < _profit) {
                    _profit = amountRequired.sub(_debtPayment);
                }
            } else {
                // we were not able to free enough funds
                if (amountAvailable < _debtOutstanding) {
                    // available funds are lower than the repayment that we need to do
                    _profit = 0;
                    _debtPayment = amountAvailable;
                    // we dont report losses here as the strategy might not be able to return in this harvest
                    // but it will still be there for the next harvest
                } else {
                    // NOTE: amountRequired is always equal or greater than _debtOutstanding
                    // important to use amountRequired just in case amountAvailable is > amountAvailable
                    _debtPayment = _debtOutstanding;
                    _profit = amountAvailable.sub(_debtPayment);
                }
            }
        } else {
            _debtPayment = _debtOutstanding;
            // profit remains unchanged unless there is not enough to pay it
            if (amountRequired.sub(_debtPayment) < _profit) {
                _profit = amountRequired.sub(_debtPayment);
            }
        }
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        uint256 wantBalance = balanceOfWant();

        if (_debtOutstanding >= wantBalance) {
            return;
        }

        uint256 amountToSwap = wantBalance.sub(_debtOutstanding);
        uint256 amountToReceive =
            amountToSwap.mul(MAX_BPS.sub(stkAaveDiscountBps)).div(MAX_BPS);
        _swapAaveForStkAave(amountToSwap, amountToReceive);

        _startCooldown();
    }

    function liquidatePosition(uint256 _amountNeeded)
        internal
        override
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        uint256 freeAssets = balanceOfWant();
        _liquidatedAmount = freeAssets;
    }

    function liquidateAllPositions()
        internal
        override
        returns (uint256 _amountFreed)
    {
        (_amountFreed, ) = liquidatePosition(type(uint256).max);
    }

    function prepareMigration(address _newStrategy) internal override {
        IERC20(address(stkAave)).safeTransfer(_newStrategy, balanceOfStkAave());
    }

    function protectedTokens()
        internal
        view
        override
        returns (address[] memory)
    {}

    // INTERNAL ACTIONS

    function _claimRewards() internal {
        uint256 stkAaveBalance = balanceOfStkAave();
        CooldownStatus cooldownStatus;
        if (stkAaveBalance > 0) {
            cooldownStatus = _checkCooldown(); // don't check status if we have no stkAave
        }

        // If it's the claim period claim
        if (stkAaveBalance > 0 && cooldownStatus == CooldownStatus.Claim) {
            // redeem AAVE from stkAave
            stkAave.claimRewards(address(this), type(uint256).max);
            stkAave.redeem(address(this), stkAaveBalance);
        }
    }

    function _startCooldown() internal {
        uint256 stkAaveBalance = balanceOfStkAave();
        if (stkAaveBalance == 0) return;

        CooldownStatus cooldownStatus = _checkCooldown();

        if (cooldownStatus == CooldownStatus.None) {
            stkAave.cooldown();
        }
    }

    // INTERNAL VIEWS
    function balanceOfWant() internal view returns (uint256) {
        return want.balanceOf(address(this));
    }

    function balanceOfStkAave() internal view returns (uint256) {
        return IERC20(address(stkAave)).balanceOf(address(this));
    }

    // conversions
    function tokenToWant(address token, uint256 amount)
        internal
        view
        returns (uint256)
    {
        if (amount == 0 || address(want) == token) {
            return amount;
        }

        uint256[] memory amounts =
            SUSHI_V2_ROUTER.getAmountsOut(
                amount,
                getTokenOutPathV2(token, address(want))
            );

        return amounts[amounts.length - 1];
    }

    function ethToWant(uint256 _amtInWei)
        public
        view
        override
        returns (uint256)
    {
        return tokenToWant(weth, _amtInWei);
    }

    function _checkCooldown() internal view returns (CooldownStatus) {
        uint256 cooldownStartTimestamp =
            IStakedAave(stkAave).stakersCooldowns(address(this));
        uint256 COOLDOWN_SECONDS = IStakedAave(stkAave).COOLDOWN_SECONDS();
        uint256 UNSTAKE_WINDOW = IStakedAave(stkAave).UNSTAKE_WINDOW();
        uint256 nextClaimStartTimestamp =
            cooldownStartTimestamp.add(COOLDOWN_SECONDS);

        if (cooldownStartTimestamp == 0) {
            return CooldownStatus.None;
        }
        if (
            block.timestamp > nextClaimStartTimestamp &&
            block.timestamp <= nextClaimStartTimestamp.add(UNSTAKE_WINDOW)
        ) {
            return CooldownStatus.Claim;
        }
        if (block.timestamp < nextClaimStartTimestamp) {
            return CooldownStatus.Initiated;
        }
    }

    function getTokenOutPathV2(address _token_in, address _token_out)
        internal
        pure
        returns (address[] memory _path)
    {
        bool is_weth =
            _token_in == address(weth) || _token_out == address(weth);
        _path = new address[](is_weth ? 2 : 3);
        _path[0] = _token_in;

        if (is_weth) {
            _path[1] = _token_out;
        } else {
            _path[1] = address(weth);
            _path[2] = _token_out;
        }
    }

    function _swapAaveForStkAave(uint256 amountIn, uint256 minOut) internal {
        // Swap Rewards in UNIV3
        // NOTE: Unoptimized, can be frontrun and most importantly this pool is low liquidity
        UNI_V3_ROUTER.exactInputSingle(
            ISwapRouter.ExactInputSingleParams(
                address(aave),
                address(stkAave),
                aaveToStkAaveSwapFee,
                address(this),
                now,
                amountIn, // wei
                minOut,
                0
            )
        );
    }

    function approveMaxSpend(address token, address spender) internal {
        IERC20(token).safeApprove(spender, type(uint256).max);
    }
}
