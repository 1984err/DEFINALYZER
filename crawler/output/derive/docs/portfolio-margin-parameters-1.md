---
protocol: "Derive"
title: "[Legacy] Portfolio Margin Parameters"
source: "https://docs.derive.xyz/docs/portfolio-margin-parameters-1"
crawled_at: "2026-07-26T22:45:08+00:00"
---

# [Legacy] Portfolio Margin Parameters

For AI agents: visit https://docs.derive.xyz/llms.txt for an index of all pages formatted in Markdown and endpoints in OpenAPI.
[Jump to Content](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#content)
[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)v2-archive-03062026 v2-archive-09072026 v2-archive-20260724 v2-archive-22062026 v2-archive-30062026 v2.2
* * *
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/portfolio-margin-parameters-1)[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
Documentation
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/portfolio-margin-parameters-1)
v2.2
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)[Legacy] Portfolio Margin Parameters
Search
CTRL-K
## Introduction
  * [About Derive](https://docs.derive.xyz/docs/about-derive)


## Protocol
  * [Overview](https://docs.derive.xyz/docs/overview-2)
  * [Derive Chain](https://docs.derive.xyz/docs/lyra-chain)
  * [Concepts](https://docs.derive.xyz/docs/concepts)
    * [Supported Products](https://docs.derive.xyz/docs/supported-products-1)
    * [Standard Margin](https://docs.derive.xyz/docs/standard-margin-1)
    * [Portfolio Margin](https://docs.derive.xyz/docs/portfolio-margin-1)
    * [Liquidations](https://docs.derive.xyz/docs/liquidations-1)
    * [Oracles](https://docs.derive.xyz/docs/oracles-1)
    * [Settlements](https://docs.derive.xyz/docs/settlements)
    * [PM2](https://docs.derive.xyz/docs/pm2)
  * [Parameters](https://docs.derive.xyz/docs/parameters)
    * [Asset Parameters](https://docs.derive.xyz/docs/asset-parameters-1)
    * [Common Parameters](https://docs.derive.xyz/docs/common-parameters)
    * [[Legacy] Portfolio Margin Parameters](https://docs.derive.xyz/docs/portfolio-margin-parameters-1)
    * [Standard Margin Parameters](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters)
    * [Portfolio Manager](https://docs.derive.xyz/docs/copy-of-portfolio-manager-new)


## DAO & Governance
  * [Overview](https://docs.derive.xyz/docs/dao-governance-overview)
  * [Governance](https://docs.derive.xyz/docs/governance)
  * [Token](https://docs.derive.xyz/docs/token)
  * [Treasury](https://docs.derive.xyz/docs/treasury)
  * [Service Providers](https://docs.derive.xyz/docs/service-providers)


## Incentive Programs
  * [Retail Trading Rewards Program](https://docs.derive.xyz/docs/retail-trading-rewards-program)
  * [Institutional Trading Rewards Program](https://docs.derive.xyz/docs/institutional-trading-rewards-program-1)
  * [Staking Rewards Program](https://docs.derive.xyz/docs/staking-rewards-program)


## Help Center
  * [Intro to Derive](https://docs.derive.xyz/docs/what-is-derive-1)
    * [What is Derive?](https://docs.derive.xyz/docs/what-is-derive-1)
    * [How do I know my funds are safe?](https://docs.derive.xyz/docs/how-do-i-know-my-funds-are-safe)
    * [Self-Custodial Withdrawals (Escape Hatch)](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch)
    * [What are options?](https://docs.derive.xyz/docs/what-are-options)
    * [The Greeks ](https://docs.derive.xyz/docs/the-greeks)
  * [Accounts](https://docs.derive.xyz/docs/why-do-i-need-to-enable-derive)
    * [Why do I need to enable Derive?](https://docs.derive.xyz/docs/why-do-i-need-to-enable-derive)
    * [Why do I need to enable spending?](https://docs.derive.xyz/docs/why-do-i-need-to-enable-spending)
    * [What wallets are supported? ](https://docs.derive.xyz/docs/what-wallets-are-supported)
    * [What networks are supported?](https://docs.derive.xyz/docs/what-networks-are-supported)
    * [What bridge does Derive use?](https://docs.derive.xyz/docs/what-bridge-does-derive-use)
    * [How to Deposit HYPE](https://docs.derive.xyz/docs/how-to-deposit-hype)
  * [Trading](https://docs.derive.xyz/docs/what-are-the-fees)
    * [What are the fees?](https://docs.derive.xyz/docs/what-are-the-fees)
    * [Standard Margin](https://docs.derive.xyz/docs/standard-margin)
    * [Portfolio Margin](https://docs.derive.xyz/docs/portfolio-margin)
    * [Liquidations](https://docs.derive.xyz/docs/liquidations)
    * [Borrowing & Lending](https://docs.derive.xyz/docs/borrowing-lending)
    * [What happens if USDC depegs from $1?](https://docs.derive.xyz/docs/what-happens-if-usdc-depegs-from-1)
    * [Expiration & Settlement](https://docs.derive.xyz/docs/expiration-settlement)
    * [How are strikes and expiries selected?](https://docs.derive.xyz/docs/how-are-strikes-and-expiries-selected)
    * [Funding Rates](https://docs.derive.xyz/docs/funding-rates)
  * [Vaults](https://docs.derive.xyz/docs/delta-1-basis-strategy)
    * [Delta-1 Basis Strategy](https://docs.derive.xyz/docs/delta-1-basis-strategy)
    * [Delta-1 Basis Execution](https://docs.derive.xyz/docs/delta-1-basis-execution)
    * [Delta-1 Basis Risks](https://docs.derive.xyz/docs/delta-1-basis-risks)
    * [Harvest Strategy](https://docs.derive.xyz/docs/harvest-strategy)
    * [Harvest Execution](https://docs.derive.xyz/docs/harvest-execution)
    * [Harvest Risks](https://docs.derive.xyz/docs/harvest-risks)
    * [Safe Harvest Strategy](https://docs.derive.xyz/docs/safe-harvest-strategy)
    * [Safe Harvest Execution](https://docs.derive.xyz/docs/safe-harvest-execution)
    * [Safe Harvest Risks](https://docs.derive.xyz/docs/safe-harvest-risks)
    * [Maxi Strategy](https://docs.derive.xyz/docs/maxi-strategy)
    * [Maxi Execution](https://docs.derive.xyz/docs/maxi-execution)
    * [Maxi Risks](https://docs.derive.xyz/docs/maxi-risks)
    * [BULL Strategy ](https://docs.derive.xyz/docs/bull-strategy)
    * [BULL Execution](https://docs.derive.xyz/docs/bull-execution)
    * [BULL Risks](https://docs.derive.xyz/docs/bull-risks)
    * [Vault Smart Contracts ](https://docs.derive.xyz/docs/vault-smart-contracts)
    * [Audits Vault Smart Contracts](https://docs.derive.xyz/docs/audits-vault-smart-contracts)
  * [DRV](https://docs.derive.xyz/docs/drv-1)
    * [DRV](https://docs.derive.xyz/docs/drv-1)
    * [ LYRA to DRV Migration](https://docs.derive.xyz/docs/lyra-to-drv-migration)
    * [DRV Token Launch](https://docs.derive.xyz/docs/drv-token-launch)
  * [Incentives & Rewards](https://docs.derive.xyz/docs/retail-trading-rewards-program-1)
    * [Retail Trading Rewards Program](https://docs.derive.xyz/docs/retail-trading-rewards-program-1)
  * [Migration](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome)
    * [Withdrawing LP from Camelot & Velodrome](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome)
    * [How to claim OP Rewards](https://docs.derive.xyz/docs/how-to-claim-op-rewards)
    * [Withdrawing Liquidity from V1 Vaults](https://docs.derive.xyz/docs/withdrawing-liquidity-from-v1-vaults)


Powered by [](https://readme.com?ref_src=hub&project=lyra-api)
# [Legacy] Portfolio Margin Parameters
This page documents the up to date values of all market specific parameters for the portfolio margin manager.
# 
Portfolio Margin Scenarios
[](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#portfolio-margin-scenarios)
These are the scenarios used when computing portfolio margin.  
| Scenario Number  | Spot Shock (%)  | Volatility Shock  |  
| --- | --- | --- |  
| 1  | +18%  | Up  |  
| 2  | +13.5%  | Up  |  
| 3  | +13.5%  | Static  |  
| 4  | +13.5%  | Down  |  
| 5  | +9%  | Up  |  
| 6  | +9%  | Static  |  
| 7  | +9%  | Down  |  
| 8  | +4.5%  | Up  |  
| 9  | +4.5%  | Static  |  
| 10  | +4.5%  | Down  |  
| 11  | +0%  | Up  |  
| 12  | +0%  | Static  |  
| 13  | +0%  | Down  |  
| 14  | -4.5%  | Up  |  
| 15  | -4.5%  | Static  |  
| 16  | -4.5%  | Down  |  
| 17  | -9%  | Up  |  
| 18  | -9%  | Static  |  
| 19  | -9%  | Down  |  
| 20  | -13.5%  | Up  |  
| 21  | -13.5%  | Static  |  
| 22  | -13.5%  | Down  |  
| 23  | -18%  | Up  |  
# 
Account Details
[](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#account-details)
These parameters govern the size and supported expiries of a PMRM subaccount.  
| Parameter  | Contract Variable  | ETH  | BTC  | Range  | Description  |  
| --- | --- | --- | --- | --- | --- |  
| `MAX_ACCOUNT_SIZE`  | `maxAccountSize`  | 128  | 128  | No bounds  | This is the maximum number of assets (options, cash, base, perpetuals) that can be supported by a single portfolio margined subaccount. This is constrained by gas requirements.  |  
| `MAX_EXPIRIES`  | `maxExpiries`  | 11  | 11  | No bounds  | This is the maximum number of unique expiries that can be held by a single portfolio margined subaccount.  |  
# 
Contingency Margin
[](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#contingency-margin)
These parameters govern various pieces of contingency margin which account for possibilities not encoded in the spot and IV shocks.  
| Parameter  | Contract Variable  | ETH  | BTC  | Range  | Description  |  
| --- | --- | --- | --- | --- | --- |  
| `PEG_FACTOR`  | `OtherContingencyParameters.pegLossFactor`  | 4.0  | 4.0  | [0.0, 20.0]  | Increases `IM_FACTOR `when USDC depegs beyond a threshold value.  |  
| `BASE_FACTOR`  | `OtherContingencyParameters.basePercent`  | 0.03  | 0.03  | [0.0, 1.0]  | This is used to compute the base contingency, simply a small percentage (given by `BASE_FACTOR`) of the spot price.  |  
| `PERP_FACTOR`  | `OtherContingencyParameters.perpPercent`  | 0.03  | 0.03  | [0.0, 1.0]  | This is used to compute the perp contingency, simply a small percentage (given by `PERP_FACTOR`) of the spot price.  |  
| `OPTION_FACTOR`  | `OtherContingencyParameters.optionPercent`  | 0.015  | 0.015  | [0.0, 1.0]  | A small percentage (`OPTION_FACTOR`) of the spot price is added per net short contract per strike to the asset contingency.  |  
# 
Volatility Shocks
[](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#volatility-shocks)
These parameters govern the shock IVs used when computing portfolio margin.  
| Parameter  | Contract Variable  | ETH  | BTC  | Range  | Description  |  
| --- | --- | --- | --- | --- | --- |  
| `VOL_RANGE (up)`  | `VolShockParameters.volRangeUp`  | 0.5  | 0.5  | [0.01, 2.0]  | Multiplicative scaling of the implied volatility when considering an increase  |  
| `VOL_RANGE (down)`  | `VolShockParameters.volRangeDown`  | 0.275  | 0.275  | [0.01, 1.0]  | Multiplicative scaling of the implied volatility when considering a decrease  |  
| `VEGA_POWER (< 30 DTE)`  | `VolShockParameters.shortTermPower`  | 0.3  | 0.3  | [0.0, 0.5]  | A power scaling of the multiplicative volatility shock (for short dated expiries).  |  
| `VEGA_POWER (> 30 DTE)`  | `VolShockParameters.longTermPower`  | 0.13  | 0.13  | [0.0, 0.5]  | A power scaling of the multiplicative volatility shock (for long dated expiries).  |  
| `DTE_FLOOR`  | `VolShockParameters.dteFloor`  | 1 day  | 1 day  | [0.01, 100] days  | A floor on the time-to-expiry used when computing the volatility shock. Avoids divergence arising from dividing by near 0 values.  |  
# 
Discounting
[](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#discounting)
These parameters govern how long sub-portfolios are discounted.  
| Parameter  | Contract Variable  | ETH  | BTC  | Range  | Description  |  
| --- | --- | --- | --- | --- | --- |  
| `RATE_PARAM_1`  | `MarginParameters.rateMultScale`  | 1.0  | 1.0  | [0.0, 5.0]  | Multiplicative scaling of the risk free rate used when computing the discounting for a long sub-portfolio.  |  
| `RATE_PARAM_2`  | `MarginParameters.rateAddScale`  | 0.12  | 0.12  | [0.0, 5.0]  | Additive scaling of the risk free rate used when computing the discounting for a long sub-portfolio.  |  
| `STATIC_SCALE`  | `MarginParameters.baseStaticDiscount`  | 0.95  | 0.95  | [0.0, 1.0]  | A flat scaling of the sub-portfolio's shocked marked value (only applies if positive).  |  
# 
Forward Contingency
[](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#forward-contingency)
These are parameters that govern the forward contingency. This accounts for forward basis movements against the trader.  
| Parameter  | Contract Variable  | ETH  | BTC  | Range  | Description  |  
| --- | --- | --- | --- | --- | --- |  
| `ADD_FACTOR`  | `BasisContingencyParameters.baseContAddFactor`  | 0.5  | 0.5  | [0,5.0]  | Additive scaling factor when computing the basis contingency  |  
| `MULT_FACTOR`  | `BasisContingencyParameters.basisContMultFactor`  | 2.0  | 2.0  | [0,5.0]  | Multiplicative scaling factor when computing the basis contingency.  |  
| `UP_SCENARIO_MOVE`  | `BasisContingencyParameters.scenarioSpotUp`  | Spot up 1.045 (IV static)  | Spot up 1.045 (IV static)  | N/A  | One of the spot shock scenarios used to compute the basis contingency.  |  
| `DOWN_SCENARIO_MOVE`  | `BasisContingencyParameters.scenarioSpotDown`  | Spot down to 0.955 (IV static)  | Spot down to 0.955 (IV static)  | N/A  | The other scenario used to compute the basis contingency.  |  
# 
Initial Margin and Oracle Contingency
[](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#initial-margin-and-oracle-contingency)
These govern how initial margin is typically defined, as well as circumstances where it may increase due to stable coin depeggings and/or low data confidence.  
| Parameter  | Contract Variable  | ETH  | BTC  | Range  | Description  |  
| --- | --- | --- | --- | --- | --- |  
| `IM_FACTOR`  | `MarginParameters.imFactor`  | 1.25  | 1.25  | [1.01, 4.0]  | This scales the `maxLoss` and `contingencies` when computing the initial margin for a portfolio margined subaccount.  |  
| `USDC_THRESHOLD`  | `OtherContingencyParameters.pegLossThreshold`  | 0.99  | 0.99  | [0.0, 1.05]  | Value of USDC beneath which the depeg contingency comes into effect.  |  
| `CONFIDENCE_THRESHOLD`  | `OtherContingencyParameters.confThreshold`  | 0.55  | 0.55  | [0.0, 1.0]  | Value of the confidence beneath which the relevant data is considered low confidence (thereby attracting additional initial margin).  |  
| `CONFIDENCE_SCALE`  | `OtherContingencyParameters.confMargin`  | 1.0  | 1.0  | [0, 2.0]  | Percentage of the spot price added when considering the oracle contingency.  |  
# 
Open Interest Caps
[](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#open-interest-caps)
Open interest caps on options, base and perpetual instruments.  
| Parameter  | Contract Variable  | ETH  | BTC  | Range  | Description  |  
| --- | --- | --- | --- | --- | --- |  
| `UNDERLYING_OI_CAP`  | `baseAsset.totalPositionCap`  | 750  | 15  | [0, no upper bound]  | Maximum open interest of the underlying asset.  |  
| `OPTION_OI_CAP`  | `option.totalPositionCap`  | 2000,000  | 100,000  | [0, no upper bound]  | Maximum open interest of options.  |  
| `PERP_OI_CAP`  | `perp.totalPositionCap`  | 250,000  | 12,000  | [0, no upper bound]  | Maximum open interest of perpetuals.  |  
# 
Fees
[](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#fees)
These are fees charged by the managers on the protocol layer.  
| Parameter  | Contract Variable  | ETH  | BTC  | Range  | Description  |  
| --- | --- | --- | --- | --- | --- |  
| `SPOT_FACTOR`  | `manager.OIFeeRateBPS`  | 0.70 (70%)  | 0.70 (70%)  | [0, 5.0]  | Percentage of the spot price charged when the trade increases the open interest.  |  
| `MIN_OI_FEE`  | `minOIFee`  | $800 USDC  | $800 USDC  | [0, 800]  | Minimum fee charged when open interest is increased.  |  
Updated 10 months ago
* * *
[Common Parameters](https://docs.derive.xyz/docs/common-parameters)[Standard Margin Parameters](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters)
Did this page help you?
Yes
No
Copy Page
  *     * [Portfolio Margin Scenarios](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#portfolio-margin-scenarios)
    * [Account Details](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#account-details)
    * [Contingency Margin](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#contingency-margin)
    * [Volatility Shocks](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#volatility-shocks)
    * [Discounting](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#discounting)
    * [Forward Contingency](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#forward-contingency)
    * [Initial Margin and Oracle Contingency](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#initial-margin-and-oracle-contingency)
    * [Open Interest Caps](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#open-interest-caps)
    * [Fees](https://docs.derive.xyz/docs/portfolio-margin-parameters-1#fees)
