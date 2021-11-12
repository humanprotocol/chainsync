import hashlib
import logging
import os
import sys
import requests
import json
import urllib
import time
import datetime

from retry import retry

from decimal import Decimal
from enum import Enum
from typing import List, Dict, Tuple

from web3 import Web3, WebsocketProvider
from web3.types import Wei
from web3._utils.events import get_event_data
from web3._utils.contracts import find_matching_event_abi
from web3.middleware import geth_poa_middleware
from web3.exceptions import MismatchedABI


from chainsync.eth.config import Config
from chainsync.eth.contracts_interface import ContractsInterface


# Setup Logging
LOGGER = logging.getLogger("ChainSync:Eth:Sync")
logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))

Status = Enum("Status", "Launched", "Pending", "Partial", "Paid", "Complete", "Cancelled")


def _setup_web3(server):
    provider = WebsocketProvider(server)
    w3 = Web3(provider)
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3


class Synchroniser():
    def __init__(self, server, contract_urls, gas_payer, gas):
        self.w3 = _setup_web3(server)
        self.contracts_interface = ContractsInterface(contract_urls)
        self.launched_api = find_matching_event_abi(
            self.contracts_interface.get_abi('EscrowFactory'), 'Launched', ['eip20', 'escrow'])
        self.launched_addrs = dict()
        self.gas = Wei(gas)
        self.gas_payer = Web3.toChecksumAddress(gas_payer)


    def _get_new_launched_addr(self, filter_params, factory_addr_list, hmtoken_addr_list):
        LOGGER.info("Started Synchronisation: {}".format(filter_params))
        logs = self.w3.eth.getLogs(filter_params)
        for log in logs:
            try:
                event = get_event_data(self.w3.codec, self.launched_api, log)
                eip20_addr = event['args']['eip20']
                escrow_addr = event['args']['escrow']
                tx_hash = event['transactionHash'].hex()
                contract = self.contracts_interface.get_contract(self.w3, 'Escrow', escrow_addr)
                launcher_ = contract.functions.launcher().call(
                    {"from": self.gas_payer, "gas": self.gas}
                )
                if eip20_addr in self.hmtoken_addr:
                    if escrow_addr not in self.launched_addrs and launcher_ in factory_addr_list:
                        self.launched_addrs[escrow_addr] = launcher_
                        LOGGER.info(f"New HMT escrow spotted at: {str(tx_hash)}")
            except Exception as e:
                LOGGER.error(f"Interrupted getting all new addresses: {e}")
        return list(self.launched_addrs.items())


    def _add_job_to_runner(self, addr, factory_addr):
        if not addr:
            LOGGER.debug("Empty address should not instantiated.")
            return False
        LOGGER.debug(f"Address {addr} getting inserted to exchange.")

        escrow_addr = Web3.toChecksumAddress(addr)
        escrow_contract = self.contracts_interface.get_contract(self.w3, 'Escrow', addr)
        url_ = escrow_contract.functions.manifestUrl().call(
            {"from": self.gas_payer, "gas": self.gas}
        )
        status_ = escrow_contract.functions.status().call(
            {"from": self.gas_payer, "gas": self.gas}
        ) + 1
        LOGGER.debug(f"url: {url_}, status: {status_}")

        if (status_ == Status.Pending and url_ != ''):
            
            payload = {
                'address': escrow_addr,
                'manifest_url': url_,
                'launched_at': datetime.datetime.now(),
                'factory': factory_addr 
            }
          

    def run(self, factory_addr_list, hmtoken_addr_list):
        # Can move this up actually
        filter_params = {'fromBlock': 0, 'toBlock': 'latest', 'address': factory_addr_list}
        LOGGER.info("Synchronisation Server Started")
        try:
            for escrow_addr, factory_addr in self._get_new_launched_addr(filter_params, factory_addr_list, hmtoken_addr_list):
                self._add_job_to_runner(escrow_addr, factory_addr)
        except Exception as e:
            LOGGER.error(f"Unable to synchronize: {e}")
            raise (e)


# Needs rework here
if __name__ == '__main__':
    synchroniser = Synchroniser(Config.SERVER, Config.CONTRACT_URLS, Config.GAS_PAYER, Config.GAS)
    while True:
        try:
            synchroniser.run()
        except Exception as e:
            LOGGER.info(f"Problem synchronizing, exiting the process..")
            sys.exit(1)
        finally:
            time.sleep(15)
