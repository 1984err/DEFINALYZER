---
protocol: "Derive"
title: "LYRA to DRV Migration"
source: "https://docs.derive.xyz/docs/lyra-to-drv-migration"
crawled_at: "2026-07-26T22:44:54+00:00"
---

# LYRA to DRV Migration

For AI agents: visit https://docs.derive.xyz/llms.txt for an index of all pages formatted in Markdown and endpoints in OpenAPI.
[Jump to Content](https://docs.derive.xyz/docs/lyra-to-drv-migration#content)
[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)v2-archive-03062026 v2-archive-09072026 v2-archive-20260724 v2-archive-22062026 v2-archive-30062026 v2.2
* * *
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/lyra-to-drv-migration)[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
Documentation
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/lyra-to-drv-migration)
v2.2
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference) LYRA to DRV Migration
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
#  LYRA to DRV Migration
The LYRA snapshot has been taken on May 8 12:00 AM UTC. All snapshotted balances convert 1:1 to DRV. The DRV token is planned to launch on Jan 15, 2025. Purchasing LYRA from May 8 12:00 AM UTC onwards will not confer any additional DRV.  
​  
Blocknumbers for the DRV snapshot were as follows:
To see the balances taken at snapshot visit the [Holder Page](https://www.derive.xyz/stake).
## 
Timeline
[](https://docs.derive.xyz/docs/lyra-to-drv-migration#timeline)
The timeline for the migration is as follows:
## 
FAQs
[](https://docs.derive.xyz/docs/lyra-to-drv-migration#faqs)
## 
General FAQs
[](https://docs.derive.xyz/docs/lyra-to-drv-migration#general-faqs)
#### 
What is DRV?
[](https://docs.derive.xyz/docs/lyra-to-drv-migration#what-is-drv)
DRV is the utility token for the Derive Derivatives Network, encompassing the chain, protocol, exchange, wallet and more.  
​  
​How will the migration affect governance mechanisms?
Governance will continue with the balances recorded at the snapshot until the launch of DRV. Voting parameters, such as duration, quorum, and proposition threshold, will remain aligned with current standards until then.
When is the official launch of DRV planned?
The launch of DRV is planned on Jan 15, 2025.
How will the DRV conversion rate be calculated?
The conversion from LYRA to DRV will be at a 1:1 ratio based on the balances at the time of the snapshot.  
​  
​When was the snapshot date?
The snapshot occurred on May 8, 12:00:00 AM UTC.  
​  
Blocknumbers are as follows:
## 
Post-Snapshot FAQs (After May 8)
[](https://docs.derive.xyz/docs/lyra-to-drv-migration#post-snapshot-faqs-after-may-8)
#### 
What is happening with Lyra's liquidity and demand?
[](https://docs.derive.xyz/docs/lyra-to-drv-migration#what-is-happening-with-lyras-liquidity-and-demand)
On May 8 the migration from LYRA to DRV began and a snapshot of all LYRA and stkLYRA balances across all networks was taken. Now Lyra's liquidity and demand are trending to 0 and is expected since LYRA now has no utility or governance value. This utility and governance value will be transferred to DRV upon the launch in Jan 2025.
I hold LYRA, what do I need to do?
You don't need to do anything. Your LYRA will migrate to DRV after the snapshot.
I hold stkLYRA, what do I need to do?
Similar to LYRA holders, you don't need to take any action. Your stkLYRA will be converted to DRV based on the snapshot.
What happens if I transfer or sell my Lyra after the snapshot?
There are no restrictions on what users can do with their LYRA. However, we strongly recommend against purchasing LYRA now since it will confer no rights to DRV. We continue to recommend that LPs withdraw their liquidity.
#### 
I didn't withdraw my LYRA LP position before the snapshot. What should I do?
[](https://docs.derive.xyz/docs/lyra-to-drv-migration#i-didnt-withdraw-my-lyra-lp-position-before-the-snapshot-what-should-i-do)
Visit the [Prestaking page](https://www.derive.xyz/stake) to see your balances taken at snapshot.
* * *
  

Updated 3 months ago
* * *
[DRV](https://docs.derive.xyz/docs/drv-1)[DRV Token Launch](https://docs.derive.xyz/docs/drv-token-launch)
Did this page help you?
Yes
No
Copy Page
  *     * [Timeline](https://docs.derive.xyz/docs/lyra-to-drv-migration#timeline)
    * [FAQs](https://docs.derive.xyz/docs/lyra-to-drv-migration#faqs)
    * [General FAQs](https://docs.derive.xyz/docs/lyra-to-drv-migration#general-faqs)
    * [Post-Snapshot FAQs (After May 8)](https://docs.derive.xyz/docs/lyra-to-drv-migration#post-snapshot-faqs-after-may-8)
