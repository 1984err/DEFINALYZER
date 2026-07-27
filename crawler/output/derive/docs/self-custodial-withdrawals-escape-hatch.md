---
protocol: "Derive"
title: "Self-Custodial Withdrawals (Escape Hatch)"
source: "https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch"
crawled_at: "2026-07-26T22:45:17+00:00"
---

# Self-Custodial Withdrawals (Escape Hatch)

For AI agents: visit https://docs.derive.xyz/llms.txt for an index of all pages formatted in Markdown and endpoints in OpenAPI.
[Jump to Content](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#content)
[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)v2-archive-03062026 v2-archive-09072026 v2-archive-20260724 v2-archive-22062026 v2-archive-30062026 v2.2
* * *
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/self-custodial-withdrawals-escape-hatch)[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
Documentation
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/self-custodial-withdrawals-escape-hatch)
v2.2
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)Self-Custodial Withdrawals (Escape Hatch)
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
# Self-Custodial Withdrawals (Escape Hatch)
Derive is a self-custodial exchange, meaning you always have custody of your assets. In the case of exchange failure (including failure or downtime of the trading interface, or off-chain matching engine), there is still a permissionless way to withdraw funds from Derive.
This guide is written assuming you onboarded via the trading interface (app.derive.xyz), and have deposited funds into a trading account (subaccount), which in turn is owned by your Smart Contract Wallet (SCW) deployed when your account was created on Derive’s rollup.
This guide is broken up into several steps.
## 
1. Fund owner wallet with native ETH
[](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#1-fund-owner-wallet-with-native-eth)
Bridge a minimal amount (0.0005) of ETH from mainnet to Derive using the superbridge app. This is used for gas to execute transactions on Derive’s layer-2 rollup: [https://superbridge.app/?fromChainId=1&toChainId=957](https://superbridge.app/?fromChainId=1&toChainId=957)
## 
2. Withdraw SubAccounts from Derive Matching system
[](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#2-withdraw-subaccounts-from-derive-matching-system)
## 
2.1 Get your SCW (Derive Wallet) address
[](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#21-get-your-scw-derive-wallet-address)
Call: `getAddress(<Owner address>, 0)`
This will return your SCW (Derive wallet) address. Save this.
## 
2.2 Get a list of your owned subaccounts
[](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#22-get-a-list-of-your-owned-subaccounts)
Easier Option:
Find the list of your owned subaccounts from the interface.
Harder Option:
Add your SCW
Example response, you may see more than one row:
[![](https://downloads.intercomcdn.com/i/o/ytse5axf/1811556275/75eb4bb13cc34f6818bb52e90ccd/Screenshot+2025-11-02+at+3_56_18%E2%80%AFpm.png?expires=1777056300&signature=0a93bf385da8717ec1966b00d65813afee38b22badd0a0a8af4d48e5ad8d8786&req=dSgmF8x7m4NYXPMW1HO4zSEsj%2F9V8MDvWLkmrYicraUrcGRE8Pti3IHegxgO%0Aq3t0fSppDv7%2BK776cLE%3D%0A)](https://downloads.intercomcdn.com/i/o/ytse5axf/1811556275/75eb4bb13cc34f6818bb52e90ccd/Screenshot+2025-11-02+at+3_56_18%E2%80%AFpm.png?expires=1777056300&signature=0a93bf385da8717ec1966b00d65813afee38b22badd0a0a8af4d48e5ad8d8786&req=dSgmF8x7m4NYXPMW1HO4zSEsj%2F9V8MDvWLkmrYicraUrcGRE8Pti3IHegxgO%0Aq3t0fSppDv7%2BK776cLE%3D%0A)
Under “topics” you will see your subaccountId in hexadecimal as the 2nd “topic”. E.g.
## 
2.3 Start your subaccount withdrawal
[](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#23-start-your-subaccount-withdrawal)
## 
2.3.1 Get the calldata for the withdrawal
[](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#231-get-the-calldata-for-the-withdrawal)
## 
2.3.2 Execute initiate withdrawal
[](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#232-execute-initiate-withdrawal)
Navigate to your SCW page on the explorer. Then go to Contract → Read/Write proxy → Write → `execute`
Connect your owner wallet
Call `execute` with:
Repeat for every subaccount
This removes your subaccount from the exchange and starts a 30min cooldown before the next step can proceed
## 
2.3.3 Complete the subaccount withdrawal
[](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#233-complete-the-subaccount-withdrawal)
After waiting 30min`completeWithdrawAccount` calldata. This will move your subaccounts from the matching system to be held by your SCW.
## 
3. Withdraw collaterals from subaccount
[](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#3-withdraw-collaterals-from-subaccount)
This step will be tricky if you hold multiple different collateral assets but still have perp or short option positions. If you have open positions, it may be easiest to just borrow the max amount of USDC to withdraw, and then return later when you get liquidated to withdraw the remainder.
After this you should have one or more assets held by the SCW, withdrawn from the protocol, that can now be bridged
## 
3.1a Get Available collaterals
[](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#31a-get-available-collaterals)
## 
3.1b Withdraw maximum possible USDC
[](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#31b-withdraw-maximum-possible-usdc)
## 
4. Bridge from derive
[](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#4-bridge-from-derive)
Withdrawing from derive can be done via a “wrapper” that converts some of the tokens to ETH to pay the bridging fee.
You will have to execute 2 functions for each token. Firstly approve and then the bridge.
For each token in step 3 (Find these on your SCW page under the “Tokens” drop down):
* * *
  

Updated 3 months ago
* * *
[How do I know my funds are safe?](https://docs.derive.xyz/docs/how-do-i-know-my-funds-are-safe)[What are options?](https://docs.derive.xyz/docs/what-are-options)
Did this page help you?
Yes
No
Copy Page
  *     * [1. Fund owner wallet with native ETH](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#1-fund-owner-wallet-with-native-eth)
    * [2. Withdraw SubAccounts from Derive Matching system](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#2-withdraw-subaccounts-from-derive-matching-system)
    * [2.1 Get your SCW (Derive Wallet) address](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#21-get-your-scw-derive-wallet-address)
    * [2.2 Get a list of your owned subaccounts](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#22-get-a-list-of-your-owned-subaccounts)
    * [2.3 Start your subaccount withdrawal](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#23-start-your-subaccount-withdrawal)
    * [2.3.1 Get the calldata for the withdrawal](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#231-get-the-calldata-for-the-withdrawal)
    * [2.3.2 Execute initiate withdrawal](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#232-execute-initiate-withdrawal)
    * [2.3.3 Complete the subaccount withdrawal](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#233-complete-the-subaccount-withdrawal)
    * [3. Withdraw collaterals from subaccount](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#3-withdraw-collaterals-from-subaccount)
    * [3.1a Get Available collaterals](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#31a-get-available-collaterals)
    * [3.1b Withdraw maximum possible USDC](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#31b-withdraw-maximum-possible-usdc)
    * [4. Bridge from derive](https://docs.derive.xyz/docs/self-custodial-withdrawals-escape-hatch#4-bridge-from-derive)
