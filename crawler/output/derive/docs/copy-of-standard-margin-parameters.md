---
protocol: "Derive"
title: "Standard Margin Parameters"
source: "https://docs.derive.xyz/docs/copy-of-standard-margin-parameters"
crawled_at: "2026-07-26T22:44:22+00:00"
---

# Standard Margin Parameters

For AI agents: visit https://docs.derive.xyz/llms.txt for an index of all pages formatted in Markdown and endpoints in OpenAPI.
[Jump to Content](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#content)
[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)v2-archive-03062026 v2-archive-09072026 v2-archive-20260724 v2-archive-22062026 v2-archive-30062026 v2.2
* * *
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/copy-of-standard-margin-parameters)[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
Documentation
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/copy-of-standard-margin-parameters)
v2.2
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)Standard Margin Parameters
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
# Standard Margin Parameters
This page documents the up to date values of all market specific parameters for the standard manager.
# 
Account Details
[](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#account-details)
These parameters govern the size of standard margin subaccounts and whether or not they can borrow against supported base assets.  
| Parameter  | Contract Variable  | Value  | Range  | Description  |  
| --- | --- | --- | --- | --- |  
| `BORROW_ENABLED`  | `borrowEnabled`  | TRUE  | [TRUE, FALSE]  | If TRUE, standard margined subaccounts can enter into a negative cash balance by borrowing against their base asset.  |  
| `maxAccountSize`  | `maxAccountSize`  | 48  | No bounds  | This represents the maximum number of assets (options, base asset, cash, perpetuals) that can be held by a single standard margined subaccount.  |  
# 
Delta-1 Margin Parameters
[](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#delta-1-margin-parameters)
These govern the margin requirements for delta-1 instruments (base assets and perpetual futures).  
| Parameter  | Contract Variable  | ETH  | BTC  | SOL  | HYPE  | ADA  | Range  | Description  |  
| --- | --- | --- | --- | --- | --- | --- | --- | --- |  
| `BASE_DISCOUNT`  | `baseMargin.marginFactor`  | 0.8  | 0.75  | NA  | 0.55  | (cbADA): 0.60  | [0.0, 0.99]  | Discount to the collateral provided by the base asset.  |  
| `BASE_DISCOUNT_SCALE`  | `baseMargin.IMFactor`  | 0.9375  | 0.93  | NA  | 0.9  | (cbADA): 0.50  | [0.0, .99]  | A scaling of BASE_DISCOUNT when computing the collateral provided by the base asset for initial margin.  |  
| `PERP_REQ_MM`  | `PerpMarginRequirements.mmPerpReq`  | 0.065  | 0.065  | 0.067  | 0.10  | 0.10  | [0.0, 1.0]  | The percentage of the spot price per perpetual contract required to be posted for maintenance margin.  |  
| `PERP_REQ_IM`  | `PerpMarginRequirements.imPerpReq`  | 0.10  | 0.10  | 0.33  | 0.15  | 0.15  | (0.0, 1.0]  | The percentage of the spot price per perpetual contract required to be posted for initial margin.  |  
# 
Isolated Option Margin Parameters
[](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#isolated-option-margin-parameters)
These parameters govern the margin requirement for isolated short option positions.  
| Parameter  | Contract Variable  | ETH/BTC  | SOL  | HYPE  | ADA  | Description  |  
| --- | --- | --- | --- | --- | --- | --- |  
| `SHORT_OPTION_IM_MAX`  | `OptionMarginParams.maxSpotReq`  | 0.15  | 0.24  | 0.3  | 0.35  |  The maximum percentage of the spot price required as additional initial margin for a short call/put. Examples provided at the end of [Standard Margin](https://docs.derive.xyz/docs/standard-margin).  |  
| `SHORT_OPTION_IM_MIN`  | `OptionMarginParmas.minSpotReq`  | 0.13  | 0.18  | 0.25  | 0.3  | The minimum percentage of the spot price required as additional initial margin for a short call/put.  |  
| `CALL_MM`  | `OptionMarginParmas.mmCallSpotReq`  | 0.09  | 0.14  | 0.18  | 0.2  | A constant percentage of the spot price required as additional maintenance margin for a short call.  |  
| `PUT_MM`  | `OptionMarginParmas.mmPutSpotReq`  | 0.09  | 0.14  | 0.18  | 0.2  | A constant percentage of the spot price required as additional maintenance margin for a short put.  |  
| `PUT_MTM`  | `OptionMarginParmas.mmPutMTMReq`  | 0.09  | 0.14  | 0.18  | 0.2  | A constant percentage of the put's mark-to-market value required as additional maintenance margin for a short put.  |  
| `MTM_OFFSET`  | `OptionMarginParams.mmOffsetScale`  | 1.05  | 1.05  | 1.05  | 1.05  | A scaling of the mark-to-market value of the put used to compute initial margin.  |  
# 
Spread Margin Parameters
[](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#spread-margin-parameters)
These parameters govern the margin requirements for sub-portfolios with naked short calls and spreads.  
| Parameter  | Contract Variable  | ETH/BTC  | SOL  | HYPE  | ADA  | Range  | Description  |  
| --- | --- | --- | --- | --- | --- | --- | --- |  
| `UNPAIRED_SCALE_IM`  | `OptionMarginParams.unpairedIMScale`  | 1.2  | 1.25  | 1.3  | 1.3  | [1.01, 3.0]  | A large percentage of the forward price per "naked" short call per expiry is added to the offset initial margin.  |  
| `UNPAIRED_SCALE_MM`  | `OptionMarginParams.unpairedMMScale`  | 1.1  | 1.2  | 1.25  | 1.25  | [1.01, 3.0]  | As above but for maintenance margin.  |  
# 
Stablecoin Margin Parameters
[](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#stablecoin-margin-parameters)
These control the extra initial margin requirements when USDC (the designated cash asset) depegs.  
| Parameter  | Contract Variable  | ETH/BTC/SOL/HYPE/ADA  | Range  | Description  |  
| --- | --- | --- | --- | --- |  
| `DEPEG_FACTOR`  | `DepegParams.depegFactor`  | 2.0  | [0, 10]  | Each short option and perpetual held by the subaccount attracts extra initial margin that scales with `DEPEG_FACTOR` and the difference between the USDC price and a given threshold.  |  
| `USDC_THRESHOLD`  | `DepegParams.threshold`  | 0.99  | [0.0, 1.05]  | Value of USDC beneath which extra depeg contingency will begin to be added.  |  
# 
Confidence Margin Parameters
[](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#confidence-margin-parameters)
These control the extra initial margin requirements when any of the data feeds have low confidence.  
| Parameter  | Contract Variable  | ETH  | BTC  | SOL  | HYPE  | ADA  | Range  | Description  |  
| --- | --- | --- | --- | --- | --- | --- | --- | --- |  
| `CONFIDENCE_SCALE`  | `OracleContingencyParams.OCFactor`  | 1.0  | 1.0  | 1.0  | 1.0  | 1.0  | [0, 2.0]  | Percentage of the spot price per short option, base or perpetual contract added to the initial margin requirements.  |  
| `THRESHOLD_CONFIDENCE`  | `OracleContingencyParams.perpThreshold OracleContingencyParams.optionThreshold OracleContingencyParams.baseThreshold`  | 0.55  | 0.55  | 0.55  | 0.55  | 0.55  | [0, 1.0]  | Value of the confidence beneath which extra IM is added.  |  
# 
Open Interest Caps
[](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#open-interest-caps)
Open interest caps on options, base and perpetual instruments.  
| Parameter  | Contract Variable  | ETH  | BTC  | SOL  | Range  | Description  |  
| --- | --- | --- | --- | --- | --- | --- |  
| `UNDERLYING_OI_CAP`  | `baseAsset.totalPositionCap`  | 250  | 5  | NA  | [0, no upper bound]  | Maximum open interest of the underlying asset.  |  
| `OPTION_OI_CAP`  | `option.totalPositionCap`  | 2,000,000  | 100,000  | NA  | [0, no upper bound]  | Maximum open interest of options.  |  
| `PERP_OI_CAP`  | `perp.totalPositionCap`  | 250,000  | 12,000  | 8000  | [0, no upper bound]  | Maximum open interest of perpetuals.  |  
# 
Fees
[](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#fees)
These are fees charged by the managers on the protocol layer.  
| Parameter  | Contract Variable  | ETH  | BTC  | SOL  | DOGE  | Range  | Description  |  
| --- | --- | --- | --- | --- | --- | --- | --- |  
| `SPOT_FACTOR`  | `manager.OIFeeRateBPS`  | 0.7 (70%)  | 0.7 (70%)  | 0.7 (70%)  | 0.7 (70%)  | [0, 5.0]  | Percentage of the spot price charged when the trade increases the open interest.  |  
| `MIN_OI_FEE`  | `minOIFee`  | $800 USDC  | $800 USDC  | $800 USDC  | $800 USDC  | [0, 10,000]  | Minimum fee charged when open interest is increased.  |  
Updated 3 months ago
* * *
[[Legacy] Portfolio Margin Parameters](https://docs.derive.xyz/docs/portfolio-margin-parameters-1)[Portfolio Manager](https://docs.derive.xyz/docs/copy-of-portfolio-manager-new)
Did this page help you?
Yes
No
Copy Page
  *     * [Account Details](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#account-details)
    * [Delta-1 Margin Parameters](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#delta-1-margin-parameters)
    * [Isolated Option Margin Parameters](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#isolated-option-margin-parameters)
    * [Spread Margin Parameters](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#spread-margin-parameters)
    * [Stablecoin Margin Parameters](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#stablecoin-margin-parameters)
    * [Confidence Margin Parameters](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#confidence-margin-parameters)
    * [Open Interest Caps](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#open-interest-caps)
    * [Fees](https://docs.derive.xyz/docs/copy-of-standard-margin-parameters#fees)
