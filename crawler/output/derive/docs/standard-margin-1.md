---
protocol: "Derive"
title: "Standard Margin"
source: "https://docs.derive.xyz/docs/standard-margin-1"
crawled_at: "2026-07-26T22:45:23+00:00"
---

# Standard Margin

For AI agents: visit https://docs.derive.xyz/llms.txt for an index of all pages formatted in Markdown and endpoints in OpenAPI.
[Jump to Content](https://docs.derive.xyz/docs/standard-margin-1#content)
[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)v2-archive-03062026 v2-archive-09072026 v2-archive-20260724 v2-archive-22062026 v2-archive-30062026 v2.2
* * *
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/standard-margin-1)[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
Documentation
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/standard-margin-1)
v2.2
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)Standard Margin
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
# Standard Margin
Standard margin evaluates each position’s margin in isolation, with the exception of spreads whose margin requirements can be offset for the same expiry. It is the default margin option for traders.
If a standard margin sub-acccount falls below its maintenance margin requirement, the account will be liquidated. See [Liquidations](https://docs.derive.xyz/reference/liquidations) for more details.
# 
Margin Calculation
[](https://docs.derive.xyz/docs/standard-margin-1#margin-calculation)
The standard margin requirement is calculated by summing an account’s margin requirement for its perpetual and option positions and then adding the value of its USDC balance and base assets (with haircut). For each market, the margin is calculated as follows:
Formula

```


InitialMargin=USDCBalance+BaseCollateral+PerpMargin+OptionMargin+DepegContingency+OracleContingencyMaintenanceMargin=USDCBalance+BaseCollateral+PerpMargin+OptionMargin


```

Where:
  * `Perp Margin` is the margin requirement for all perpetuals in the account, calculated as a simple percentage of the underlying’s spot price. The profit and loss of said perpetuals, as well as owe/owing funding is included in this value.
  * `Option Margin` is the margin requirement for all options in the account, typically calculated as the sum of isolated margin for each option, with the possibility for margin offsets for spreads and other multi-legged strategies within the same expiry.
  * `Depeg Contingency` is extra initial margin conditionally required to protect against USDC depegging.
  * `Oracle Contingency` is extra initial margin conditionally required to protect against inaccurate oracle data feeds.
  * `USDC Balance` is the subaccount's balance of USDC (which can be positive or negative)
  * `Base Collateral` is the value of the base asset held in the subaccount (with a risk based haircut).


Each margin component has slightly greater initial margin requirements compared to maintenance margin requirements. This is applied via parameterization. Read the sections below for more details.
Both initial and maintenance margin are centred around zero. I.e. a sub-account is subject to liquidation if its `Maintenance Margin` is negative (see [Liquidations](https://docs.derive.xyz/liquidations.md) for more details) and a sub-account is only able to open a new position if its final `Initial Margin` is positive. See the end of this page for more detail on this and risk reducing trades.
> 📘
> ### 
> Depeg and Oracle Contingencies are typically zero and only add to initial margin requirements, i.e. they do not change margin requirements for already open positions, but may block opening new positions.
> [](https://docs.derive.xyz/docs/standard-margin-1#depeg-and-oracle-contingencies-are-typically-zero-and-only-add-to-initial-margin-requirements-ie-they-do-not-change-margin-requirements-for-already-open-positions-but-may-block-opening-new-positions)
## 
Base Collateral
[](https://docs.derive.xyz/docs/standard-margin-1#base-collateral)
Base Collateral which is simply the sum of the value of each base asset, multiplied by a risk based haircut.
Formula

```


CollateralMM=ΣBaseₘ*BASE_DISCOUNTₘ*SpotₘCollateralIM=ΣBaseₘ*BASE_DISCOUNTₘ*BASE_SCALEₘ*Spotₘ


```

Where:
  * `Baseₘ` is the account’s balance of base asset `m`.
  * `BASE_DISCOUNTₘ` is the discount factor for base asset `m` (0.8 for ETH and 0.75 for BTC).
  * `BASE_DISCOUNT_SCALEₘ` is a scale factor less than 1 used when computing the collateral value of the base asset in initial margin calculations (0.9375 for ETH, 0.93 for BTC).
  * `Spotₘ` is the spot price of base asset `m`.


## 
Perpetuals Margin
[](https://docs.derive.xyz/docs/standard-margin-1#perpetuals-margin)
All perpetuals have margin requirements proportional to the perpetual price. This percentage is larger when computing initial margin:
Formula

```


InitialPerpetualMargin=-absSize*0.10*PerpetualPriceMaintenancePerpetualMargin=-absSize*0.065*PerpetualPrice


```

Where:
  * `Size` is the number of perpetual contracts (this number is negative for shorts).
  * `Perpetual Price` is the mark price of the perpetual.


## 
Option Margin
[](https://docs.derive.xyz/docs/standard-margin-1#option-margin)
Options are typically margined in isolation, with the exception of spreads and multi-legged strategies whose margin requirements can be offset for the same expiry.
The option margin for an account is the sum of each expiry’s margin, which is calculated by grouping positions per expiry, summing their isolated margin and offsetting spreads and multi-legged strategies where possible.
Options with different underlyings (ETH, BTC) are margined separately and then added together. I.e. the option margin of all ETH options is found, then added to that for all BTC options to get the total option margin for the subaccount. In the following, we focus on computing the option margin for a single underlying; the option margin for a subaccount with multiple underlyings is easily found given this.
### 
Isolated Margin
[](https://docs.derive.xyz/docs/standard-margin-1#isolated-margin)
The isolated margin of an option for strike price `j` is calculated as follows:
For long calls and puts:
Formula

```


InitialIsolatedOptionMarginⱼ=NoneMaintenanceIsolatedOptionMarginⱼ=None


```

For short calls:
Formula

```


InitialIsolatedOptionMarginⱼ=n*-max0.15-OTMⱼ/Spot0.13*Spot+MarkPriceⱼMaintenanceIsolatedOptionMarginⱼ=n*-0.09*Spot+MarkPriceⱼ


```

For short puts:
Formula

```


InitialMarginⱼ=n*-maxmax0.15-OTMⱼ/Spot0.13*Spot-MarkPriceⱼ-1.05xMaintenanceMarginⱼMaintenanceMarginⱼ=n*-max0.09*-MarkPriceⱼ0.09*Spot+MarkPriceⱼ


```

Where:
  * `n` is the number of short options held
  * `OTM` is the out-the-money amount. For calls, `OTM = max(0, Strike - Spot)` and for puts, `OTM = max(0, Spot - Strike).`
  * `Spot` is the spot price of the underlying base asset.
  * `Mark Price` is the mark-to-market value of the option calculated using [Black76](https://en.wikipedia.org/wiki/Black_model) with no discounting. Since the option is short, this is a negative quantity.


Note
### 
Expiry Margin
[](https://docs.derive.xyz/docs/standard-margin-1#expiry-margin)
The default margin of expiry `i` is calculated by summing the isolated margin of each option in the account for that expiry:
Formula

```


DefaultInitialMarginᵢ=ΣInitialMarginⱼDefaultMaintenanceMarginᵢ=ΣMaintenanceMarginⱼ


```

We also compute an offset margin for expiry `i` to offset spreads and other multi-legged strategies. This is made up of 2 components:
  1. The minimum intrinsic value of the expiry’s options evaluated at all strikes in with this expiry (including the zero strike).
  2. A percentage of the expiry's forward price multiplied by the number of "naked" short calls in the expiry.


Note
Formula

```


NakedShortCallSize=-maxNumberofShortCalls-NumberofLongCalls0


```

For example, if an expiry has 3 short calls on the $1600 strike and 2 long calls on the $1800 strike, then Naked Short Call Size is simply -1. Combining all of this, we have
Formula

```


OffsetInitialMarginᵢ=minIntrinsicValueᵢ0+UNPAIRED_SCALE_IM*NakedShortCallSizeᵢ*ForwardPriceᵢOffsetMaintenanceMarginᵢ=minIntrinsicValueᵢ0+UNPAIRED_SCALE_MM*NakedShortCallSizeᵢ*ForwardPriceᵢ


```

Where:
  * `Intrinsic Valueᵢ` is the intrinsic value of all options in the expiry evaluated at each strike `k` for expiry `i` (including the zero strike).
  * `Short Call Sizeᵢ` is the number of naked short call contracts open in the expiry `i`.
  * `Forward Priceᵢ` is the forward price for the expiry `i`.
  * `UNPAIRED_SCALE_IM = 1.2` scales naked short calls for initial margin requirements.
  * `UNPAIRED_SCALE_MM = 1.1` scales naked short calls for maintenance margin requirements.


The final margin for expiry `i` is then the better (larger) of the default expiry margin and offset expiry margin:
Formula

```


InitialMarginᵢ=maxDefaultInitialMarginᵢOffsetInitialMarginᵢMaintenanceMarginᵢ=maxDefaultMaintenanceMarginᵢOffsetInitialMarginᵢ


```

Note that both `Default Initial Margin` and `Offset Initial Margin` are negative, so the above takes the more lenient margin requirements for the trader.
### 
Total Margin
[](https://docs.derive.xyz/docs/standard-margin-1#total-margin)
Finally, the total option margin for an account is the sum of each expiry’s margin:
Formula

```


OptionInitialMargin=ΣInitialMarginᵢOptionMaintenanceMargin=ΣMaintenanceMarginᵢ


```

## 
Depeg Contingency
[](https://docs.derive.xyz/docs/standard-margin-1#depeg-contingency)
When USDC depegs from $1, additional initial margin requirements are added:
Formula

```


DepegContingency=-max0USDC_THRESHOLD-USDCValue*Spot*DEPEG_FACTOR*ΣShortOptionSizeⱼ+absPerpSize


```

Where:
  * `USDC Value` is the market value of USDC.
  * `Spot` is the spot price of the underlying base asset.
  * `Short Option Sizeⱼ` is the absolute number of contracts for a short option with strike `j` in the account.
  * `Perp Size` is the number of perpetual contracts (this number is negative for shorts).
  * `USDC_THRESHOLD = 0.99` is the threshold value of USDC that triggers a depegging event.
  * `DEPEG_FACTOR = 2.0` scales the depeg contingency.


Note that this is the depeg contingency for a given underlying (say, ETH). For multiple underlying assets, the relevant asset's spot and corresponding subaccount positions are used.
> 📘
> ### 
> When the USDC value (reported by oracle data feeds) is greater than the depegging threshold, the depeg margin requirement is $0.
> [](https://docs.derive.xyz/docs/standard-margin-1#when-the-usdc-value-reported-by-oracle-data-feeds-is-greater-than-the-depegging-threshold-the-depeg-margin-requirement-is-0)
## 
Oracle Contingency
[](https://docs.derive.xyz/docs/standard-margin-1#oracle-contingency)
Associated to each oracle data feed is a confidence score; a metric for the feed's reliability and accuracy. When confidence scores are below a given threshold, this indicates the data feeds could be feeding inaccurate price data into the system, and the protocol automatically introduces additional initial margin requirements. Learn more about oracle data feeds [here](https://docs.derive.xyz/oracles.md).
The oracle contingency is the sum of base, perpetual and option oracle contingencies:
Formula

```


BaseOracleContingency=-CONFIDENCE_SCALE_SM*BaseBalance*Spot*1-SpotConfidenceifSpotConfidence<BASE_CONF_THRESHOLDotherwise0


```

Formula

```


PerpOracleContingency=-CONFIDENCE_SCALE_SM*absPerpSize*Spot*1-minSpotConfidencePerpConfidenceifminSpotConfidencePerpConfidence<PERP_CONF_THRESHOLDotherwise0


```

Formula

```


OptionOracleContingency=-CONFIDENCE_SCALE_SM*absShortOptionsSize*Spot*1-minSpotConfidenceForwardConfidenceVolConfidenceifminSpotConfidenceForwardConfidenceVolConfidence<OPTION_CONF_THRESHOLDotherwise0


```

I.e.
Formula

```


OracleContingency=Base+Perp+OptionOracleContingencies


```

Where:
  * `CONFIDENCE_SCALE_SM = 1.0` is a constant scaling factor.
  * `Short Options Size` is the number of short options contracts for the relevant feeds.
  * `Perp Size` is the number of perpetual contracts open in the account.
  * `Spot Confidence` is confidence score of the spot price data.
  * `Forward Confidence` is confidence score of the forward data.
  * `Vol Confidence` is confidence of the implied volatility data.
  * `Perp Confidence` is confidence of the perpetual price data.
  * `BASE_CONF_THRESHOLD = PERP_CONF_THRESHOLD = OPTION_CONF_THRESHOLD = 0.55` represent the thresholds after which extra initial margin is added due to low confidence.


## 
Open Interest Caps
[](https://docs.derive.xyz/docs/standard-margin-1#open-interest-caps)
The standard manager has a cap on the open interest of all instruments it supports. Namely:
  * (ETH, BTC) = (250, 5) base asset
  * (ETH, BTC) = (2,000,000, 100,000) options
  * (ETH, BTC) = (250,000, 12,000) perpetual contracts


These bounds can be adjusted as necessary over time. A low amount of base asset is set due to limited functionality of this instrument at launch. This will be raised when a spot market is available.
# 
Risk Reducing Trades and Risk Assessors
[](https://docs.derive.xyz/docs/standard-margin-1#risk-reducing-trades-and-risk-assessors)
On the smart contract level, the standard risk manager will allow any trade to be conducted so long as it satisfies either of the following conditions:
  * the initial margin of the portfolio after the transaction is conducted is positive (`IM(post) > 0`) OR
  * the trade is risk reducing


To clarify the last point, we say a trade is risk reducing
  * Adds a long option
  * Adds a positive amount of the cash asset (USDC)
  * Adds base collateral
  * Closes a perpetual


It is highly desirable to always allow users to be able to close risky positions. For example, suppose a trader has a short ETH $1700 call with $300 of USDC as collateral. Perhaps the trader wishes to de-risk and buy back 0.5 of this call with some of their USDC.
On the smart contract layer, this transaction does not satisfy the second condition (since cash will be taken from the account to buy back the option). Further, if the option is sufficiently risky, there is no guarantee that the first condition will be satisfied either. This is problematic, since the above conditions would otherwise prohibit users from de-risking their portfolios.
This motivates the existence of risk assessors (RAs)[portfolio margin](https://v2-docs.lyra.finance/docs/portfolio-margin)) and/or allow certain trades not normally allowed by the managers.
Specifically for the standard manager, the risk assessor will have special logic to always allow users to close risky (i.e. short) positions. On-chain, the managers will always verify that all accounts have positive maintenance margin.
This means that a malicious risk assessor can never open liquidatable (nor insolvent) positions
The worst that such a nefarious entity can do is refuse to permit users from closing risky positions (short options, etc) (but this can still be done permissionlessly on-chain).
# 
Examples
[](https://docs.derive.xyz/docs/standard-margin-1#examples)
## 
Example 1: A simple short call
[](https://docs.derive.xyz/docs/standard-margin-1#example-1-a-simple-short-call)
ETH is trading at $1900.
Account:
  * $2000 of USDC
  * 3.0 short ETH $1800 calls expiring in 3 weeks, mark price $120 per call.


We have:
Formula

```


USDCBalance=2000


```

Since ETH is at $1900, we have `OTM = max(0,1800-1900)=0`.
Formula

```


InitialMarginshortcalls=3*-max0.15-0/19000.13*1900-120=-$1215MaintenanceMarginshortcalls=3*-0.09*1900-120=-$873


```

Thus:
Formula

```


InitialMargin=-1215+2000=$785MaintenanceMarginshortcalls=$1127


```

Since both the maintenance and initial margin are positive, the subaccount is not liquidatable and new positions may be added.
## 
Example 2: Spread Logic
[](https://docs.derive.xyz/docs/standard-margin-1#example-2-spread-logic)
Account:
  * $2000 of USDC
  * 8 x SHORT $1700 ETH calls expiring in 2 weeks
  * 8 x LONG $1900 ETH calls expiring in 2 weeks


Assume that ETH is trading at $2100 and the 2 weekly forward at $2105.
Let’s begin by computing the default margin.
Formula

```


DefaultMargin=marginSHORT1700call+marginLONG1900call


```

Since long options contribute nothing to the default margin, we only have to compute the margin of the short $1700 call.
Assuming a 0% interest rate and an implied volatility of 92.5%. Then the mark price of the $1700 call is $425. We have:
Formula

```


DefaultInitialMargin=8*-max0.15-0/21000.13*2100-425=-5920DefaultMaintenanceMargin=8*-0.09*2100-425=-4912


```

Next, we compute the offset margin. In the 2 week expiry there are 8 long calls and 8 short calls; thus, there are no naked calls. We compute the intrinsic value at all relevant strikes (0, $1700, $1900) in the table below:  
| Strike  | Intrinsic Value  |  
| --- | --- |  
| $0  | 0  |  
| $1700  | 0  |  
| $1900  | -$1600  |  
Thus, we have
Formula

```


OffsetMargin=-1600


```

Finally,
Formula

```


InitialOptionMarginᵢ=max-5920-1600=-1600MaintenanceOptionMarginᵢ=max-4912-1600=-1600


```

and so both the initial and maintenance option margin are -$1600. We thus have
Formula

```


InitialMargin=-1600+2000=+400MaintenanceMargin=-1600+2000=+400


```

## 
Example 3: Multi Asset Account
[](https://docs.derive.xyz/docs/standard-margin-1#example-3-multi-asset-account)
Account:
  * $25000 USDC
  * 8 x SHORT $1700 ETH calls expiring in 2 weeks
  * 8 x LONG $1900 ETH calls expiring in 2 weeks
  * 7 x LONG BTC perpetuals (with no unrealized PNL or funding)


Assume that ETH is trading at $2100 (as in the above example with 2 weekly forward at $2105) and BTC (and its perpetual) are trading at $28,000.
Using the above example, we know
Formula

```


InitialOptionMarginETH=-1600MaintenanceOptionMarginETH=-1600


```

To find the same quantities for BTC, we know
Formula

```


InitialMarginBTCPerp=-7*0.10*28000=-19600MaintenanceMarginBTCPerp=-7*0.065*28000=-12740


```

Thus, the total margin requirements for the account are:
Formula

```


InitialMargin=25000+-1600+-19600=3800MaintenanceMargin=25000+-1600+-12740=10660


```

## 
Example 4: General Case
[](https://docs.derive.xyz/docs/standard-margin-1#example-4-general-case)
Consider the same subaccount as in example 3, but now assume:
  * The confidence of the BTC perp feed decreases to 0.50 (below the threshold of 0.55) and
  * The market price of USDC depegs to $0.7.


Let’s now compute the confidence and depeg margins. We have
Formula

```


PerpConfidenceMarginBTC=-1.0*7*28000*1-0.5=-98000


```

For depeg margin, we have
Formula

```


DepegMarginETH=-Max00.99-0.7*2100*2.0*8=-9744DepegMarginBTC=-Max00.99-0.7*28000*2.0*7=-113680


```

So the margin requirements of the subaccount become
Formula

```


InitialMargin=25000+-1600+-19600+-98000+-9744+-113680=-217624MaintenanceMargin=25000+-1600+-12740=10660


```

Updated 10 months ago
* * *
[Supported Products](https://docs.derive.xyz/docs/supported-products-1)[Portfolio Margin](https://docs.derive.xyz/docs/portfolio-margin-1)
Did this page help you?
Yes
No
Copy Page
  *     * [Margin Calculation](https://docs.derive.xyz/docs/standard-margin-1#margin-calculation)
    *       * [Base Collateral](https://docs.derive.xyz/docs/standard-margin-1#base-collateral)
      * [Perpetuals Margin](https://docs.derive.xyz/docs/standard-margin-1#perpetuals-margin)
      * [Option Margin](https://docs.derive.xyz/docs/standard-margin-1#option-margin)
      * [Depeg Contingency](https://docs.derive.xyz/docs/standard-margin-1#depeg-contingency)
      * [Oracle Contingency](https://docs.derive.xyz/docs/standard-margin-1#oracle-contingency)
      * [Open Interest Caps](https://docs.derive.xyz/docs/standard-margin-1#open-interest-caps)
    * [Risk Reducing Trades and Risk Assessors](https://docs.derive.xyz/docs/standard-margin-1#risk-reducing-trades-and-risk-assessors)
    * [Examples](https://docs.derive.xyz/docs/standard-margin-1#examples)
    *       * [Example 1: A simple short call](https://docs.derive.xyz/docs/standard-margin-1#example-1-a-simple-short-call)
      * [Example 2: Spread Logic](https://docs.derive.xyz/docs/standard-margin-1#example-2-spread-logic)
      * [Example 3: Multi Asset Account](https://docs.derive.xyz/docs/standard-margin-1#example-3-multi-asset-account)
      * [Example 4: General Case](https://docs.derive.xyz/docs/standard-margin-1#example-4-general-case)
