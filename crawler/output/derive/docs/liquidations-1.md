---
protocol: "Derive"
title: "Liquidations"
source: "https://docs.derive.xyz/docs/liquidations-1"
crawled_at: "2026-07-26T22:44:52+00:00"
---

# Liquidations

For AI agents: visit https://docs.derive.xyz/llms.txt for an index of all pages formatted in Markdown and endpoints in OpenAPI.
[Jump to Content](https://docs.derive.xyz/docs/liquidations-1#content)
[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)v2-archive-03062026 v2-archive-09072026 v2-archive-20260724 v2-archive-22062026 v2-archive-30062026 v2.2
* * *
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/liquidations-1)[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
Documentation
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/liquidations-1)
v2.2
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)Liquidations
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
# Liquidations
Users who fall beneath their maintenance margin requirements are subject to liquidation. In this section we describe how liquidations take place. The ability to liquidate is open to all; users are encouraged to operate their own liquidation bots. A script is provided [here](https://hackmd.io/5hMWWuLmRIeiCiwwO-xbUQ#Bidding-script).
# 
Liquidation Auctions
[](https://docs.derive.xyz/docs/liquidations-1#liquidation-auctions)
Liquidations are performed via an auction system where a percentage of all assets in the subaccount (quote, base, perpetuals and options) are available to bidders.
When a user falls beneath their maintenance margin requirements (i.e. maintenance margin becomes negative), any user can call the function `liquidate()`on said account. The auction process then begins; the user is prohibited from conducting any transactions using the flagged account.
A note on portfolio margined accounts
## 
Buffer Margin
[](https://docs.derive.xyz/docs/liquidations-1#buffer-margin)
When liquidating an account, it is important that the resulting account has sufficiently more collateral than its maintenance margin requires. Otherwise, a small move in price against it will result in it being liquidated again. Consequently, we define the buffer margin as:
Formula

```

Buffer Margin = Maintenance Margin + 
    BUFFER_SCALE * (Maintenance Margin - MtM Value)

```

Where:
  * `MtM Value` is the mark-to-market value of the account. This is the sum of all credits (quote and base collateral for all accounts, long options for portfolio margin) and debits (short options for all accounts). Note that the unrealized profit and loss of perpetuals is accounted for in the quote asset due to continuous settlement.
  * `Maintenance Margin` is defined for [Standard Margin](https://docs.derive.xyz/reference/standard-margin) and [Portfolio Margin](https://docs.derive.xyz/reference/portfolio-margin) accounts.
  * `BUFFER_SCALE = 0.15.`


The `Buffer Margin` represents how much USDC needs to be added to the account in order to terminate the liquidation. For instance, a buffer margin of -1000 means at least $1000 USDC needs to be added in order to stop the liquidation.
> 📘
> ### 
> At the end of a liquidation, we want the liquidating account's buffer margin to be 0 to ensure the a small price move doesn't liquidate the account again.
> [](https://docs.derive.xyz/docs/liquidations-1#at-the-end-of-a-liquidation-we-want-the-liquidating-accounts-buffer-margin-to-be-0-to-ensure-the-a-small-price-move-doesnt-liquidate-the-account-again)
## 
Charging the Liquidation Fee
[](https://docs.derive.xyz/docs/liquidations-1#charging-the-liquidation-fee)
When an account is flagged for liquidation, a small fee is charged. The fee is computed using the following formula:
Formula

```


LiquidationFee=MtMValue*0.10*BufferMargin/BufferMargin-MtMValue


```

## 
Solvent Auction
[](https://docs.derive.xyz/docs/liquidations-1#solvent-auction)
After the liquidation fee is charged, the account is put up for a solvent auction. Liquidators can take on a percentage of the entire subaccount at discount to the mark-to-market value.
This discount starts at `INITIAL_DISCOUNT = 5%`, meaning the liquidator buys a percentage of the original subaccount at a 5% discount to the mark-to-market value (mark determined by the manager).
The discount increases linearly from `INITIAL_DISCOUNT` to `FAST_DISCOUNT = 30%` over a period of `FAST_LIQUIDATION_TIME = 15 minutes`.
When a liquidator wishes to liquidate the subaccount, they are able to take on any percentage of the subaccount up to a cap. The cap is computed as follows:
Formula

```


MaxPercentage=BufferMargin/BufferMargin-1-Discount*MtMValue-DiscountxReservedFunds


```

Where:
  * `Discount` is the current percentage discount to the mark-to-market value.
  * `MtM Value` is the mark-to-market value of the entire portfolio defined above.
  * `Reserved Funds` is the amount of cash received by the portfolio from all previous liquidations during the auction. It is necessary to ensure liquidators liquidating at the same price/discount pay the same price.
  * `Buffer Margin` is defined above of the current subaccount (including reserved funds)


If a liquidator requests more than the cap, they are floored at `Max Percentage` and the liquidation terminates.
Otherwise, the liquidator receives their requested percentage of the current portfolio and pays
Formula

```


LiquidatorCost=PercentageReceivedbyLiquidatorxPortfolioValue-ReservedFundsx1-discount


```

USDC to take on their chunk of the portfolio. The liquidation then continues.
If the discount reaches `FAST_DISCOUNT = 30%`(i.e. the liquidation has been ongoing for `FAST_LIQUIDATION_TIME = 15 minutes`) then the auction continues with the discount decreasing from `FAST_DISCOUNT` up to 100% over `LONG_LIQUIDATION_TIME = 12 hours.`
The above methodology for liquidations still holds, the only difference is that the discount increases at a slower rate.
Note that all perpetual PNL and funding, along with all interest on the USDC cash asset is settled before any liquidator bid.
The solvent auction terminates if any of the following conditions are met:
  * `Buffer Margin ≥ 0`. This can occur through any or all of the following: 
    * sufficient amounts of the portfolio (see below) have been liquidated (i.e. `Max Percentage`)
    * the market has moved sufficiently in the trader's favour.
  * The discount hits 100% (i.e. liquidators can take on the portfolio for free). This triggers the start of the insolvent auction (see below).
  * `MtM Value ≤ Reserved Funds` (indicating current portfolio is insolvent as per the feeds) 
    * if `MtM Value ≤ 0` the insolvent auction (see below) can immediately begin
    * if `MtM Value ≥ 0` then 
      * if `Maintenance Margin < 0` the solvent auction restarts
      * if `Maintenance Margin ≥ 0` the trader's liquidation is terminated.


### 
Insolvent Auction
[](https://docs.derive.xyz/docs/liquidations-1#insolvent-auction)
At the insolvent auction, offers start at the mark-to-market value of the portfolio and increase over `INSOLVENT_DURATION = 60 minutes` to the current `Maintenance Margin` of the liquidated portfolio.
Specifically, the current offer at a given time `t` will be given by
Formula

```

currentOffer = min(0, mtm) + (t/INSOLVENT_DURATION) * (Maintenance Margin - min(0, mtm))

```

where
  * `mtm` is the mark-to-market value of the portfolio


From the above, it is clear that all offers at the insolvent auction will also be negative. This indicates that the liquidator will be paid by the security module (SM) (see below) to take on the portfolio.
The percentage that can be taken on by the liquidator during the insolvent auction is always set to 100%.
Offers which reach the maintenance margin stay there indefinitely (note the price liquidators receive will continuously vary with the dynamic maintenance margin of the portfolio).
The insolvent auction ends when either of the following conditions are met:
  * All of the portfolio has been liquidated
  * `Maintenance Margin ≥ 0`


NoteAt the beginning of every insolvent auction, the initial maintenance margin of the portfolio in question is added to a cached sum. If this amount exceeds the total balance of the security module, then all USDC withdrawals are blocked until this is no longer the case. For instance, say Alice became insolvent at time t_1 and Bob at time t_2. Let their maintenance margin at these times be MM(Alice, t_1) and MM(Bob, t_2) respectively. If Charlie becomes insolvent at t_3, then USDC withdrawals are blocked if MM(Alice, t_1) + MM(Bob, t_2) + MM(Charlie, t_3) > Security Module Balance. When an insolvent auction terminates, the cached maintenance margin is removed. The Security Module also earns fees and interest over time, so whenever the resulting sum is smaller than the Security module balance, USDC withdrawals can recommence.
# 
Insurance Fund
[](https://docs.derive.xyz/docs/liquidations-1#insurance-fund)
The insurance fund pays liquidators to take on insolvent accounts. In return for backstopping the system, the SM receives a variety of fees. In the event of a large insolvency, the SM could be depleted, triggering socialized losses.
## 
Socialized Losses
[](https://docs.derive.xyz/docs/liquidations-1#socialized-losses)
When the security module does not have enough funds to pay out an insolvency, socialized losses are enforced via a temporary withdrawal fee. All users trying to withdraw USDC from the system will be charged a withdrawal fee. This fee applies uniformly to all users and scales with the size of the insolvency.
The temporary withdrawal fee is calculated as follows:
Formula

```


TemporaryWithdrawalFee%=UnpaidInsolventDebt/UnpaidInsolventDebt+DepositedUSDC


```

For example, if the SM is unable to cover $100,000 of insolvent debt and there is $1,000,000 of USDC deposited in the system, then the temporary withdrawal fee is
Formula

```


TemporaryWithdrawalFee%=100000/100000+1000000=9.09%


```

In this example, if a user wishes to withdraw $20,000 USDC, then $20,000 x 9.09% will be charged as part of the temporary withdrawal fee.
When the temporary withdrawal fee is in effect, the security module will receive `SM_FEE = 100%` of all interest payments. This is to ensure the withdrawal fee vanishes as quickly as possible.
# 
Liquidator Requirements
[](https://docs.derive.xyz/docs/liquidations-1#liquidator-requirements)
To liquidate an account, the liquidator must have an account consisting only
The liquidator is required to possess a minimum amount of cash. During the solvent auction, the liquidator is required to have sufficient cash so that their buffer margin (after taking on the portfolio) is 0. Specifically, the liquidator is required to have the following amount of cash
Formula

```

cashRequired = Percent Liquidated * (1-discount) * (MtM Value - ResFunds) + f * |Buffer Margin - ResFunds|

```

where:
  * `cashRequired` is the cash required to be in the liquidator's account in order to perform the liquidation
  * `Percent Liquidated` is the percentage of the current portfolio the liquidator has taken on
  * `discount` is the current mark-to-market discount
  * `MtM Value` is the mark-to-market value of the portfolio
  * `ResFunds` is the total reserved funds for the portfolio undergoing solvent liquidation
  * `Buffer Margin` is the buffer margin of the account.


The first term represents the cash the liquidator pays to take on the account (they have to have enough cash to buy it!) while the second term represents the amount of extra USDC that must remain in the liquidator’s cash account to ensure the resulting portfolio has at least zero buffer margin.
For the insolvent auction, we instead require that the liquidator's final account has zero maintenance margin. Similar logic yields
Formula

```

cashRequired = Percent Liquidated * (Maintenance Margin) - cashReceived

```

where
  * `Collateral` and Maintenance Margin are defined above
  * `cashReceived` is the cash received by the liquidator for taking on the portfolio.


NoteA liquidator is required to have a subaccount using the same manager as the liquidated account. I.e. if Bob is liquidating Alice who is using the standard manager, then the subaccount Bob is liquidating Alice with must also subscribe to said manager.
# 
Example (Solvent Auction)
[](https://docs.derive.xyz/docs/liquidations-1#example-solvent-auction)
Consider Alice’s portfolio consisting of:
  * $400,000 of USDC
  * 10 short ETH perpetuals
  * 30 short ETH calls


Suppose Alice’s portfolio is subject to liquidation.
Liquidation Fee
Formula

```


initialfraction=-60000/-60000-100000=37.5%


```

The liquidation fee she is charged is
Formula

```


LiquidationFee=$100000x10%x37.5%=$3750


```

Auction
Suppose there are two liquidators in the system: Bob and Charlie.
The auction starts at a discount of 5%. Some time passes and the discount increases to 12%. At this point, Bob decides he wants to liquidate. Alice’s mark-to-market value and buffer margin are recomputed - say these are $98,000 and -$62,000 respectively.
The maximum amount that Bob can liquidate is given by
Formula

```


MaxPerecentage=-62000/-62000-1-0.12x98000=41.8%


```

Bob only wants to liquidate 20% of Alice’s portfolio. He pays
Formula

```


BobCost=20%x98000x1-0.12=$17248


```

To take on 20% of Alice’s portfolio. I.e. he receives 20% of:
  * $400,000 of USDC ($320,000 remaining)
  * 10 short ETH perpetuals (8 remaining)
  * 30 short ETH calls (24 remaining)


Bob is required to have the following cash in his liquidating account
Formula

```


RequiredCashBob=20%x98000x1-0.12+20%x|-62000|=$29648.


```

The liquidation continues. When the discount reaches 30%, Charlie decides to liquidate the remainder of Alice’s portfolio.
When Charlie decides to step in, Alice’s _remaining_ portfolio has a mark-to-market value of $82,000 and buffer margin of -$46,000. There are also $17,248 of reserved funds. The maximum amount that Charlie can liquidate is given by
Formula

```


MaxPerecentage=-46000/-46000-1-0.3x82000-0.3x17248=42.37%


```

I.e. Charlie can liquidate up to 42.37% of Alice’s remaining portfolio. Let’s say Charlie does so - he pays
Formula

```

Charlie Cost = 42.37% x 82000 x (1-0.3) = $24320.4

```

and receives 42.37% of
  * $320,000 of USDC (note: $17,248 of reserved funds are not included!)
  * 8 short ETH perpetuals
  * 24 short ETH calls


The liquidation terminates as Alice’s portfolio is now deemed safe (since her buffer margin is zero). Her final portfolio consists of
  * $184,416 + (24320.4 + 17248) USDC
  * 4.6 short ETH perpetuals
  * 13.83 short ETH calls


Charlie is required to have the following amount of cash in his account
Formula

```


RequiredCashCharlie=42.37%x82000-17248x1-0.3+42.37%x|-46000-17248|=$46000


```

Note that this is precisely the current buffer margin of Alice's account!
# 
Example (Insolvent Auction)
[](https://docs.derive.xyz/docs/liquidations-1#example-insolvent-auction)
Alice’s portfolio becomes insolvent and the insolvent auction begins.
Suppose that 10 minutes into the insolvent auction process, Bob wants to liquidate Alice. At this point in time, her portfolio has
  * `Mark to Market = -$4000`
  * `Maintenance Margin = -$15,000`


Using the formula from above, we have
Formula

```

currentOffer = min(0, mtm) + (t/INSOLVENT_DURATION) * (MM - min(0, mtm))

```

where
  * `mtm = -$4000`
  * `t = 10`
  * `INSOLVENT_DURATION = 60`
  * `MM = -$15,000`


This yields
Formula

```

currentOffer = -$5,833.33

```

In other words, Bob can take on 100% of the portfolio and receive an additional payout of $5833.33 from the Security Module. If Bob wants only 40%, then he receives 40% of the entire portfolio and is paid out
Formula

```

SM Payout = 0.4 * 5833.33=2333.33

```

from the SM. He is required to have
Formula

```

cashRequired = f * |MM| - cashReceived = 0.4 * |-15,000| - 2333.33= $3666.67

```

of USDC in his account in order to liquidate the account.
Updated 10 months ago
* * *
[Portfolio Margin](https://docs.derive.xyz/docs/portfolio-margin-1)[Oracles](https://docs.derive.xyz/docs/oracles-1)
Did this page help you?
Yes
No
Copy Page
  *     * [Liquidation Auctions](https://docs.derive.xyz/docs/liquidations-1#liquidation-auctions)
    *       * [Buffer Margin](https://docs.derive.xyz/docs/liquidations-1#buffer-margin)
      * [Charging the Liquidation Fee](https://docs.derive.xyz/docs/liquidations-1#charging-the-liquidation-fee)
      * [Solvent Auction](https://docs.derive.xyz/docs/liquidations-1#solvent-auction)
    * [Insurance Fund](https://docs.derive.xyz/docs/liquidations-1#insurance-fund)
    *       * [Socialized Losses](https://docs.derive.xyz/docs/liquidations-1#socialized-losses)
    * [Liquidator Requirements](https://docs.derive.xyz/docs/liquidations-1#liquidator-requirements)
    * [Example (Solvent Auction)](https://docs.derive.xyz/docs/liquidations-1#example-solvent-auction)
    * [Example (Insolvent Auction)](https://docs.derive.xyz/docs/liquidations-1#example-insolvent-auction)
