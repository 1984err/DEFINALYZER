---
protocol: "Derive"
title: "Portfolio Margin"
source: "https://docs.derive.xyz/docs/portfolio-margin-1"
crawled_at: "2026-07-26T22:45:06+00:00"
---

# Portfolio Margin

For AI agents: visit https://docs.derive.xyz/llms.txt for an index of all pages formatted in Markdown and endpoints in OpenAPI.
[Jump to Content](https://docs.derive.xyz/docs/portfolio-margin-1#content)
[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)v2-archive-03062026 v2-archive-09072026 v2-archive-20260724 v2-archive-22062026 v2-archive-30062026 v2.2
* * *
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/portfolio-margin-1)[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
Documentation
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/portfolio-margin-1)
v2.2
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)Portfolio Margin
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
# Portfolio Margin
To compute portfolio margin, the portfolio is first evaluated at various forward and volatility shocks and the greatest market loss is selected. Extra contingency margin is added to account for risk factors not captured by the shocks. Compared to standard margin, this can substantially reduce a portfolio’s margin requirement.
However, portfolio margin does not support cross-market margin, meaning each portfolio margin account can only support derivates/base asset corresponding to one underlying asset which we call the denominated base asset
If a portfolio margin account's collateral falls below its maintenance margin requirement, the account will be liquidated. See [Liquidations](https://docs.derive.xyz/reference/liquidations) for more details.
> 📘
> ### 
> Portfolio margin does not support cross-market margin, meaning unlike standard margin, there is only one denominated base asset that can be used as collateral in a portfolio.
> [](https://docs.derive.xyz/docs/portfolio-margin-1#portfolio-margin-does-not-support-cross-market-margin-meaning-unlike-standard-margin-there-is-only-one-denominated-base-asset-that-can-be-used-as-collateral-in-a-portfolio)
# 
Margin Calculation
[](https://docs.derive.xyz/docs/portfolio-margin-1#margin-calculation)
A user's initial and maintenance margin requirements are calculated as follows.
Formula

```


InitialMargin=PortfolioMtM++mfactor+DepegContingency*minmaxLossForwardContingency+AssetContingency+OracleContingencyMaintenanceMargin=PortfolioMtM++minmaxLossForwardContingency+AssetContingency


```

Where:
  * `Portfolio MtM` is the mark-to-market value of the portfolio (includes all perpetual funding/PNL). This includes the account's USDC balance and all base assets (marked to their current value). Note options are marked with a discounting of 1.0.
  * `mFactor = 1.25` is a scaling of the maximum loss and associated contingencies used to compute initial margin.
  * `Depeg Contingency` is extra initial margin conditionally required to protect against USDC depegging.
  * `maxLoss` is the maximum loss the portfolio will endure under 23 scenarios comprised of various forward and volatility shocks.
  * `Forward Contingency` accounts for the forward basis for each expiry moving unfavourably against the trader.
  * `Asset Contingency` is extra margin applied to options, perpetual and base assets held in the account.
  * `Oracle Contingency` is extra initial margin conditionally required to protect against inaccurate oracle data feeds.


> 📘
> ### 
> Oracle Contingencies are typically zero and only add to initial margin requirements, i.e. they do not change margin requirements for already open positions, but may block opening new positions.
> [](https://docs.derive.xyz/docs/portfolio-margin-1#oracle-contingencies-are-typically-zero-and-only-add-to-initial-margin-requirements-ie-they-do-not-change-margin-requirements-for-already-open-positions-but-may-block-opening-new-positions)
As described in [Standard Margin](https://docs.derive.xyz/docs/standard-margin), an account is subject to liquidation if `Maintenance Margin` falls beneath 0 and can only open new positions if the final state has `Initial Margin` above 0.
## 
maxLoss
[](https://docs.derive.xyz/docs/portfolio-margin-1#maxloss)
To compute `maxLoss`, the portfolio’s options, perpetual and base assets are evaluated under 23 forward and volatility shocks. The largest loss is set to `maxLoss` and potentially used to define the account's margin requirement.
The scenarios are comprised of all spot shocks from -18% to +18%, increasing in steps of 4.5%. Up/down/static vol shocks for all scenarios between (and inclusive of) -13.5% and +13.5%. Only volatility increasing scenarios are used for +18% and -18%. See [Portfolio Margin Parameters](https://docs.derive.xyz/docs/portfolio-margin-parameters) for an explicit table.
The magnitude of these shocks is explained below.
### 
Shocked Base Value
[](https://docs.derive.xyz/docs/portfolio-margin-1#shocked-base-value)
The account’s base collateral value is shocked by a constant factor under scenario `k`:
Formula

```


ShockedBaseValueₖ=Base*1+SpotShockₖ*Spot


```

Where:
  * `Base` is the balance of the account's denominated base asset.
  * `Spot Shockₖ` is the shock to the spot price for scenario `k`.
  * `Spot` is the spot price of the underlying base asset.


### 
Shocked Perpetual Value
[](https://docs.derive.xyz/docs/portfolio-margin-1#shocked-perpetual-value)
The account’s perpetual position value is shocked by a constant factor under scenario `k`:
Formula

```


ShockedPerpValueₖ=PerpPosition*1+SpotShockₖ*PerpPrice


```

Where:
  * `Perp Position` is the number of perpetual contracts (this number is negative for shorts).
  * `Spot Shockₖ` is the shock to the spot price for scenario `k`.
  * `Perp Price` is the mark-to-market value of the perpetual.


### 
Shocked Option Value
[](https://docs.derive.xyz/docs/portfolio-margin-1#shocked-option-value)
The account’s option positions are grouped and shocked per expiry. Each expiry `i` is evaluated for a given shock scenario `k`. The shocked value for an expiry `i` is the value of each option position with strike price `j` calculated with shocked forward and volatility values.
The forward is shocked to:
Formula

```


ShockedForwardᵢₖ=Forwardᵢ*1+SpotShockₖ


```

Where:
  * `Forwardᵢ` is the forward price of expiry `i`.
  * `Spot Shockₖ` is the shock multiplier for scenario `k`.


The IV shock is multiplicative. The magnitude of the shock depends on time to expiry and whether or not the shock is positive or negative. We have:
Formula

```


ShockedIVⱼₖ=IVShockₖ*IVⱼIVShockₖ=1+VOL_RANGE*30/365/max1/365TimeToExpiryᵢ**VEGA_POWER


```

Where:
  * `IV` is the implied volatility of strike `j`.
  * `Time To Expiry` is the number of years until expiry.
  * `VOL_RANGE = -0.275` if IV is being shocked down.
  * `VOL_RANGE = 0.5` if IV is being shocked up.
  * `VEGA_POWER = 0.3` if time to expiry < 30 days.
  * `VEGA_POWER = 0.13` if time to expiry > 30 days.


A discount is applied to the options expiry when its net value is positive (else it defaults to 1.0):
Formula

```


Discountᵢₖ=ExpiryValue>0exp-InterestRateᵢ*RATE_PARAM_1+RATE_PARAM_2*TimeToExpiry*STATIC_SCALEExpiryValue<01.0


```

Where:
  * `Interest Rate` is the risk free rate for an expiry.
  * `Time To Expiry` is the number of years until expiry.
  * `RATE_PARAM_1 = 1.0`.
  * `RATE_PARAM_2 = 0.12`.
  * `STATIC_SCALE = 0.95`.


Finally, an expiry group’s shocked value is calculated by summing the mark-to-market value of each option for an expiry using [Black76](https://en.wikipedia.org/wiki/Black_model), with the applied discount:
Formula

```


ShockedExpiryValueᵢₖ=ΣShockedOptionValueⱼₖxDiscountᵢₖ


```

### 
Scenario Analysis
[](https://docs.derive.xyz/docs/portfolio-margin-1#scenario-analysis)
The portfolio’s loss under scenario `k` is then the sum of perpetual, base and each expiry’s value minus its shocked value:
Formula

```


PortfolioValue=BaseValue+PerpValue+ΣExpiryValueᵢPortfolioShockedValueₖ=ShockedBaseValueₖ+ShockedPerpValueₖ+ΣShockedExpiryValueᵢₖPortfolioLossₖ=PortfolioShockedValueₖ-PortfolioValue


```

Where:
  * `Base Value` is the mark value of the account's base balance.
  * `Perp Value` is the mark value of the account's perpetual position.
  * `Expiry Valueᵢ` is the mark-to-market value of the account's option positions with expiry `i`.
  * `Shocked Base Valueₖ` is the shocked value of the account's base balance for scenario `k`
  * `Shocked Perp Valueₖ` is the shocked value of the account's perpetual position for scenario `k`
  * `Shocked Expiry Valueᵢₖ` is the shocked mark-to-market value of the account's option positions with expiry `i` under shock scenario `k`


maxLoss is then the smallest (i.e. most negative) portfolio loss under all 23 scenarios:
tsx

```

maxLoss = min(Portfolio Loss(1), Portfolio Loss(2), ..., Portfolio Loss(23))

```

## 
Forward Contingency
[](https://docs.derive.xyz/docs/portfolio-margin-1#forward-contingency)
The forward contingency accounts for the forward basis for an account’s options moving unfavourably against the trader.
We consider an up and down scenario where spot goes up or down 5%. For each expiry `i`, we calculate the basis loss, or the max loss of the up and down scenario for each expiry’s option positions:
Formula

```


BasisLossᵢ=minmin0UpExpiryValueᵢ-ExpiryValueᵢmin0DownExpiryValueᵢ-ExpiryValueᵢ


```

Where:
  * `Expiry Valueᵢ` is the mark-to-market value of positions in expiry `i`.
  * `Up Expiry Valueᵢ` is the mark-to-market value of positions in expiry `i` under the up scenario (5% increase in spot).
  * `Down Expiry Valueᵢ` is the mark-to-market value of positions in expiry `i` under the down scenario (5% decrease in spot).


The forward contingency is then the sum of each expiry’s basis loss:
Formula

```


ForwardContingency=ΣADD_FACTOR+MULT_FACTOR*TimeToExpiryᵢ*BasisLossᵢ


```

Where:
  * `ADD_FACTOR = 0.5`
  * `MULT_FACTOR = 2.0`.
  * `Time To Expiryᵢ` is the number of years until expiry.


## 
Asset Contingency
[](https://docs.derive.xyz/docs/portfolio-margin-1#asset-contingency)
Asset contingency is three small components of margin required for base, perpetual and option positions held in the account:
Formula

```


AssetContingency=BaseContingency+PerpContingency+OptionContingency


```

### 
Base Contingency
[](https://docs.derive.xyz/docs/portfolio-margin-1#base-contingency)
The account's base asset has a small margin associated with it, based on the base balance and spot price.
Formula

```


BaseContingency=-Base*BASE_FACTOR*Spot


```

Where:
  * `Base` is the balance of the account's denominated base asset.
  * `Spot` is the spot price of the underlying base asset.
  * `BASE_FACTOR = 0.03`.


### 
Perp Contingency
[](https://docs.derive.xyz/docs/portfolio-margin-1#perp-contingency)
The account's perpetual position has a small amount of margin associated with it, based on the number of perpetual contracts and spot price:
Formula

```


PerpContingency=-absPerpSize*PERP_FACTOR*Spot


```

Where:
  * `Perp Size` is the number of perpetual contracts (this number is negative for shorts).
  * `PERP_FACTOR = 0.03`.
  * `Spot` is the spot price of the underlying base asset.


### 
Option Contingency
[](https://docs.derive.xyz/docs/portfolio-margin-1#option-contingency)
For each short option `j` in the portfolio, a small amount of margin is associated with it based on the number of short contracts and a small percentage of the spot price:
Formula

```


OptionContingency=Σmin0OptionSizeⱼxOPTION_FACTORxSpot


```

Where:
  * `Option Sizeⱼ` is the number of option contracts held for expiry `i` and strike `j` (this number is negative for shorts).
  * `OPTION_FACTOR = 0.015`.
  * `Spot` is the spot price of the underlying base asset.


## 
Oracle Contingency
[](https://docs.derive.xyz/docs/portfolio-margin-1#oracle-contingency)
This is the same as [standard margin oracle contingency](https://docs.derive.xyz/reference/standard-margin/#oracle-contingency), with the exception that Option Oracle Contingency counts the total (absolute value of the) number of long and short options contracts on a given strike, not just the number of short options contracts:
Formula

```


OptionOracleContingency=-CONFIDENCE_SCALE*OptionsSize*Spot*1-minSpotConfidenceForwardConfidenceVolConfidence


```

Where `Options Size` is the total number of long and short options contracts for a given strike/expiry. For example, if there are 4 long calls and 3 short puts on the $2000 3 weekly strike, then `Options Size = 4 + 3 = 7`.
## 
Depeg Contingency
[](https://docs.derive.xyz/docs/portfolio-margin-1#depeg-contingency)
When USDC depegs from $1, the value of `mFactor` will increase, proportional to the magnitude of the depeg. Specifically, we have
Formula

```


mFactor=mFactor+max00.99-USDCPrice*PEG_FACTOR


```

where
  * `PEG_FACTOR = 4.0`
  * `USDC_PRICE` is the current price of USDC (measured in USD).


## 
Open Interest Caps
[](https://docs.derive.xyz/docs/portfolio-margin-1#open-interest-caps)
The portfolio margin manager has a cap on the open interest of all instruments it supports. Namely:
  * (ETH, BTC) = (750, 15) base asset
  * (ETH, BTC) = (2,000,000, 100,000) options
  * (ETH, BTC) = (250,000, 12,000) perpetual contracts


These bounds can be adjusted as necessary over time. A low amount of base asset is set due to limited functionality of this instrument at launch. This will be raised when a spot market is available.
# 
Risk Reducing Trades and Risk Assessors
[](https://docs.derive.xyz/docs/portfolio-margin-1#risk-reducing-trades-and-risk-assessors)
As is the case with the standard manager, on the smart contract level, the portfolio margin risk manager will allow any trade to be conducted so long as it satisfies either of the following conditions:
  * the initial margin of the portfolio after the transaction is conducted is positive (`IM(post) > 0`) OR
  * the trade is risk reducing (see the description in [Standard Margin](https://docs.derive.xyz/docs/standard-margin)).


A subtle but key difference is that closing perpetual positions for portfolio margined accounts is not considered a risk reducing transaction. This is because perpetuals could act as a delta hedge and so removing these positions might increase the risk of the portfolio.
As with the standard manager, the portfolio margin manager will also support risk assessors. In addition to the aforementioned benefits of allowing general risk reducing trades, risk assessors are necessary because computing all scenarios for portfolio margin on chain is expensive.
In order to minimise such gas costs and offer traders large portfolio margined accounts, risk assessors only have to compute 3 scenarios on chain: the "mark-to-market" (mtm) scenario (where spot and vol are static) and the two scenarios used to compute the basis contingency (see below).
This means that the risk assessors cannot allow insolvent positions to be opened.
They can, however, allow liquidatable positions to be opened.
# 
Examples
[](https://docs.derive.xyz/docs/portfolio-margin-1#examples)
Consider an account comprised of the following:
  * 1 x LONG ETH $1800 CALL (IV = 60%)
  * 1 x SHORT ETH $1700 PUT (IV = 65%)
  * 700 USDC


where both options have the same expiry (2 weeks) and the corresponding forward is marked at $1740. Assume the risk free rate is `r = 4%` and the spot price of ETH is $1735.
There are 23 scenarios under which the portfolio is evaluated, these are shown in the table below. Let’s explain how to compute the `maxLoss`.
Consider scenario 1, where the forward increases by 18% and the volatility increases. For the former, this results in the portfolio being marked to
Formula

```


Forward=1740x1.18=2053.2


```

To find the shocked volatilities, we know
Formula

```


shockedIV=IVshockxIV


```

where
Formula

```


IVshock=1+VOL_RANGEx30/365/TimeToExpiry)**VEGA_POWER


```

Since `VOL_RANGE = 0.50`, `Time To Expiry = 14/365` and `VEGA_POWER = 0.30`, we have:
Formula

```


IVshock=1+0.50x30/365/14/365**0.3=1.628


```

I.e. the volatility is increased by 62.8% (this is multiplicative).
Hence, the shocked volatilities are:
Formula

```


shockedIV1800strike=0.6*1.628=0.9768shockedIV1700strike=0.65*1.628=1.0582


```

Using these values, we have:
Formula

```


MarkPrice1800call=Call0.6180017400.0414/365=56.27MarkPrice1800callshocked=Call0.9768180020880.0414/365=333.875MarkPrice1700SHORTput=-Put0.65170017400.0414/365=-68.6377MarkPrice1700SHORTputshocked=-Put1.0582170020880.0414/365=-32.8701


```

Thus:
Formula

```


PNL1800shockedcall=333.875-56.27=277.605PNL1700shockedput=-32.8701--68.64=35.7699TotalundiscountedPNL2weekexpiry=277.605+35.7699=+313.375


```

Next, we compute the discount for the 2 week expiry; since the total PNL of the expiry is positive (i.e. it profits from this shock), a discount is applied. The discount is computed as:
Formula

```


Discount2weekexpiry=0.95*exp-1*0.04*14/365+0.12=0.841283


```

So the final discounted PNL is:
Formula

```


DiscountedTotalPNL2week=0.841283*313.375=263.637


```

In the table below, we repeat this methodology for all 24 other scenarios. From the table, we obtain:
Formula

```


maxLoss=minPortfolioLossshockk=-263.536


```

Now, we compute the forward contingency. Using the scenarios in bold
Formula

```


UpLosses=min060.1447=0DownLosses=min0-59.2353=-59.2353ForwardContingency=0.5+2.0*14/365*-59.2353=-34.1617


```

As for the other contingencies, the portfolio contains no perpetual or base asset, so the perpetual and base contingencies are both zero.
We now compute the option contingency. The 2 week expiry has a single short option on the 1700 strike, so the option contingency is:
Formula

```


OptionContingency=-0.015x1735x1=--26.025


```

Finally, we compute:
Formula

```


PortfolioMtM=USDCBalance+-mtm1700PUT+mtm1800CALL=700+-68.743+56.3514=687.608


```

Combining all of this, we have
Formula

```


MaintenanceMargin=687.608+1.0*-34.7+min-34.1617-263.536=389.372


```

Next, let’s address the initial margin. To add some complexity, let’s assume:
  1. The confidence in the 2 weekly forward is 0.49 and
  2. USDC depegs to 0.77.


We now need to compute the oracle contingency and change to the initial margin factor.
For the former, we have:
Formula

```


OptionConfidenceMargin=-1.0*1+1*1735*1-0.49=-1769.7


```

Next, since USDC has depegged, we find:
Formula

```


mfactor+=max00.99-0.77*4.0=1.25+0.88=2.13


```

Hence, we have:
Formula

```


InitialMargin=687.608+2.13*-34.7+min-61.9617-263.536-1769.7=-1717.33


```
  
| Scenario  | Forward Shock  | Vol Shock  | $1800 Call PNL  | $1700 Put PNL  | Total (Discounted) PNL  |  
| --- | --- | --- | --- | --- | --- |  
| 1  | +18%  | Up  | 286.225  | 28.1772  | 264.501  |  
| 2  | +13.5%  | Up  | 219.856  | 13.0125  | 195.908  |  
| 3  | +13.5%  | Unchanged  | 166.73  | 57.5317  | 188.668  |  
| 4  | +13.5%  | Down  | 149.017  | 67.5717  | 182.211  |  
| 5  | +9%  | Up  | 159.528  | -6.89254  | 128.409  |  
| 6  | +9%  | Unchanged  | 99.1002  | 46.9334  | 122.856  |  
| 7  | +9%  | Down  | 72.7765  | 64.4081  | 115.408  |  
| 8  | +4.5%  | Up  | 106.237  | -32.5345  | 62.0045  |  
| 9  | +4.5%  | Unchanged  | 42.7296  | 28.762,  | 60.1447  |  
| 10  | +4.5%  | Down  | 11.1749  | 54.8482  | 55.5394  |  
| 11  | 0  | Up  | 60.8026  | -64.8907  | -3.43923  |  
| 12  | 0  | Unchanged  | 0  | 0  | 0  |  
| 13  | 0  | Down  | -29.1825  | 31.9727  | 2.34315  |  
| 14  | -4.5%  | Up  | 23.7198  | -104.805  | -68.2159  |  
| 15  | -4.5%  | Unchanged  | -28.581  | -41.8297  | -59.2353  |  
| 16  | -4.5%  | Down  | -48.6523  | -11.0417  | -50.2219  |  
| 17  | -9%  | Up  | -4.97608  | -152.853  | -132.779  |  
| 18  | -9%  | Unchanged  | -44.8853  | -97.6136  | -119.882  |  
| 19  | -9%  | Down  | -54.9171  | -75.2099  | -109.474  |  
| 20  | -13.5%  | Up  | -25.7886  | -209.201  | -197.693  |  
| 21  | -13.5%  | Unchanged  | -52.5187  | -166.001  | -183.837  |  
| 22  | -13.5%  | Down  | -56.1314  | -154.022  | -176.799  |  
| 23  | -18%  | Up  | -39.7424  | -273.512  | -263.536  |  
Updated 10 months ago
* * *
[Standard Margin](https://docs.derive.xyz/docs/standard-margin-1)[Liquidations](https://docs.derive.xyz/docs/liquidations-1)
Did this page help you?
Yes
No
Copy Page
  *     * [Margin Calculation](https://docs.derive.xyz/docs/portfolio-margin-1#margin-calculation)
    *       * [maxLoss](https://docs.derive.xyz/docs/portfolio-margin-1#maxloss)
      * [Forward Contingency](https://docs.derive.xyz/docs/portfolio-margin-1#forward-contingency)
      * [Asset Contingency](https://docs.derive.xyz/docs/portfolio-margin-1#asset-contingency)
      * [Oracle Contingency](https://docs.derive.xyz/docs/portfolio-margin-1#oracle-contingency)
      * [Depeg Contingency](https://docs.derive.xyz/docs/portfolio-margin-1#depeg-contingency)
      * [Open Interest Caps](https://docs.derive.xyz/docs/portfolio-margin-1#open-interest-caps)
    * [Risk Reducing Trades and Risk Assessors](https://docs.derive.xyz/docs/portfolio-margin-1#risk-reducing-trades-and-risk-assessors)
    * [Examples](https://docs.derive.xyz/docs/portfolio-margin-1#examples)
