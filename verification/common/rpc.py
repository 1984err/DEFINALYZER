"""
Shared Web3 connection utilities.
"""

from web3 import Web3

from verification.common.config import RPC_URLS


def get_web3(network: str) -> Web3:
    """
    Return a Web3 connection for the requested network.

    Parameters
    ----------
    network : str
        Supported network name (e.g. ethereum, arbitrum).

    Returns
    -------
    Web3
        Connected Web3 instance.

    Raises
    ------
    ValueError
        If the network is unsupported or no RPC URL is configured.
    ConnectionError
        If a connection to the RPC endpoint cannot be established.
    """

    network = network.lower()

    if network not in RPC_URLS:
        raise ValueError(f"Unsupported network: {network}")

    rpc_url = RPC_URLS[network]

    if not rpc_url:
        raise ValueError(f"No RPC URL configured for '{network}'")

    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        raise ConnectionError(f"Unable to connect to {network}")

    return w3