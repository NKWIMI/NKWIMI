# blockchain_service.py - FIXED VERSION with proper user wallet switching
import os
import json
import logging
from typing import Optional, Tuple, Dict, Any, List
from web3 import Web3, exceptions
from eth_account import Account
from eth_utils import to_checksum_address
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

class BlockchainServiceError(Exception):
    pass

class BlockchainService:
    _abi_cache = None
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, user=None):
        if not hasattr(self, 'w3'):
            self.user = user
            self.setup_web3_connection()
            self.setup_account(user)
            if self.w3:
                self._ensure_minimum_balance()
                self.setup_contract()

    def setup_web3_connection(self):
        blockchain_config = getattr(settings, "BLOCKCHAIN_CONFIG", {})
        rpc_url = blockchain_config.get('GANACHE_URL', "http://127.0.0.1:7545")
        
        if not rpc_url:
            logger.warning("⚠ No RPC URL configured. Using mock blockchain mode.")
            self.w3 = None
            self.contract = None
            return

        try:
            self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 60}))
            if not self.w3.is_connected():
                raise ConnectionError(f"Failed to connect to Ethereum node at {rpc_url}")
            
            logger.info(f"✅ Connected to Ethereum node at {rpc_url} (Chain ID: {self.w3.eth.chain_id})")
        except Exception as e:
            logger.error(f"Web3 connection error: {str(e)}")
            self.w3 = None
            self.contract = None

    def setup_account(self, user=None):
        """Simplified account setup that prioritizes user wallets"""
        if user is not None:
            self.user = user
            
        if not self.w3:
            self.account = None
            self.private_key = None
            return
            
        try:
            # Always try to use user's wallet first
            if self.user and self.user.is_authenticated:
                logger.info(f"🔍 Setting up wallet for authenticated user: {self.user.username}")
                
                # Check if user has blockchain address
                if hasattr(self.user, 'blockchain_address') and self.user.blockchain_address:
                    logger.info(f"📋 User has blockchain address: {self.user.blockchain_address}")
                    
                    # Try to get private key from profile
                    private_key = self._get_user_private_key()
                    
                    if private_key:
                        self.private_key = private_key
                        self._setup_account_from_private_key("user wallet")
                        return
                    else:
                        logger.warning(f"⚠ No private key found for user {self.user.username}")
                        # Try to assign a Ganache wallet
                        if self._assign_ganache_wallet_to_user(self.user):
                            private_key = self._get_user_private_key()
                            if private_key:
                                self.private_key = private_key
                                self._setup_account_from_private_key("new ganache wallet")
                                return
                
                logger.warning(f"⚠ User {self.user.username} has no usable wallet, falling back to system wallet")
            
            # Fallback to system wallet
            self._fallback_to_system_wallet()
                    
        except Exception as e:
            logger.error(f"Account setup failed: {str(e)}")
            self._fallback_to_system_wallet()

    def _get_user_private_key(self):
        """Extract private key from user - FIXED: No UserProfile dependency"""
        try:
            # Check if user has encrypted_private_key directly (no profile needed)
            if hasattr(self.user, 'encrypted_private_key') and self.user.encrypted_private_key:
                try:
                    # You'll need to implement decryption based on your setup
                    private_key = self._decrypt_private_key(self.user.encrypted_private_key)
                    logger.info(f"🔑 Retrieved private key from user")
                    return private_key
                except Exception as e:
                    logger.warning(f"⚠ Could not decrypt user's private key: {e}")
            
            # Try to find private key in Ganache using user's blockchain_address
            if hasattr(self.user, 'blockchain_address') and self.user.blockchain_address:
                private_key = self._find_private_key_in_ganache(self.user.blockchain_address)
                if private_key:
                    logger.info(f"🔑 Found private key in Ganache for {self.user.blockchain_address}")
                    # Save it to user for future use
                    if hasattr(self.user, 'encrypted_private_key'):
                        self.user.encrypted_private_key = self._encrypt_private_key(private_key)
                        self.user.save()
                    return private_key
                    
        except Exception as e:
            logger.warning(f"Error getting user private key: {e}")
            
        return None

    def _decrypt_private_key(self, encrypted_key):
        """Decrypt private key - implement based on your encryption method"""
        # This is a placeholder - implement your actual decryption logic
        try:
            # If you're using Django's crypto functions:
            from django.core import signing
            return signing.loads(encrypted_key)
        except:
            # If it's stored in plain text (for development)
            return encrypted_key

    def _encrypt_private_key(self, private_key):
        """Encrypt private key - implement based on your encryption method"""
        # This is a placeholder - implement your actual encryption logic
        try:
            from django.core import signing
            return signing.dumps(private_key)
        except:
            return private_key  # Fallback to plain text for development

    def _setup_account_from_private_key(self, account_source):
        """Set up account from private key with validation"""
        if self.private_key:
            cleaned_key = self.private_key.strip().replace("0x", "")
            if len(cleaned_key) == 64 and all(c in '0123456789abcdefABCDEF' for c in cleaned_key):
                self.account = self.w3.eth.account.from_key(cleaned_key)
                logger.info(f"✅ Account loaded from {account_source}: {self.account.address}")
                
                # Fund account if needed in development
                if settings.DEBUG and self.w3.eth.chain_id == 1337:
                    self._ensure_minimum_balance()
            else:
                raise ImproperlyConfigured("Invalid private key format")
        else:
            logger.error("❌ No private key available")
            self.account = None

    def _ensure_minimum_balance(self):
        """Ensure account has minimum balance for transactions"""
        try:
            if not self.account:
                return
                
            balance = self.w3.eth.get_balance(self.account.address)
            min_balance = self.w3.to_wei(0.1, 'ether')
            
            if balance < min_balance:
                logger.warning(f"⚠ Low balance: {self.w3.from_wei(balance, 'ether')} ETH")
                self.fund_user_account(self.account.address, 1.0)
        except Exception as e:
            logger.error(f"Balance check failed: {str(e)}")

    def switch_to_user_wallet(self, user):
        """CRITICAL FIX: Switch to a specific user's wallet for transactions"""
        try:
            if not self.w3:
                logger.error("❌ No blockchain connection available")
                return False
                
            logger.info(f"🔄 Switching to user wallet: {user.username}")
            
            # Get user's private key
            private_key = self._get_user_private_key_for_user(user)
            
            if not private_key:
                logger.error(f"❌ No private key found for user {user.username}")
                return False
            
            # Set up the account
            cleaned_key = private_key.strip().replace("0x", "")
            if len(cleaned_key) == 64 and all(c in '0123456789abcdefABCDEF' for c in cleaned_key):
                self.account = self.w3.eth.account.from_key(cleaned_key)
                self.private_key = private_key
                self.user = user
                
                logger.info(f"✅ Switched to user wallet: {user.username} -> {self.account.address}")
                
                # Update contract with new account context
                if self.contract:
                    self.setup_contract()
                    
                return True
            else:
                logger.error(f"❌ Invalid private key format for user {user.username}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to switch to user wallet: {str(e)}")
            return False

    def _get_user_private_key_for_user(self, user):
        """Get private key for a specific user - FIXED: No UserProfile dependency"""
        try:
            # Check user model directly for encrypted_private_key
            if hasattr(user, 'encrypted_private_key') and user.encrypted_private_key:
                try:
                    return self._decrypt_private_key(user.encrypted_private_key)
                except Exception as e:
                    logger.warning(f"⚠ Could not decrypt private key for {user.username}: {e}")
            
            # Try to find in Ganache using user's blockchain_address
            if hasattr(user, 'blockchain_address') and user.blockchain_address:
                return self._find_private_key_in_ganache(user.blockchain_address)
                
        except Exception as e:
            logger.error(f"Error getting private key for user {user.username}: {e}")
            
        return None

    def switch_to_specific_address(self, address):
        """Switch to a specific Ethereum address using known private keys"""
        try:
            if not self.w3:
                return False
                
            private_key = self._find_private_key_in_ganache(address)
            if private_key:
                self.account = self.w3.eth.account.from_key(private_key)
                self.private_key = private_key
                self.user = None  # Clear user context since we're using specific address
                
                logger.info(f"✅ Switched to specific address: {self.account.address}")
                return True
            else:
                logger.error(f"❌ No private key found for address: {address}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to switch to specific address: {str(e)}")
            return False

    def _fallback_to_system_wallet(self):
        try:
            blockchain_config = getattr(settings, "BLOCKCHAIN_CONFIG", {})
            if blockchain_config.get('ETHEREUM_PRIVATE_KEY'):
                self.private_key = blockchain_config['ETHEREUM_PRIVATE_KEY']
                cleaned_key = self.private_key.strip().replace("0x", "")
                self.account = self.w3.eth.account.from_key(cleaned_key)
                logger.warning("⚠ Using system wallet - user transactions may fail!")
                return True
            return False
        except Exception as e:
            logger.error(f"Fallback failed: {str(e)}")
            return False

    def _find_private_key_in_ganache(self, address):
        ganache_private_keys = [
            "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",  # 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
            "59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",  # 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
            "5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",  # 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
            "7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",  # 0x90F79bf6EB2c4f870365E785982E1f101E93b906
            "47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",  # 0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65
            "8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba",  # 0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc
            "92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e",  # 0x976EA74026E726554dB657fA54763abd0C3a0aa9
            "4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356",  # 0x14dC79964da2C08b23698B3D3cc7Ca32193d9955
            "dbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97",  # 0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f
            "2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6",  # 0xa0Ee7A142d267C1f36714E4a8F75612F20a79720
        ]
        
        target_address = address.lower()
        for private_key in ganache_private_keys:
            test_account = self.w3.eth.account.from_key(private_key)
            if test_account.address.lower() == target_address:
                return private_key
        return None

    def _assign_ganache_wallet_to_user(self, user):
        """FIXED: Assign Ganache wallet without UserProfile dependency"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Get all used addresses from User model directly
            used_addresses = set()
            for existing_user in User.objects.exclude(blockchain_address__isnull=True).exclude(blockchain_address=''):
                if existing_user.blockchain_address:
                    used_addresses.add(existing_user.blockchain_address.lower())
            
            ganache_private_keys = [
                "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
                "59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d", 
                "5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
                "7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
                "47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",
                "8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba",
                "92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e",
                "4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356",
                "dbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97",
                "2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6",
            ]
            
            for private_key in ganache_private_keys:
                account = self.w3.eth.account.from_key(private_key)
                if account.address.lower() not in used_addresses:
                    # Assign wallet directly to User model
                    user.blockchain_address = account.address
                    user.encrypted_private_key = self._encrypt_private_key(private_key)
                    user.save()
                    
                    if settings.DEBUG:
                        self.fund_user_account(account.address)
                    
                    logger.info(f"✅ Assigned Ganache wallet to {user.username}: {account.address}")
                    return True
            
            logger.error("❌ No available Ganache accounts")
            return False
            
        except Exception as e:
            logger.error(f"Failed to assign Ganache wallet: {str(e)}")
            return False

    def setup_contract(self):
        if not self.w3:
            return
            
        try:
            blockchain_config = getattr(settings, "BLOCKCHAIN_CONFIG", {})
            contract_address = blockchain_config.get('CONTRACT_ADDRESS', '')
            
            if not contract_address:
                raise ImproperlyConfigured("CONTRACT_ADDRESS not found")

            self.contract_address = to_checksum_address(contract_address)
            abi = self.get_contract_abi()
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=abi)
            
            # Verify contract
            code = self.w3.eth.get_code(self.contract_address)
            if code == b'':
                raise ValueError("No code at contract address")
                
            logger.info(f"✅ Contract verified: {self.contract_address}")
        
        except Exception as e:
            logger.error(f"Contract setup failed: {str(e)}")
            self.contract = None

    def get_contract_abi(self):
        if BlockchainService._abi_cache:
            return BlockchainService._abi_cache

        try:
            blockchain_config = getattr(settings, "BLOCKCHAIN_CONFIG", {})
            abi_path = blockchain_config.get('CONTRACT_ABI_PATH')
            
            if not abi_path or not os.path.exists(abi_path):
                raise FileNotFoundError(f"ABI file not found: {abi_path}")

            with open(abi_path, "r") as f:
                contract_data = json.load(f)
                
                if isinstance(contract_data, dict):
                    if "abi" in contract_data:
                        abi = contract_data["abi"]
                    else:
                        raise ValueError("No ABI found in JSON")
                else:
                    abi = contract_data
                    
                BlockchainService._abi_cache = abi
                return abi
        
        except Exception as e:
            logger.error(f"ABI loading failed: {str(e)}")
            raise BlockchainServiceError("Failed to load ABI")

    # TRANSFER METHODS WITH PROPER WALLET HANDLING
    def initiate_transfer(self, parcel_id: str, to_address: str, document_hash: str = "") -> str:
        """Initiate a parcel transfer on blockchain - WITH WALLET VALIDATION"""
        try:
            logger.info(f"🔍 Starting transfer initiation: {parcel_id} to {to_address}")
            
            if not self.w3 or not self.contract:
                error_msg = "No blockchain connection available"
                logger.error(f"❌ {error_msg}")
                raise BlockchainServiceError(error_msg)
                
            if not self.account:
                error_msg = "No account available for transaction"
                logger.error(f"❌ {error_msg}")
                raise BlockchainServiceError(error_msg)

            # Convert to checksum address
            to_address_checksum = to_checksum_address(to_address)
            logger.info(f"✅ Recipient address: {to_address_checksum}")
            logger.info(f"✅ Sender address: {self.account.address}")
            logger.info(f"✅ Document hash: {document_hash}")

            # CRITICAL: Validate ownership using current wallet
            if not self.validate_ownership(parcel_id, self.account.address):
                error_msg = f"Parcel {parcel_id} not owned by {self.account.address}"
                logger.error(f"❌ {error_msg}")
                raise BlockchainServiceError(error_msg)

            # Use initiateTransfer function
            function_call = self.contract.functions.initiateTransfer(
                parcel_id, 
                to_address_checksum, 
                document_hash or ""
            )
            
            logger.info("🔄 Building transfer transaction...")
            
            # Estimate gas
            try:
                gas_estimate = function_call.estimate_gas({
                    'from': self.account.address
                })
                logger.info(f"✅ Gas estimate: {gas_estimate}")
            except Exception as e:
                logger.warning(f"⚠ Gas estimation failed: {e}")
                gas_estimate = 300000  # Safe default

            # Build transaction
            transaction = function_call.build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': int(gas_estimate * 1.3),
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })

            logger.info(f"📝 Transfer transaction built: gas={transaction['gas']}")

            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            
            # Get raw transaction (Web3 v6 compatible)
            if hasattr(signed_txn, 'raw_transaction'):
                raw_tx = signed_txn.raw_transaction
            elif hasattr(signed_txn, 'rawTransaction'):
                raw_tx = signed_txn.rawTransaction
            else:
                raise BlockchainServiceError("Could not find raw transaction data")
            
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            logger.info(f"📤 Transfer transaction sent: {tx_hash.hex()}")

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            logger.info(f"📦 Transfer transaction mined in block: {receipt.blockNumber}")

            if receipt.status == 1:
                logger.info(f"✅ Transfer initiated SUCCESSFUL: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                error_msg = f"Transfer initiation failed with status 0: {tx_hash.hex()}"
                logger.error(f"❌ {error_msg}")
                raise BlockchainServiceError(error_msg)

        except exceptions.ContractLogicError as e:
            error_msg = f"Contract logic error in transfer: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise BlockchainServiceError(error_msg)
            
        except Exception as e:
            error_msg = f"Transfer initiation failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise BlockchainServiceError(error_msg)

    def validate_ownership(self, parcel_id: str, expected_owner: str) -> bool:
        """Validate parcel ownership - FIXED for proper wallet usage"""
        try:
            if not self.w3 or not self.contract:
                logger.warning("No blockchain connection - skipping ownership validation")
                return True

            # Get parcel data from blockchain
            parcel_data = self.get_parcel(parcel_id)
            if not parcel_data:
                logger.error(f"❌ Parcel {parcel_id} not found on blockchain")
                return False
                
            blockchain_owner = parcel_data.get('owner', '').lower()
            expected_owner_clean = expected_owner.lower()
            
            # Get current wallet address
            current_wallet_address = self.account.address.lower() if self.account else ""
            
            logger.info(f"🔍 Ownership check - Parcel: {parcel_id}")
            logger.info(f"   Blockchain owner: {blockchain_owner}")
            logger.info(f"   Expected owner: {expected_owner_clean}")
            logger.info(f"   Current wallet address: {current_wallet_address}")
            
            # Check if the expected owner matches blockchain owner
            is_owner = blockchain_owner == expected_owner_clean
            
            if not is_owner:
                logger.error(f"❌ Ownership mismatch! Parcel owned by {blockchain_owner}, but {expected_owner_clean} claimed ownership")
                return False
            
            # Additional check: verify transaction sender matches parcel owner
            if self.account and self.account.address.lower() != expected_owner_clean:
                logger.error(f"❌ CRITICAL: Transaction sender {self.account.address} doesn't match parcel owner {expected_owner_clean}")
                logger.error(f"💡 This means we're using the wrong wallet! Should be using: {expected_owner_clean}")
                return False
            
            logger.info(f"✅ Ownership validated: {parcel_id} belongs to {expected_owner_clean}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating ownership: {str(e)}")
            return False

    # Other methods remain the same...
    def register_parcel(self, land_id: str, owner_address: str, document_hash: str = "") -> str:
        """Register a new parcel on the blockchain"""
        logger.info(f"🚀 Starting blockchain registration for parcel: {land_id}")
        
        if not self.w3:
            error_msg = "No blockchain connection available"
            logger.error(f"❌ {error_msg}")
            raise BlockchainServiceError(error_msg)
        
        if not self.contract:
            error_msg = "No contract configured"
            logger.error(f"❌ {error_msg}")
            raise BlockchainServiceError(error_msg)
            
        if not self.account:
            error_msg = "No account available for transaction"
            logger.error(f"❌ {error_msg}")
            raise BlockchainServiceError(error_msg)

        try:
            # Convert to checksum address
            owner_address_checksum = to_checksum_address(owner_address)
            logger.info(f"✅ Owner address: {owner_address_checksum}")
            logger.info(f"✅ Sender address: {self.account.address}")
            logger.info(f"✅ Document hash: {document_hash}")

            # Check account balance
            balance = self.w3.eth.get_balance(self.account.address)
            balance_eth = self.w3.from_wei(balance, 'ether')
            logger.info(f"💰 Account balance: {balance_eth} ETH")
            
            if balance < self.w3.to_wei(0.01, 'ether'):
                error_msg = f"Insufficient balance: {balance_eth} ETH"
                logger.error(f"❌ {error_msg}")
                raise BlockchainServiceError(error_msg)

            # Check if parcel already exists
            try:
                existing = self.get_parcel(land_id)
                if existing and existing.get('exists'):
                    error_msg = f"Parcel {land_id} already registered on blockchain"
                    logger.error(f"❌ {error_msg}")
                    raise BlockchainServiceError(error_msg)
            except Exception as e:
                logger.warning(f"⚠ Could not check existing parcel: {e}")

            # Use the correct function signature (3 parameters)
            function_call = self.contract.functions.registerParcel(
                land_id, 
                owner_address_checksum, 
                document_hash or ""
            )
            
            logger.info("🔄 Building transaction...")
            
            # Estimate gas
            try:
                gas_estimate = function_call.estimate_gas({
                    'from': self.account.address
                })
                logger.info(f"✅ Gas estimate: {gas_estimate}")
            except Exception as e:
                logger.warning(f"⚠ Gas estimation failed: {e}")
                gas_estimate = 400000  # Safe default

            # Build transaction
            transaction = function_call.build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': int(gas_estimate * 1.3),  # 30% buffer
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })

            logger.info(f"📝 Transaction built: gas={transaction['gas']}, gasPrice={transaction['gasPrice']}")

            # Sign transaction (Web3 v6 compatible)
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            
            # Get the raw transaction data
            if hasattr(signed_txn, 'raw_transaction'):
                raw_tx = signed_txn.raw_transaction  # Web3 v6
            elif hasattr(signed_txn, 'rawTransaction'):
                raw_tx = signed_txn.rawTransaction  # Web3 v5
            else:
                raise BlockchainServiceError("Could not find raw transaction data")
            
            # Send raw transaction
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            logger.info(f"📤 Transaction sent: {tx_hash.hex()}")

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            logger.info(f"📦 Transaction mined in block: {receipt.blockNumber}")

            if receipt.status == 1:
                logger.info(f"✅ Parcel registration SUCCESSFUL: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                error_msg = f"Transaction failed with status 0: {tx_hash.hex()}"
                logger.error(f"❌ {error_msg}")
                raise BlockchainServiceError(error_msg)

        except exceptions.ContractLogicError as e:
            error_msg = f"Contract logic error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise BlockchainServiceError(error_msg)
            
        except exceptions.TimeExhausted as e:
            error_msg = f"Transaction timeout: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise BlockchainServiceError(error_msg)
            
        except Exception as e:
            error_msg = f"Registration failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise BlockchainServiceError(error_msg)

    def get_parcel(self, parcel_id):
        """Get parcel details from blockchain"""
        try:
            if not self.w3 or not self.contract:
                return None
            
            # Try different function names
            functions_to_try = ['getParcel', 'parcels', 'getLand', 'lands']
            
            for func_name in functions_to_try:
                try:
                    if hasattr(self.contract.functions, func_name):
                        parcel_data = getattr(self.contract.functions, func_name)(parcel_id).call()
                        if parcel_data and (isinstance(parcel_data, tuple) or isinstance(parcel_data, list)):
                            return {
                                'exists': True,
                                'land_id': parcel_data[0] if parcel_data[0] else parcel_id,
                                'owner': parcel_data[2] if len(parcel_data) > 2 else None,
                                'frozen': parcel_data[3] if len(parcel_data) > 3 else False,
                                'latest_ipfs_hash': parcel_data[4] if len(parcel_data) > 4 else "",
                                'created_at': parcel_data[5] if len(parcel_data) > 5 else 0,
                                'updated_at': parcel_data[6] if len(parcel_data) > 6 else 0
                            }
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting parcel {parcel_id}: {e}")
            return None

    def accept_transfer(self, parcel_id: str) -> str:
        """Accept a pending transfer - WITH PROPER WALLET VALIDATION"""
        try:
            logger.info(f"🔍 Accepting transfer for parcel: {parcel_id}")
            
            if not self.w3 or not self.contract:
                raise BlockchainServiceError("No blockchain connection available")
                
            if not self.account:
                raise BlockchainServiceError("No account available for transaction")

            # CRITICAL: Check if there's actually a pending transfer for this user
            pending_data = self.get_pending_transfer(parcel_id)
            if not pending_data or not pending_data.get('active', False):
                raise BlockchainServiceError("No active pending transfer found for this parcel")
            
            # CRITICAL: Verify that the current user is the intended recipient
            intended_recipient = pending_data.get('to', '').lower()
            current_user_address = self.account.address.lower()
            
            logger.info(f"🔍 Transfer acceptance validation:")
            logger.info(f"   Intended recipient: {intended_recipient}")
            logger.info(f"   Current user: {current_user_address}")
            
            if intended_recipient != current_user_address:
                error_msg = f"Only the intended recipient ({intended_recipient}) can accept this transfer. Current user: {current_user_address}"
                logger.error(f"❌ {error_msg}")
                raise BlockchainServiceError(error_msg)

            # Check account balance
            balance = self.w3.eth.get_balance(self.account.address)
            balance_eth = self.w3.from_wei(balance, 'ether')
            logger.info(f"💰 Account balance: {balance_eth} ETH")
            
            if balance < self.w3.to_wei(0.01, 'ether'):
                error_msg = f"Insufficient balance: {balance_eth} ETH"
                logger.error(f"❌ {error_msg}")
                raise BlockchainServiceError(error_msg)

            function_call = self.contract.functions.acceptTransfer(parcel_id)
            
            # Estimate gas properly
            try:
                gas_estimate = function_call.estimate_gas({
                    'from': self.account.address
                })
                logger.info(f"✅ Gas estimate: {gas_estimate}")
            except Exception as e:
                logger.warning(f"⚠ Gas estimation failed: {e}")
                gas_estimate = 300000  # Safe default

            # Build transaction with proper gas
            transaction = function_call.build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': int(gas_estimate * 1.3),  # 30% buffer
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })

            logger.info(f"📝 Acceptance transaction built: gas={transaction['gas']}")

            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            
            # Get raw transaction (Web3 v6 compatible)
            if hasattr(signed_txn, 'raw_transaction'):
                raw_tx = signed_txn.raw_transaction
            elif hasattr(signed_txn, 'rawTransaction'):
                raw_tx = signed_txn.rawTransaction
            else:
                raise BlockchainServiceError("Could not find raw transaction data")
            
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            logger.info(f"📤 Acceptance transaction sent: {tx_hash.hex()}")

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            logger.info(f"📦 Acceptance transaction mined in block: {receipt.blockNumber}")

            if receipt.status == 1:
                logger.info(f"✅ Transfer acceptance SUCCESSFUL: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                error_msg = f"Transfer acceptance failed with status 0: {tx_hash.hex()}"
                logger.error(f"❌ {error_msg}")
                raise BlockchainServiceError(error_msg)

        except exceptions.ContractLogicError as e:
            error_msg = f"Contract logic error in transfer acceptance: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise BlockchainServiceError(error_msg)
            
        except Exception as e:
            error_msg = f"Transfer acceptance failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise BlockchainServiceError(error_msg)

    def cancel_transfer(self, parcel_id: str) -> str:
        """Cancel a pending transfer"""
        try:
            logger.info(f"🔍 Cancelling transfer for parcel: {parcel_id}")
            
            if not self.w3 or not self.contract:
                raise BlockchainServiceError("No blockchain connection available")
                
            if not self.account:
                raise BlockchainServiceError("No account available for transaction")

            function_call = self.contract.functions.cancelTransfer(parcel_id)
            
            # Build transaction
            transaction = function_call.build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })

            # Sign and send
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            
            if hasattr(signed_txn, 'raw_transaction'):
                raw_tx = signed_txn.raw_transaction
            else:
                raw_tx = signed_txn.rawTransaction
                
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status == 1:
                logger.info(f"✅ Transfer cancelled: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                raise BlockchainServiceError("Transfer cancellation failed")
                
        except Exception as e:
            logger.error(f"Error cancelling transfer: {e}")
            raise BlockchainServiceError(f"Failed to cancel transfer: {str(e)}")

    def get_pending_transfer(self, parcel_id: str) -> Optional[Dict]:
        """Get pending transfer details"""
        try:
            if not self.w3 or not self.contract:
                return None
                
            transfer_data = self.contract.functions.getPendingTransfer(parcel_id).call()
            return {
                'from': transfer_data[0],
                'to': transfer_data[1],
                'ipfs_hash': transfer_data[2],
                'active': transfer_data[3],
                'initiated_at': transfer_data[4]
            }
        except Exception as e:
            logger.error(f"Error getting pending transfer: {e}")
            return None

    def fund_user_account(self, address, amount_eth=1.0):
        try:
            if not self.w3 or not settings.DEBUG:
                return False
                
            test_accounts = self.w3.eth.accounts
            if test_accounts:
                funder = test_accounts[0]
                amount_wei = self.w3.to_wei(amount_eth, 'ether')
                
                tx_hash = self.w3.eth.send_transaction({
                    'from': funder,
                    'to': address,
                    'value': amount_wei
                })
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                logger.info(f"⚡ Funded {address} with {amount_eth} ETH")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to fund account: {str(e)}")
            return False

    # Utility methods
    def build_transaction(self, function_call, value=0):
        if not self.w3:
            raise BlockchainServiceError("No blockchain connection")
            
        try:
            estimated_gas = function_call.estimate_gas({
                'from': self.account.address,
                'value': value
            })
            
            transaction = function_call.build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gasPrice': self.w3.eth.gas_price,
                'gas': int(estimated_gas * 1.2),
                'value': value
            })
            
            return transaction
        except Exception as e:
            logger.error(f"Transaction build failed: {str(e)}")
            raise BlockchainServiceError("Failed to build transaction") from e

    def send_transaction(self, transaction):
        if not self.w3:
            mock_hash = f"0x{'mock_tx_hash_for_dev' * 3}"[:66]
            logger.info(f"⚠ Mock transaction: {mock_hash}")
            return mock_hash
            
        try:
            signed_tx = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            
            # Web3 v6 compatibility
            if hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            elif hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            else:
                raise BlockchainServiceError("Could not find raw transaction data")
                
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 0:
                raise BlockchainServiceError("Transaction failed (status=0)")
            
            logger.info(f"✅ Transaction successful: {tx_hash.hex()}")
            return tx_hash.hex()
        
        except exceptions.TimeExhausted as e:
            logger.error(f"Transaction timeout: {str(e)}")
            raise BlockchainServiceError("Transaction timed out") from e
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            raise BlockchainServiceError(f"Failed to send transaction: {str(e)}") from e