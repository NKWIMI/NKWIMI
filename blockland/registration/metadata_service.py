import logging
from django.conf import settings
from web3 import Web3
from .blockchain_service import BlockchainService
from .file_hash_service import FileHashService

logger = logging.getLogger(__name__)

class MetadataService:
    def __init__(self, user=None):
        self.blockchain = BlockchainService(user)
        self.file_service = FileHashService(
            use_ipfs=bool(settings.IPFS_API_KEY and settings.IPFS_API_SECRET)
        )

    def add_metadata_version(self, parcel, document=None, ipfs_hash=None, description=""):
        """
        Add new metadata version to a parcel
        Args:
            parcel: Parcel instance
            document: File object to upload
            ipfs_hash: Existing IPFS hash (alternative to document)
            description: Human-readable description
        Returns:
            MetadataVersion instance
        """
        if not document and not ipfs_hash:
            raise ValueError("Either document or ipfs_hash must be provided")

        # Upload document to IPFS if provided
        if document:
            ipfs_hash = self.file_service.add_file(document)
            if not ipfs_hash:
                raise ValueError("Failed to upload document to IPFS")

        # Verify parcel exists on blockchain
        if not self.blockchain.is_parcel_registered(parcel.land_id):
            raise ValueError(f"Parcel {parcel.land_id} not registered on blockchain")

        # Add to blockchain
        receipt = self.blockchain.add_metadata_version(parcel.land_id, ipfs_hash)

        # Create local record
        metadata = MetadataVersion.objects.create(
            parcel=parcel,
            ipfs_hash=ipfs_hash,
            description=description,
            document=document,
            creator=self.blockchain.user
        )

        logger.info(
            f"Added metadata version {metadata.version_number} for {parcel.land_id} "
            f"(IPFS: {ipfs_hash}, Tx: {receipt.transactionHash.hex()})"
        )
        return metadata

    def get_metadata_content(self, ipfs_hash):
        """Retrieve metadata content from IPFS"""
        return self.file_service.get_file(ipfs_hash)

    def verify_metadata_integrity(self, metadata_version):
        """
        Verify that the metadata version exists on blockchain and matches local record
        Returns:
            bool: True if verification passes
            dict: Verification details
        """
        try:
            # Get blockchain record
            blockchain_versions = self.blockchain.get_metadata_versions(
                Web3.keccak(text=metadata_version.parcel.land_id)
            )
            
            # Find our version in blockchain records
            for v in blockchain_versions:
                if v['ipfs_hash'] == metadata_version.ipfs_hash:
                    return True, {
                        'blockchain_version': v['version'],
                        'timestamp': v['timestamp'],
                        'matches': True
                    }
            
            return False, {'error': 'Metadata not found on blockchain'}
        except Exception as e:
            return False, {'error': str(e)}

    def sync_metadata(self, parcel):
        """Synchronize metadata versions between blockchain and local database"""
        try:
            # Get blockchain versions
            blockchain_versions = self.blockchain.get_metadata_versions(
                Web3.keccak(text=parcel.land_id)
            )
            
            # Create/update local records
            for v in blockchain_versions:
                MetadataVersion.objects.update_or_create(
                    parcel=parcel,
                    version_number=v['version'],
                    defaults={
                        'ipfs_hash': v['ipfs_hash'],
                        'timestamp': v['timestamp']
                    }
                )
            
            return True, f"Synced {len(blockchain_versions)} metadata versions"
        except Exception as e:
            return False, str(e)