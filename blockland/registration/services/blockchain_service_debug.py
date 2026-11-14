# Standard library imports
import os
import json
import logging
from typing import Optional, Tuple, Dict, Any, List

# Third-party imports
from web3 import Web3, exceptions
from eth_account import Account
from eth_utils import to_checksum_address

# Django imports
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.apps import apps
from django.utils import timezone
import binascii

logger = logging.getLogger(__name__)

def string_to_bytes32(text):
    """Convert a string to bytes32 format"""
    if len(text) > 32:
        text = text[:32]
    return text.encode('utf-8').ljust(32, b'\0')

def bytes32_to_string(bytes_data):
    """Convert bytes32 back to string"""
    return bytes_data.rstrip(b'\0').decode('utf-8')

class BlockchainServiceError(Exception):
    """Custom exception for blockchain service errors"""
    pass

class BlockchainService:
    """
    Service for interacting with Ethereum blockchain and smart contracts.
    Handles connections, transactions, and database synchronization.
    """
    
    _abi_cache = None
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern implementation"""
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, user=None):
        """Initialize blockchain connection with proper validation"""
        if not hasattr(self, 'w3'):  # Only initialize once
            self.setup_web3_connection()
            self.setup_account(user)
            if self.w3:  # Only setup contract if we have a connection
                self.validate_account_balance()
                self.setup_contract()
                self._setup_event_filters()

    def _setup_event_filters(self):
        """Setup event filters for real-time monitoring"""
        if not self.w3 or not self.contract:
            return
            
        try:
            self.event_filters = {
                'TransferInitiated': self.contract.events.TransferInitiated.create_filter(from_block='latest'),
                'TransferAccepted': self.contract.events.TransferAccepted.create_filter(from_block='latest'),
                'MetadataVersioned': self.contract.events.MetadataVersioned.create_filter(from_block='latest')
            }
        except Exception as e:
            logger.warning(f"Could not setup event filters: {e}")

    def setup_web3_connection(self) -> None:
        """Configure Web3 connection with fallback and validation"""
        # Try to get RPC URL from BLOCKCHAIN_CONFIG first, then direct settings
        blockchain_config = getattr(settings, "BLOCKCHAIN_CONFIG", {})
        rpc_url = blockchain_config.get('GANACHE_URL') or getattr(settings, "BLOCKCHAIN_RPC_URL", "http://127.0.0.1:7545")
        
        if not rpc_url:
            logger.warning("⚠ No RPC URL configured. Using mock blockchain mode.")
            self.w3 = None
            self.contract = None
            return

        try:
            self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 30}))
            if not self.w3.is_connected():
                raise ConnectionError(f"Failed to connect to Ethereum node at {rpc_url}")
            
            logger.info(f"✅ Connected to Ethereum node at {rpc_url} (Chain ID: {self.w3.eth.chain_id})")
        except Exception as e:
            logger.error(f"Web3 connection error: {str(e)}")
            logger.warning("⚠ Falling back to mock blockchain mode")
            self.w3 = None
            self.contract = None

    def setup_account(self, user=None) -> None:
        """Configure and validate the Ethereum account"""
        self.user = user
        
        # If web3 is not connected, use mock mode
        if not self.w3:
            self.account = None
            self.private_key = None
            logger.warning("⚠ Using mock blockchain mode - no real account configured")
            return
            
        try:
            # Priority 1: BLOCKCHAIN_CONFIG private key
            blockchain_config = getattr(settings, "BLOCKCHAIN_CONFIG", {})
            if blockchain_config.get('ETHEREUM_PRIVATE_KEY'):
                self.private_key = blockchain_config['ETHEREUM_PRIVATE_KEY']
                account_source = "BLOCKCHAIN_CONFIG"
            
            # Priority 2: Settings private key (direct variable)
            elif hasattr(settings, "ETHEREUM_PRIVATE_KEY") and settings.ETHEREUM_PRIVATE_KEY:
                self.private_key = settings.ETHEREUM_PRIVATE_KEY
                account_source = "settings"
            
            # Priority 3: User's profile private key
            elif user and hasattr(user, 'profile') and user.profile.encrypted_private_key:
                self.private_key = user.profile.get_wallet_private_key()
                account_source = "user profile"
            
            # Priority 4: First Ganache account (development only)
            elif settings.DEBUG and self.w3.eth.chain_id == 1337:
                self.private_key = self.w3.eth.account.create().key.hex()
                account_source = "Ganache default"
            
            else:
                raise ImproperlyConfigured("No Ethereum private key available")

            # Validate and clean private key
            cleaned_key = self.private_key.strip().replace("0x", "")
            if not all(c in "0123456789abcdefABCDEF" for c in cleaned_key) or len(cleaned_key) != 64:
                raise ImproperlyConfigured("Invalid private key format")

            self.account = self.w3.eth.account.from_key(cleaned_key)
            logger.info(f"✅ Blockchain account loaded from {account_source}: {self.account.address}")
        
        except Exception as e:
            logger.error(f"Account setup failed: {str(e)}")
            self.account = None
            self.private_key = None

    def validate_account_balance(self) -> None:
        """Check and ensure sufficient ETH balance"""
        if not self.w3 or not self.account:
            return
            
        try:
            balance = self.w3.eth.get_balance(self.account.address)
            min_balance = self.w3.to_wei(0.1, 'ether')
            
            if balance < min_balance:
                logger.warning(
                    f"⚠ Low balance: {self.w3.from_wei(balance, 'ether')} ETH "
                    f"(minimum {self.w3.from_wei(min_balance, 'ether')} ETH recommended)"
                )
                
                # Auto-fund from first Ganache account in development
                if settings.DEBUG and self.w3.eth.chain_id == 1337:
                    self.fund_account_from_testnet(min_balance - balance)
        
        except Exception as e:
            logger.error(f"Balance check failed: {str(e)}")

    def fund_account_from_testnet(self, amount: int) -> Optional[Dict]:
        """Automatically fund account from first Ganache account (dev only)"""
        try:
            test_accounts = self.w3.eth.accounts
            if test_accounts:
                funder = test_accounts[0]
                tx_hash = self.w3.eth.send_transaction({
                    'from': funder,
                    'to': self.account.address,
                    'value': amount
                })
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                new_balance = self.w3.eth.get_balance(self.account.address)
                logger.info(
                    f"⚡ Funded account with {self.w3.from_wei(amount, 'ether')} ETH. "
                    f"New balance: {self.w3.from_wei(new_balance, 'ether')} ETH"
                )
                return receipt
            return None
        except Exception as e:
            logger.error(f"Failed to auto-fund account: {str(e)}")
            return None

    def _string_to_bytes32(self, text: str) -> bytes:
        """Convert a string to bytes32 format for smart contract calls"""
        if not text:
            return b'\x00' * 32
        
        # Encode the string to bytes and pad/truncate to 32 bytes
        text_bytes = text.encode('utf-8')
        if len(text_bytes) > 32:
            # Truncate if too long
            return text_bytes[:32]
        else:
            # Pad with zeros if too short
            return text_bytes.ljust(32, b'\x00')

    def _bytes32_to_string(self, bytes_data: bytes) -> str:
        """Convert bytes32 back to string"""
        if not bytes_data:
            return ""
        
        # Remove trailing zeros and decode
        return bytes_data.rstrip(b'\x00').decode('utf-8', errors='ignore')
        
    def setup_contract(self) -> None:
        """Configure the contract interface with validation"""
        if not self.w3:
            logger.warning("⚠ No Web3 connection - skipping contract setup")
            return
            
        try:
            # Read from BLOCKCHAIN_CONFIG instead of direct settings
            blockchain_config = getattr(settings, "BLOCKCHAIN_CONFIG", {})
            contract_address = blockchain_config.get('CONTRACT_ADDRESS', '')
            
            if not contract_address:
                raise ImproperlyConfigured("CONTRACT_ADDRESS not found in BLOCKCHAIN_CONFIG")

            self.contract_address = to_checksum_address(contract_address)
            logger.info(f"Validated contract address: {self.contract_address}")

            abi = self.get_contract_abi()
            self.contract = self.w3.eth.contract(
                address=self.contract_address,
                abi=abi
            )
            
            # Verify contract is deployed
            code = self.w3.eth.get_code(self.contract_address)
            if code == b'':
                raise ValueError("No code at contract address - contract not deployed?")
                
            logger.info(f"✅ Contract verified at address: {self.contract_address}")
        
        except Exception as e:
            logger.error(f"Contract setup failed: {str(e)}")
            self.contract = None

    def get_contract_abi(self) -> List[Dict]:
        """Load and cache the contract ABI"""
        if BlockchainService._abi_cache:
            return BlockchainService._abi_cache

        try:
            # Read from BLOCKCHAIN_CONFIG instead of direct settings
            blockchain_config = getattr(settings, "BLOCKCHAIN_CONFIG", {})
            abi_path = blockchain_config.get('CONTRACT_ABI_PATH')
            
            if not abi_path:
                raise ImproperlyConfigured("CONTRACT_ABI_PATH not set in BLOCKCHAIN_CONFIG")
            if not os.path.exists(abi_path):
                raise FileNotFoundError(f"Contract ABI file not found at: {abi_path}")

            with open(abi_path, "r", encoding="utf-8") as f:
                contract_data = json.load(f)
                
                # Handle different ABI formats
                if isinstance(contract_data, dict):
                    if "abi" in contract_data:
                        abi = contract_data["abi"]
                    elif "contracts" in contract_data:
                        contract_name = next(iter(contract_data["contracts"]))
                        abi = contract_data["contracts"][contract_name]["abi"]
                    else:
                        raise ValueError("No ABI found in JSON file")
                elif isinstance(contract_data, list):
                    abi = contract_data
                else:
                    raise ValueError("Invalid ABI JSON format")
                
                if not isinstance(abi, list) or len(abi) == 0:
                    raise ValueError("Empty or invalid ABI array")
                    
                BlockchainService._abi_cache = abi
                logger.debug(f"Loaded and cached contract ABI with {len(abi)} items")
                return abi
        
        except Exception as e:
            logger.error(f"ABI loading failed: {str(e)}")
            raise BlockchainServiceError("Failed to load contract ABI") from e

    def validate_ownership(self, parcel_id: str, owner_address: str) -> bool:
        """Validate that the sender owns the parcel on blockchain"""
        try:
            if not self.w3 or not self.contract:
                logger.warning("No blockchain connection - skipping ownership validation")
                return True  # Return True in mock mode for development
                
            # Get the current owner from blockchain
            parcel_data = self.get_parcel(parcel_id)
            if not parcel_data:
                logger.error(f"Parcel {parcel_id} not found on blockchain")
                return False
                
            blockchain_owner = parcel_data.get('owner', '').lower()
            expected_owner = owner_address.lower()
            
            is_owner = blockchain_owner == expected_owner
            
            logger.debug(
                f"Ownership validation - Parcel: {parcel_id}, "
                f"Expected: {expected_owner}, "
                f"Actual: {blockchain_owner}, "
                f"Valid: {is_owner}"
            )
            
            return is_owner
            
        except Exception as e:
            logger.error(f"Error validating ownership for parcel {parcel_id}: {str(e)}")
            return False

    def build_transaction(self, function_call, value: int = 0) -> Dict:
        """Build a transaction with proper gas estimation"""
        if not self.w3:
            raise BlockchainServiceError("No blockchain connection available")
            
        try:
            transaction = function_call.build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gasPrice': self.w3.eth.gas_price,
                'value': value
            })
            
            estimated_gas = function_call.estimate_gas({
                'from': self.account.address,
                'value': value
            })
            transaction['gas'] = int(estimated_gas * 1.2)  # 20% buffer
            
            return transaction
        except exceptions.ContractLogicError as e:
            logger.error(f"Contract logic error: {str(e)}")
            raise BlockchainServiceError(f"Contract error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Transaction build failed: {str(e)}")
            raise BlockchainServiceError("Failed to build transaction") from e

    def send_transaction(self, transaction: Dict) -> str:
        """Send a signed transaction and wait for receipt - FIXED: rawTransaction attribute"""
        if not self.w3:
            # Mock transaction for development
            mock_hash = f"0x{'mock_tx_hash_for_dev_12345' * 2}"[:66]
            logger.info(f"⚠ Mock transaction (no blockchain): {mock_hash}")
            return mock_hash
            
        try:
            signed_tx = self.w3.eth.account.sign_transaction(
                transaction, 
                private_key=self.private_key
            )
            
            # FIX: Use rawTransaction (correct attribute name)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 0:
                # Try to get the revert reason
                try:
                    tx = self.w3.eth.get_transaction(tx_hash)
                    # Simulate the transaction to get revert reason
                    self.w3.eth.call({
                        'to': tx['to'],
                        'from': tx['from'],
                        'value': tx['value'],
                        'data': tx['input'],
                        'gas': tx['gas'],
                        'gasPrice': tx['gasPrice']
                    }, tx['blockNumber'] - 1)
                except Exception as revert_error:
                    error_msg = f"Transaction reverted: {str(revert_error)}"
                else:
                    error_msg = "Transaction failed (status=0) - unknown reason"
                
                raise BlockchainServiceError(error_msg)
            
            logger.info(f"✅ Transaction successful: {tx_hash.hex()}")
            return tx_hash.hex()
        
        except exceptions.TimeExhausted as e:
            logger.error(f"Transaction timeout: {str(e)}")
            raise BlockchainServiceError("Transaction timed out") from e
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            raise BlockchainServiceError(f"Failed to send transaction: {str(e)}") from e

    def _send_transaction_simple(self, function_call, gas_limit=2000000):
        """Helper method to send transactions with proper error handling - FIXED: rawTransaction"""
        try:
            if not self.w3 or not self.account:
                logger.error("No blockchain connection or account available")
                return None

            # Build transaction
            transaction = function_call.build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': gas_limit,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            
            # Send raw transaction - FIX: Use rawTransaction (correct attribute)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                return tx_hash.hex()
            else:
                logger.error(f"Transaction failed: {tx_hash.hex()}")
                return None
                
        except Exception as e:
            logger.error(f"Transaction error: {e}")
            return None

    def call_function(self, function_name: str, *args) -> Any:
        """Call a read-only contract function"""
        if not self.w3 or not self.contract:
            # Mock responses for development
            if function_name == "getParcelsByOwner":
                return ["mock_parcel_1", "mock_parcel_2"]
            elif function_name == "getParcelByKey":
                return ["mock_id", 100.0, "0xMockAddress", False, "QmMockHash", 1234567890, 1234567890]
            else:
                return None
                
        try:
            func = getattr(self.contract.functions, function_name)
            return func(*args).call()
        except exceptions.ContractLogicError as e:
            logger.error(f"Contract call error: {str(e)}")
            raise BlockchainServiceError(f"Contract error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Function call failed: {str(e)}")
            raise BlockchainServiceError("Failed to call contract function") from e

    def get_parcels_by_owner(self, owner_address: str) -> List[str]:
        """Get all parcel IDs owned by an address"""
        try:
            owner_address = to_checksum_address(owner_address)
            parcel_keys = self.call_function("getParcelsByOwner", owner_address)
            
            # Convert bytes32 keys back to strings
            if parcel_keys:
                return [self._bytes32_to_string(key) for key in parcel_keys]
            return []
        except Exception as e:
            logger.error(f"Failed to get parcels for owner {owner_address}: {str(e)}")
            return []

    def register_parcel(self, land_id: str, owner_address: str, document_hash: str) -> str:
        """Register a new parcel on the blockchain - FIXED: Use string parameters"""
        try:
            owner_address = to_checksum_address(owner_address)
            
            # Use string parameters directly (no bytes32 conversion)
            tx = self.build_transaction(
                self.contract.functions.registerParcel(
                    land_id,           # string parameter
                    owner_address,     # address parameter  
                    document_hash      # string parameter
                )
            )
            
            return self.send_transaction(tx)
        except Exception as e:
            logger.error(f"Parcel registration failed for {land_id}: {str(e)}")
            raise BlockchainServiceError("Failed to register parcel on blockchain") from e

    def freeze_parcel(self, land_id: str) -> str:
        """Freeze a parcel on the blockchain - FIXED: Use string parameters"""
        try:
            # Use string parameter directly
            tx = self.build_transaction(
                self.contract.functions.freezeParcel(land_id)
            )
            
            return self.send_transaction(tx)
        except Exception as e:
            logger.error(f"Parcel freeze failed for {land_id}: {str(e)}")
            raise BlockchainServiceError("Failed to freeze parcel on blockchain") from e

    def unfreeze_parcel(self, land_id: str) -> str:
        """Unfreeze a parcel on the blockchain - FIXED: Use string parameters"""
        try:
            # Use string parameter directly
            tx = self.build_transaction(
                self.contract.functions.unfreezeParcel(land_id)
            )
            
            return self.send_transaction(tx)
        except Exception as e:
            logger.error(f"Parcel unfreeze failed for {land_id}: {str(e)}")
            raise BlockchainServiceError("Failed to unfreeze parcel on blockchain") from e

    def execute_transfer(self, parcel_id: str, from_address: str, to_address: str, document_hash: str = "") -> Tuple[Optional[str], Optional[str]]:
        """Execute parcel transfer on blockchain - used by transfer service"""
        try:
            # Validate ownership first
            if not self.validate_ownership(parcel_id, from_address):
                logger.error(f"Parcel {parcel_id} not owned by {from_address}")
                return None, "Parcel not owned by sender"

            if not self.w3 or not self.account:
                return None, "No blockchain connection available"

            # Prepare and execute transfer
            to_address_checksum = to_checksum_address(to_address)
            
            transaction = self.build_transaction(
                self.contract.functions.completeTransfer(
                    parcel_id,           # string parameter
                    to_address_checksum, # address parameter
                    document_hash or ''  # string parameter
                )
            )
            
            tx_hash = self.send_transaction(transaction)
            return tx_hash, None

        except Exception as e:
            logger.error(f"Transfer execution failed for {parcel_id}: {str(e)}")
            return None, str(e)

    def initiate_transfer(self, parcel_id, from_address, to_address, ipfs_hash=""):
        """Initiate land transfer on blockchain - FIXED: Proper transaction handling"""
        try:
            function_call = self.contract.functions.initiateTransfer(
                parcel_id, to_address, ipfs_hash
            )
            tx_hash = self._send_transaction_simple(function_call)
            
            if tx_hash:
                logger.info(f"✅ Transfer initiated: {tx_hash}")
            else:
                logger.error("❌ Transfer initiation failed")
                
            return tx_hash
            
        except Exception as e:
            logger.error(f"Error initiating transfer: {e}")
            return None

    def accept_transfer(self, parcel_id):
        """Accept a pending transfer - FIXED: Proper transaction handling"""
        try:
            function_call = self.contract.functions.acceptTransfer(parcel_id)
            tx_hash = self._send_transaction_simple(function_call)
            
            if tx_hash:
                logger.info(f"✅ Transfer accepted: {tx_hash}")
            else:
                logger.error("❌ Transfer acceptance failed")
                
            return tx_hash
            
        except Exception as e:
            logger.error(f"Error accepting transfer: {e}")
            return None

    def cancel_transfer(self, parcel_id):
        """Cancel a transfer - FIXED: Proper transaction handling"""
        try:
            function_call = self.contract.functions.cancelTransfer(parcel_id)
            tx_hash = self._send_transaction_simple(function_call)
            
            if tx_hash:
                logger.info(f"✅ Transfer cancelled: {tx_hash}")
            else:
                logger.error("❌ Transfer cancellation failed")
                
            return tx_hash
            
        except Exception as e:
            logger.error(f"Error cancelling transfer: {e}")
            return None

    def complete_transfer(self, land_id: str, recipient_address: str, document_hash: str = "") -> str:
        """Complete a property transfer on the blockchain - FIXED: Use string parameters"""
        try:
            recipient_address = to_checksum_address(recipient_address)
            
            # Use string parameters directly
            tx = self.build_transaction(
                self.contract.functions.completeTransfer(
                    land_id,           # string parameter
                    recipient_address, # address parameter
                    document_hash or '' # string parameter
                )
            )
            
            return self.send_transaction(tx)
        except Exception as e:
            if "completeTransfer" in str(e):
                # Fallback to acceptTransfer
                logger.warning("completeTransfer not found, falling back to acceptTransfer")
                return self.accept_transfer(land_id)
            else:
                logger.error(f"Transfer completion failed for {land_id}: {str(e)}")
                raise BlockchainServiceError("Failed to complete transfer") from e

    def reject_transfer(self, land_id: str) -> str:
        """Reject a transfer - FIXED: Use string parameters"""
        try:
            # Use string parameter directly
            tx = self.build_transaction(
                self.contract.functions.rejectTransfer(land_id)
            )
            return self.send_transaction(tx)
        except Exception as e:
            if "rejectTransfer" in str(e):
                # Fallback to cancelTransfer
                logger.warning("rejectTransfer failed, trying cancelTransfer")
                return self.cancel_transfer(land_id)
            else:
                logger.error(f"Transfer rejection failed for {land_id}: {str(e)}")
                raise BlockchainServiceError("Failed to reject transfer on blockchain") from e

    def get_metadata_versions(self, land_id: str) -> List[Dict]:
        """Get all metadata versions for a property - FIXED: Use string parameters"""
        try:
            # Use string parameter directly
            versions = self.call_function("getMetadataVersions", land_id)
                
            return [{
                'ipfs_hash': v[0],
                'timestamp': v[1],
                'uploader': v[2]
            } for v in versions]
        except Exception as e:
            logger.error(f"Failed to get metadata for {land_id}: {str(e)}")
            raise BlockchainServiceError("Failed to get metadata versions") from e

    def sync_all(self) -> Tuple[bool, str]:
        """Full synchronization of blockchain state with local database"""
        try:
            self.sync_parcels()
            self.sync_transfers()
            self.sync_metadata()
            return True, "Synchronization completed successfully"
        except Exception as e:
            logger.error(f"Synchronization failed: {str(e)}")
            return False, str(e)

    def sync_parcels(self) -> None:
        """Sync all parcels from blockchain to local database"""
        try:
            User = apps.get_model('registration', 'User')
            Parcel = apps.get_model('registration', 'Parcel')
            
            all_users = User.objects.exclude(blockchain_address=None)
            for user in all_users:
                parcel_keys = self.get_parcels_by_owner(user.blockchain_address)
                for key in parcel_keys:
                    self.sync_parcel(key)
        except Exception as e:
            logger.error(f"Parcel synchronization failed: {str(e)}")
            raise

    def sync_parcel(self, land_key: str) -> None:
        """Sync a single parcel's details"""
        try:
            Parcel = apps.get_model('registration', 'Parcel')
            User = apps.get_model('registration', 'User')
            
            parcel_data = self.get_parcel(land_key)
            if not parcel_data:
                return
                
            # Find owner by blockchain address
            owner_address = parcel_data['owner'].lower()
            try:
                owner = User.objects.get(blockchain_address=owner_address)
            except User.DoesNotExist:
                logger.warning(f"Owner not found for address {owner_address}, skipping parcel sync")
                return
            
            Parcel.objects.update_or_create(
                land_id=parcel_data['id'],
                defaults={
                    'owner': owner,
                    'size': float(parcel_data['size']),
                    'blockchain_hash': land_key,
                    'is_frozen': parcel_data['is_frozen'],
                    'document_ipfs_hash': parcel_data['document_hash'],
                    'created_at': timezone.datetime.fromtimestamp(parcel_data['created_at']),
                    'updated_at': timezone.datetime.fromtimestamp(parcel_data['updated_at'])
                }
            )
        except Exception as e:
            logger.error(f"Failed to sync parcel {land_key}: {str(e)}")
            raise

    def process_new_events(self) -> None:
        """Process new blockchain events since last check"""
        try:
            for event_name, event_filter in self.event_filters.items():
                if event_filter is None:
                    continue
                for event in event_filter.get_new_entries():
                    if event_name == 'TransferInitiated':
                        self._process_transfer_initiated(event)
                    elif event_name == 'TransferAccepted':
                        self._process_transfer_accepted(event)
                    elif event_name == 'MetadataVersioned':
                        self._process_metadata_versioned(event)
        except Exception as e:
            logger.error(f"Event processing failed: {str(e)}")
            raise

    def _process_transfer_initiated(self, event) -> None:
        """Process a TransferInitiated event"""
        try:
            TransferModel = apps.get_model('registration', 'Transfer')
            PendingTransferModel = apps.get_model('registration', 'PendingTransfer')
            ParcelModel = apps.get_model('registration', 'Parcel')
            
            # Convert bytes32 land_id back to string
            land_id = self._bytes32_to_string(event.args.landId) if isinstance(event.args.landId, bytes) else str(event.args.landId)
            
            try:
                parcel_obj = ParcelModel.objects.get(land_id=land_id)
            except ParcelModel.DoesNotExist:
                logger.warning(f"Parcel {land_id} not found in database, skipping event processing")
                return
            
            # Get recipient address from event
            recipient_address = event.args.to.lower()
            UserModel = apps.get_model('registration', 'User')
            
            try:
                recipient = UserModel.objects.get(blockchain_address=recipient_address)
            except UserModel.DoesNotExist:
                logger.warning(f"Recipient user with address {recipient_address} not found")
                return
            
            # Find or create transfer record with transaction hash
            transfer, created = TransferModel.objects.get_or_create(
                parcel=parcel_obj,
                status=TransferModel.PENDING,
                recipient=recipient,
                defaults={
                    'sender': parcel_obj.owner,
                    'transaction_hash': event.transactionHash.hex()
                }
            )
            
            # If transfer already existed, update the transaction hash
            if not created:
                transfer.transaction_hash = event.transactionHash.hex()
                transfer.save()
            
            PendingTransferModel.objects.update_or_create(
                transfer=transfer,
                defaults={
                    'blockchain_tx_id': event.transactionHash.hex(),
                    'is_confirmed': True,
                    'last_checked': timezone.now()
                }
            )
        except Exception as e:
            logger.error(f"Failed to process TransferInitiated event: {str(e)}")
            raise

    def _process_transfer_accepted(self, event) -> None:
        """Process a TransferAccepted event"""
        try:
            ParcelModel = apps.get_model('registration', 'Parcel')
            TransferModel = apps.get_model('registration', 'Transfer')
            TransferHistoryModel = apps.get_model('registration', 'TransferHistory')
            UserModel = apps.get_model('registration', 'User')
            PendingTransferModel = apps.get_model('registration', 'PendingTransfer')
            
            # Convert bytes32 land_id back to string
            land_id = self._bytes32_to_string(event.args.landId) if isinstance(event.args.landId, bytes) else str(event.args.landId)
            
            try:
                parcel_obj = ParcelModel.objects.get(land_id=land_id)
            except ParcelModel.DoesNotExist:
                logger.warning(f"Parcel {land_id} not found in database, skipping event processing")
                return
            
            # Find the recipient user
            recipient_address = event.args.to.lower()
            try:
                recipient = UserModel.objects.get(blockchain_address=recipient_address)
            except UserModel.DoesNotExist:
                logger.warning(f"Recipient user with address {recipient_address} not found")
                return
            
            # Find the transfer
            try:
                transfer = TransferModel.objects.get(parcel=parcel_obj, status=TransferModel.PENDING)
            except TransferModel.DoesNotExist:
                logger.warning(f"No pending transfer found for parcel {land_id}")
                return
            except TransferModel.MultipleObjectsReturned:
                transfer = TransferModel.objects.filter(parcel=parcel_obj, status=TransferModel.PENDING).latest('created_at')
            
            # Update parcel ownership
            old_owner = parcel_obj.owner
            parcel_obj.owner = recipient
            parcel_obj.save()
            
            # Update transfer status
            transfer.status = TransferModel.ACCEPTED
            transfer.recipient = recipient
            transfer.transaction_hash = event.transactionHash.hex()
            transfer.accepted_at = timezone.now()
            transfer.save()
            
            # Create transfer history record
            TransferHistoryModel.objects.create(
                transfer=transfer,
                from_user=old_owner,
                to_user=recipient,
                parcel=parcel_obj,
                status=TransferModel.ACCEPTED,
                transaction_hash=event.transactionHash.hex(),
                notes="Transfer accepted on blockchain"
            )
            
            # Clear any pending transfer
            PendingTransferModel.objects.filter(transfer=transfer).delete()
        except Exception as e:
            logger.error(f"Failed to process TransferAccepted event: {str(e)}")
            raise

    def _process_transfer_rejected(self, event) -> None:
        """Process a TransferRejected event"""
        try:
            ParcelModel = apps.get_model('registration', 'Parcel')
            TransferModel = apps.get_model('registration', 'Transfer')
            TransferHistoryModel = apps.get_model('registration', 'TransferHistory')
            PendingTransferModel = apps.get_model('registration', 'PendingTransfer')
            
            # Convert bytes32 land_id back to string
            land_id = self._bytes32_to_string(event.args.landId) if isinstance(event.args.landId, bytes) else str(event.args.landId)
            
            try:
                parcel_obj = ParcelModel.objects.get(land_id=land_id)
            except ParcelModel.DoesNotExist:
                logger.warning(f"Parcel {land_id} not found in database, skipping event processing")
                return
            
            # Find the transfer
            try:
                transfer = TransferModel.objects.get(parcel=parcel_obj, status=TransferModel.PENDING)
            except TransferModel.DoesNotExist:
                logger.warning(f"No pending transfer found for parcel {land_id}")
                return
            except TransferModel.MultipleObjectsReturned:
                transfer = TransferModel.objects.filter(parcel=parcel_obj, status=TransferModel.PENDING).latest('created_at')
            
            # Update transfer status
            transfer.status = TransferModel.REJECTED
            transfer.transaction_hash = event.transactionHash.hex()
            transfer.rejected_at = timezone.now()
            transfer.save()
            
            # Create transfer history record
            TransferHistoryModel.objects.create(
                transfer=transfer,
                from_user=transfer.sender,
                to_user=transfer.recipient,
                parcel=parcel_obj,
                status=TransferModel.REJECTED,
                transaction_hash=event.transactionHash.hex(),
                notes="Transfer rejected on blockchain"
            )
            
            # Clear any pending transfer
            PendingTransferModel.objects.filter(transfer=transfer).delete()
            
            logger.info(f"✅ Transfer rejected for parcel {land_id}: {event.transactionHash.hex()}")
            
        except Exception as e:
            logger.error(f"Failed to process TransferRejected event: {str(e)}")
            raise

    def _process_metadata_versioned(self, event) -> None:
        """Process a MetadataVersioned event"""
        try:
            ParcelModel = apps.get_model('registration', 'Parcel')
            ParcelDocumentModel = apps.get_model('registration', 'ParcelDocument')
            
            # Convert bytes32 land_id back to string
            land_id = self._bytes32_to_string(event.args.landId) if isinstance(event.args.landId, bytes) else str(event.args.landId)
            
            try:
                parcel_obj = ParcelModel.objects.get(land_id=land_id)
            except ParcelModel.DoesNotExist:
                logger.warning(f"Parcel {land_id} not found in database, skipping event processing")
                return
            
            ParcelDocumentModel.objects.update_or_create(
                parcel=parcel_obj,
                ipfs_hash=event.args.ipfsHash,
                defaults={
                    'document_type': 'OTHER',
                    'uploaded_by': parcel_obj.owner,
                    'uploaded_at': timezone.datetime.fromtimestamp(event.args.timestamp)
                }
            )
        except Exception as e:
            logger.error(f"Failed to process MetadataVersioned event: {str(e)}")
            raise

    def verify_metadata_integrity(self, parcel_document) -> Tuple[bool, Dict]:
        """
        Verify that a document exists on the blockchain
        and matches the local record
        """
        try:
            blockchain_versions = self.get_metadata_versions(parcel_document.parcel.land_id)
            
            for v in blockchain_versions:
                if v['ipfs_hash'] == parcel_document.ipfs_hash:
                    return True, {
                        'blockchain_timestamp': v['timestamp'],
                        'matches': True
                    }
            
            return False, {'error': 'Document not found on blockchain'}
        except Exception as e:
            return False, {'error': str(e)}

    def get_latest_blocks(self, count=10):
        """Retrieve the latest blocks from the blockchain"""
        latest_block = self.w3.eth.block_number
        
    def get_parcel(self, parcel_id):
        """Get parcel details from blockchain using string parameter"""
        try:
            # Try getParcel function that accepts string
            parcel_data = self.contract.functions.getParcel(parcel_id).call()
            
            # Check if parcel exists (first element should be non-empty string)
            if parcel_data and parcel_data[0]:  # outLandId
                return {
                    'exists': True,
                    'land_id': parcel_data[0],
                    'land_key': parcel_data[1],
                    'owner': parcel_data[2],
                    'frozen': parcel_data[3],
                    'latest_ipfs_hash': parcel_data[4],
                    'created_at': parcel_data[5],
                    'updated_at': parcel_data[6],
                    'metadata_versions': parcel_data[7]
                }
            return None
        except Exception as e:
            print(f"Error getting parcel {parcel_id}: {e}")
            return None
    
    def get_parcel_by_key(self, parcel_key_bytes):
        """Get parcel details using bytes32 key (alternative method)"""
        try:
            parcel_data = self.contract.functions.getParcelByKey(parcel_key_bytes).call()
            
            if parcel_data and parcel_data[0]:
                return {
                    'exists': True,
                    'land_id': parcel_data[0],
                    'land_key': parcel_data[1],
                    'owner': parcel_data[2],
                    'frozen': parcel_data[3],
                    'latest_ipfs_hash': parcel_data[4],
                    'created_at': parcel_data[5],
                    'updated_at': parcel_data[6],
                    'metadata_versions': parcel_data[7]
                }
            return None
        except Exception as e:
            print(f"Error getting parcel by key: {e}")
            return None
    
    def is_parcel_registered(self, parcel_id):
        """Check if parcel is registered - uses string parameter"""
        try:
            return self.contract.functions.isParcelRegistered(parcel_id).call()
        except Exception as e:
            print(f"Error checking parcel registration for {parcel_id}: {e}")
            return False
    
    def get_pending_transfer(self, parcel_id):
        """Get pending transfer details"""
        try:
            transfer_data = self.contract.functions.getPendingTransfer(parcel_id).call()
            return {
                'from': transfer_data[0],
                'to': transfer_data[1],
                'ipfs_hash': transfer_data[2],
                'active': transfer_data[3],
                'initiated_at': transfer_data[4]
            }
        except Exception as e:
            print(f"Error getting pending transfer: {e}")
            return None