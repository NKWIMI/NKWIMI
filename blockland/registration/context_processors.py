import os  # Add this line
from django.conf import settings
from web3 import Web3
import json

def blockchain_context(request):
    w3 = Web3(Web3.HTTPProvider(settings.GANACHE_URL))
    with open(os.path.join(settings.BASE_DIR, 'abi.json')) as f:
        abi = json.load(f)
    contract_address = Web3.to_checksum_address(settings.CONTRACT_ADDRESS)
    contract = w3.eth.contract(address=contract_address, abi=abi)
    return {'w3': w3, 'contract': contract}