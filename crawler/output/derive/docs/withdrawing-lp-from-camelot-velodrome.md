---
protocol: "Derive"
title: "Withdrawing LP from Camelot & Velodrome"
source: "https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome"
crawled_at: "2026-07-26T22:45:46+00:00"
---

# Withdrawing LP from Camelot & Velodrome

For AI agents: visit https://docs.derive.xyz/llms.txt for an index of all pages formatted in Markdown and endpoints in OpenAPI.
[Jump to Content](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome#content)
[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)v2-archive-03062026 v2-archive-09072026 v2-archive-20260724 v2-archive-22062026 v2-archive-30062026 v2.2
* * *
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/withdrawing-lp-from-camelot-velodrome)[![Derive](https://files.readme.io/97584af-brandmark-white.svg)](https://docs.derive.xyz/)
Documentation
[Log In](https://docs.derive.xyz/login?redirect_uri=/docs/withdrawing-lp-from-camelot-velodrome)
v2.2
[Home](https://docs.derive.xyz/)[Documentation](https://docs.derive.xyz/docs)[API Reference](https://docs.derive.xyz/reference)Withdrawing LP from Camelot & Velodrome
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
# Withdrawing LP from Camelot & Velodrome
If you did not manage to withdraw your liquidity before the snapshot on May 8, at 12:00 am UTC, please fill out this [form](https://forms.gle/RmXDoMMEuMs9BkQ1A) and withdraw your liquidity.
UPDATED (MAY 8 12:00:00 AM UTC)  
The DRV snapshot has been taken as MAY 8 12:00:00 AM UTC.  
Purchasing LYRA from May 8 12:00 AM UTC onwards will not confer any additional DRV.  
​  
Blocknumbers for the DRV snapshot were as follows:
To see the balances taken at snapshot visit the [Holder Page](https://lyra.finance/holder).
This article provides guides on how to withdraw liquidity from the following LYRA liquidity pools across the different networks:
## 
Camelot - Arbitrum
[](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome#camelot---arbitrum)
Follow this guide to unstake and withdraw from Camelot.
## 
Guide
[](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome#guide)
Step 1[Positions page](https://app.camelot.exchange/positions) on the Camelot app and connect your wallet.
[![](https://downloads.intercomcdn.com/i/o/1026085416/2e87021abc4f9172466e0268/Kopie+van+Help+Center+Template+%289%29.png?expires=1777060800&signature=03bf244016cfe5325fb34460250fc4a56e06b3c54806af7739dcf78df6d370c6&req=dSAlEMl2mIVeX%2FMW1HO4zbkGa0cNkT1hhT161S5ePfV4wLaCMimkzHs0Sl9M%0AyEAAOcz22pL64IGITPQ%3D%0A)](https://downloads.intercomcdn.com/i/o/1026085416/2e87021abc4f9172466e0268/Kopie+van+Help+Center+Template+%289%29.png?expires=1777060800&signature=03bf244016cfe5325fb34460250fc4a56e06b3c54806af7739dcf78df6d370c6&req=dSAlEMl2mIVeX%2FMW1HO4zbkGa0cNkT1hhT161S5ePfV4wLaCMimkzHs0Sl9M%0AyEAAOcz22pL64IGITPQ%3D%0A)
Step 2
[![](https://downloads.intercomcdn.com/i/o/1026085502/168066ffc126b1186311964c/Kopie+van+Help+Center+Template+%2810%29.png?expires=1777060800&signature=14b73b8514e4f71f60855f864d60a3c38be3869f94af6f6a919617a07b9dfc0d&req=dSAlEMl2mIRfW%2FMW1HO4zXutTMPiJomDPVcW%2FQrsKrEx6VmBHrgV61SjEloS%0ABABc6kzPefpZR7ng82k%3D%0A)](https://downloads.intercomcdn.com/i/o/1026085502/168066ffc126b1186311964c/Kopie+van+Help+Center+Template+%2810%29.png?expires=1777060800&signature=14b73b8514e4f71f60855f864d60a3c38be3869f94af6f6a919617a07b9dfc0d&req=dSAlEMl2mIRfW%2FMW1HO4zXutTMPiJomDPVcW%2FQrsKrEx6VmBHrgV61SjEloS%0ABABc6kzPefpZR7ng82k%3D%0A)
Step 3 (Optional)
[![](https://downloads.intercomcdn.com/i/o/1026085555/28a6a5902cbc9f45e0e125d2/Kopie+van+Help+Center+Template+%2811%29.png?expires=1777060800&signature=d01d390b0b855981e2fad53ffdcd24a56da4a8fa9bfd59e6cef82224e7e14088&req=dSAlEMl2mIRaXPMW1HO4zZAW2PDP8pkkMLLQSKTGKdQKaLuNZyPvMKjusmPu%0AZf9uDMOHK5AF4FGGbEo%3D%0A)](https://downloads.intercomcdn.com/i/o/1026085555/28a6a5902cbc9f45e0e125d2/Kopie+van+Help+Center+Template+%2811%29.png?expires=1777060800&signature=d01d390b0b855981e2fad53ffdcd24a56da4a8fa9bfd59e6cef82224e7e14088&req=dSAlEMl2mIRaXPMW1HO4zZAW2PDP8pkkMLLQSKTGKdQKaLuNZyPvMKjusmPu%0AZf9uDMOHK5AF4FGGbEo%3D%0A)
Step 4
[![](https://downloads.intercomcdn.com/i/o/1026085602/16d661eefbc0ef1c1c6299bb/Kopie+van+Help+Center+Template+%2813%29.png?expires=1777060800&signature=ac151bb4eb96546e05ff99a69c140b49383f7acadd52557fd1d6d60f01cfa38c&req=dSAlEMl2mIdfW%2FMW1HO4zUQx5kndxUaNIN0AEMhTmEb17jJ82xqQyXgB5op8%0AwCx8AGVrPYghdJMV1bo%3D%0A)](https://downloads.intercomcdn.com/i/o/1026085602/16d661eefbc0ef1c1c6299bb/Kopie+van+Help+Center+Template+%2813%29.png?expires=1777060800&signature=ac151bb4eb96546e05ff99a69c140b49383f7acadd52557fd1d6d60f01cfa38c&req=dSAlEMl2mIdfW%2FMW1HO4zUQx5kndxUaNIN0AEMhTmEb17jJ82xqQyXgB5op8%0AwCx8AGVrPYghdJMV1bo%3D%0A)
Step 5
[![](https://downloads.intercomcdn.com/i/o/1026085656/154cccc9dcd3caf38b4df8c8/Kopie+van+Help+Center+Template+%2814%29.png?expires=1777060800&signature=4201068a26196277d461eefdd62272af7a140e46aafb787f14d457f3b9afa0c7&req=dSAlEMl2mIdaX%2FMW1HO4zROUia%2BHY33ttjberDjUClcbbTmHr7QaZep8sZMB%0A6pwcnFUPfwi1z4I4lIc%3D%0A)](https://downloads.intercomcdn.com/i/o/1026085656/154cccc9dcd3caf38b4df8c8/Kopie+van+Help+Center+Template+%2814%29.png?expires=1777060800&signature=4201068a26196277d461eefdd62272af7a140e46aafb787f14d457f3b9afa0c7&req=dSAlEMl2mIdaX%2FMW1HO4zROUia%2BHY33ttjberDjUClcbbTmHr7QaZep8sZMB%0A6pwcnFUPfwi1z4I4lIc%3D%0A)
## 
Velodrome - Optimism
[](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome#velodrome---optimism)
Follow this guide to unstake and withdraw from Velodrome. Users will need to navigate to their Velodrome dashboard to withdraw and unstake their positions.
## 
Guide
[](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome#guide-1)
Step 1[Velodrome app](https://velodrome.finance/) and connect your wallet.
[![](https://downloads.intercomcdn.com/i/o/1026086064/04fdd5495c27bb34df77e4ba/Kopie+van+Help+Center+Template+%2815%29.png?expires=1777060800&signature=61f2344c0ec0c223c8944d53dfae4942e27008bef0edacab34559de4a8901f01&req=dSAlEMl2m4FZXfMW1HO4zfmm78Xcn44EHGI3biOsnv48lYbe8rFfejTwJ1MR%0AAIGtCc3VkiFNSIvTvvI%3D%0A)](https://downloads.intercomcdn.com/i/o/1026086064/04fdd5495c27bb34df77e4ba/Kopie+van+Help+Center+Template+%2815%29.png?expires=1777060800&signature=61f2344c0ec0c223c8944d53dfae4942e27008bef0edacab34559de4a8901f01&req=dSAlEMl2m4FZXfMW1HO4zfmm78Xcn44EHGI3biOsnv48lYbe8rFfejTwJ1MR%0AAIGtCc3VkiFNSIvTvvI%3D%0A)
Step 2
[![](https://downloads.intercomcdn.com/i/o/1026086130/b4fb3274bbce00576962a663/Kopie+van+Help+Center+Template+%2816%29.png?expires=1777060800&signature=116498d49acb62e57776beb37f2d4764f581563ed10938d05b92e629d61edad7&req=dSAlEMl2m4BcWfMW1HO4zUEJTvVmumpRqGnQsX3uhItnlqGUaJK9Lxgtwt1l%0AT3oOGLt3uD1KufghmCA%3D%0A)](https://downloads.intercomcdn.com/i/o/1026086130/b4fb3274bbce00576962a663/Kopie+van+Help+Center+Template+%2816%29.png?expires=1777060800&signature=116498d49acb62e57776beb37f2d4764f581563ed10938d05b92e629d61edad7&req=dSAlEMl2m4BcWfMW1HO4zUEJTvVmumpRqGnQsX3uhItnlqGUaJK9Lxgtwt1l%0AT3oOGLt3uD1KufghmCA%3D%0A)
Step 3
[![](https://downloads.intercomcdn.com/i/o/1026086188/7673f1b8acdc6a4e1862c7ad/Kopie+van+Help+Center+Template+%2817%29.png?expires=1777060800&signature=821ab937464d832edf0c7f1d44c5a96a5b0382c10559211a872ded189da440b8&req=dSAlEMl2m4BXUfMW1HO4zfgQn9zLd0akjdBGgAHhyWzGnifcYifuCaLJZo2a%0Aq0k7r9f6pe6c6Nhkj%2Fs%3D%0A)](https://downloads.intercomcdn.com/i/o/1026086188/7673f1b8acdc6a4e1862c7ad/Kopie+van+Help+Center+Template+%2817%29.png?expires=1777060800&signature=821ab937464d832edf0c7f1d44c5a96a5b0382c10559211a872ded189da440b8&req=dSAlEMl2m4BXUfMW1HO4zfgQn9zLd0akjdBGgAHhyWzGnifcYifuCaLJZo2a%0Aq0k7r9f6pe6c6Nhkj%2Fs%3D%0A)
Step 4
[![](https://downloads.intercomcdn.com/i/o/1026086257/b2c9508b6694487e34397288/Kopie+van+Help+Center+Template+%2818%29.png?expires=1777060800&signature=bb33a38acdf7a54a465ddd8ae8589e2baa95550d984a01e9a1821df78304a022&req=dSAlEMl2m4NaXvMW1HO4zaCTFMp%2Fdg1m%2FudtrnCNRiHupkSDlsHNm9W4yOZ7%0AZqgCcSMUF%2FR%2BfiSu7aY%3D%0A)](https://downloads.intercomcdn.com/i/o/1026086257/b2c9508b6694487e34397288/Kopie+van+Help+Center+Template+%2818%29.png?expires=1777060800&signature=bb33a38acdf7a54a465ddd8ae8589e2baa95550d984a01e9a1821df78304a022&req=dSAlEMl2m4NaXvMW1HO4zaCTFMp%2Fdg1m%2FudtrnCNRiHupkSDlsHNm9W4yOZ7%0AZqgCcSMUF%2FR%2BfiSu7aY%3D%0A)
Step 5
[![](https://downloads.intercomcdn.com/i/o/1026086405/26e24a7d11c6196ba1269189/Kopie+van+Help+Center+Template+%2837%29.png?expires=1777060800&signature=16a57e0cc125a58c94734bdcb8c3536f370c95ec5975ef279e37dc309153d46f&req=dSAlEMl2m4VfXPMW1HO4zb8H8RvjQ1sqwIRMu40HbVMiRKdZ%2Fq9a2%2BMGzhGC%0ATzlAseEMW32ZhNM%2BxH8%3D%0A)](https://downloads.intercomcdn.com/i/o/1026086405/26e24a7d11c6196ba1269189/Kopie+van+Help+Center+Template+%2837%29.png?expires=1777060800&signature=16a57e0cc125a58c94734bdcb8c3536f370c95ec5975ef279e37dc309153d46f&req=dSAlEMl2m4VfXPMW1HO4zb8H8RvjQ1sqwIRMu40HbVMiRKdZ%2Fq9a2%2BMGzhGC%0ATzlAseEMW32ZhNM%2BxH8%3D%0A)
Step 6
[![](https://downloads.intercomcdn.com/i/o/1026086455/669cd106029e12739079d623/Kopie+van+Help+Center+Template+%2836%29.png?expires=1777060800&signature=4a25eaabc3a541d718f8ec5a8c67234caaf37ac2b61356ee699bc7cd26c76d19&req=dSAlEMl2m4VaXPMW1HO4zX7lzuLrbKs044ZB%2B1ZoaP%2BU6EDp6MoE%2BPVCAPkf%0AuaRdYgGbjr2pL4F7xJk%3D%0A)](https://downloads.intercomcdn.com/i/o/1026086455/669cd106029e12739079d623/Kopie+van+Help+Center+Template+%2836%29.png?expires=1777060800&signature=4a25eaabc3a541d718f8ec5a8c67234caaf37ac2b61356ee699bc7cd26c76d19&req=dSAlEMl2m4VaXPMW1HO4zX7lzuLrbKs044ZB%2B1ZoaP%2BU6EDp6MoE%2BPVCAPkf%0AuaRdYgGbjr2pL4F7xJk%3D%0A)
## 
Arrakis - Optimism
[](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome#arrakis---optimism)
Follow this guide to unstake and withdraw from Arrakis on V1. Users will need to navigate to the old V1 dApp site, withdraw their tokens, and remove their liquidity from the Arrakis pool.
## 
Guide
[](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome#guide-2)
Step 1[Arrakis LYRA-ETH LP](https://v1-app.lyra.finance/pools/lyra-eth) on the V1 Interface and connect your wallet.
[![](https://downloads.intercomcdn.com/i/o/1026084302/c0cc7c55668e15361367f848/Kopie+van+Help+Center+Template+%2823%29.png?expires=1777060800&signature=49294f5992186d1d7b59255e6fa9a7841eac86d6eeed3e13b9faaf778f9d7760&req=dSAlEMl2mYJfW%2FMW1HO4zeqUZho0jhgJ4LyPH4vmo3swnTfYCJ7zFBatLyS0%0AO%2BHka1XMeaOdS2PPUzg%3D%0A)](https://downloads.intercomcdn.com/i/o/1026084302/c0cc7c55668e15361367f848/Kopie+van+Help+Center+Template+%2823%29.png?expires=1777060800&signature=49294f5992186d1d7b59255e6fa9a7841eac86d6eeed3e13b9faaf778f9d7760&req=dSAlEMl2mYJfW%2FMW1HO4zeqUZho0jhgJ4LyPH4vmo3swnTfYCJ7zFBatLyS0%0AO%2BHka1XMeaOdS2PPUzg%3D%0A)
Step 2
[![](https://downloads.intercomcdn.com/i/o/1026084384/b79e86f9221786e3b20402c6/Kopie+van+Help+Center+Template+%2824%29.png?expires=1777060800&signature=39193dd964d94a989f3e3be0a1252ade474f444dc552e2caad5c3d54c6c42813&req=dSAlEMl2mYJXXfMW1HO4zYRjWfMoWr%2FqCpqiDM4L%2BOZAipvi67Rj8hlz0xw3%0A%2BC7x%2F7HfBdy4fk6R34c%3D%0A)](https://downloads.intercomcdn.com/i/o/1026084384/b79e86f9221786e3b20402c6/Kopie+van+Help+Center+Template+%2824%29.png?expires=1777060800&signature=39193dd964d94a989f3e3be0a1252ade474f444dc552e2caad5c3d54c6c42813&req=dSAlEMl2mYJXXfMW1HO4zYRjWfMoWr%2FqCpqiDM4L%2BOZAipvi67Rj8hlz0xw3%0A%2BC7x%2F7HfBdy4fk6R34c%3D%0A)
Step 3[Arrakis vault](https://beta.arrakis.finance/vaults/0x70535c46ce04181adf749f34b65b6365164d6b6e?name=lyra&sortDirection=desc&sort=tvl), connect your wallet, and select Remove.
[![](https://downloads.intercomcdn.com/i/o/1026084630/10bb4d2e4071aa53f4109bcc/Kopie+van+Help+Center+Template+%2838%29.png?expires=1777060800&signature=0c6a8b5988edf745bbe6fb83ff89acd30be81cadbb66784cd34a625160bfc3fa&req=dSAlEMl2mYdcWfMW1HO4zeMiCHRKDK3c%2FpNlzqSpuAM71%2FJ7cPAocF0YwXHr%0AJeJ8%2BC9LOHBVrVfHiKA%3D%0A)](https://downloads.intercomcdn.com/i/o/1026084630/10bb4d2e4071aa53f4109bcc/Kopie+van+Help+Center+Template+%2838%29.png?expires=1777060800&signature=0c6a8b5988edf745bbe6fb83ff89acd30be81cadbb66784cd34a625160bfc3fa&req=dSAlEMl2mYdcWfMW1HO4zeMiCHRKDK3c%2FpNlzqSpuAM71%2FJ7cPAocF0YwXHr%0AJeJ8%2BC9LOHBVrVfHiKA%3D%0A)
Step 4
[![](https://downloads.intercomcdn.com/i/o/1026084761/f53f1ea243196d9f9981e547/Kopie+van+Help+Center+Template+%2839%29.png?expires=1777060800&signature=5397a452e53e69118e56208fbf80d67c231cfa76397ac1fb8b6421ba7dd82786&req=dSAlEMl2mYZZWPMW1HO4zSOPttZC4Feo1SsDyWDcHXzCwDUpMx0jxtsmg3J0%0AXVGMBYT56KcLl3HgPp0%3D%0A)](https://downloads.intercomcdn.com/i/o/1026084761/f53f1ea243196d9f9981e547/Kopie+van+Help+Center+Template+%2839%29.png?expires=1777060800&signature=5397a452e53e69118e56208fbf80d67c231cfa76397ac1fb8b6421ba7dd82786&req=dSAlEMl2mYZZWPMW1HO4zSOPttZC4Feo1SsDyWDcHXzCwDUpMx0jxtsmg3J0%0AXVGMBYT56KcLl3HgPp0%3D%0A)
Step 5
[![](https://downloads.intercomcdn.com/i/o/1026084887/e01db2d1b6e01e3c30dfb2ba/Kopie+van+Help+Center+Template+%2840%29.png?expires=1777060800&signature=b54e1e344855b4a8aa91de803a6943767b7f949ad562ea8dacad1fdaa54729c8&req=dSAlEMl2mYlXXvMW1HO4zaNYmIOXWFTpHvO7pS2%2BEPhwaG4ie2WHOjTgXBpu%0AD97cuxkY5od8Efr1R8E%3D%0A)](https://downloads.intercomcdn.com/i/o/1026084887/e01db2d1b6e01e3c30dfb2ba/Kopie+van+Help+Center+Template+%2840%29.png?expires=1777060800&signature=b54e1e344855b4a8aa91de803a6943767b7f949ad562ea8dacad1fdaa54729c8&req=dSAlEMl2mYlXXvMW1HO4zaNYmIOXWFTpHvO7pS2%2BEPhwaG4ie2WHOjTgXBpu%0AD97cuxkY5od8Efr1R8E%3D%0A)
* * *
  

Updated 3 months ago
* * *
[Retail Trading Rewards Program](https://docs.derive.xyz/docs/retail-trading-rewards-program-1)[How to claim OP Rewards](https://docs.derive.xyz/docs/how-to-claim-op-rewards)
Did this page help you?
Yes
No
Copy Page
  *     * [Camelot - Arbitrum](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome#camelot---arbitrum)
    * [Guide](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome#guide)
    * [Velodrome - Optimism](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome#velodrome---optimism)
    * [Guide](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome#guide-1)
    * [Arrakis - Optimism](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome#arrakis---optimism)
    * [Guide](https://docs.derive.xyz/docs/withdrawing-lp-from-camelot-velodrome#guide-2)
