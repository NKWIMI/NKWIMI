// SPDX-License-Identifier: MIT
pragma solidity ^0.8.9;

contract LandRegistry {
    struct Parcel {
        bytes32 landKey;   // keccak256 of landId
        address owner;     // current owner
        bool frozen;       // block transfers when true
        string landId;     // original human-readable ID (for convenience)
        uint64 createdAt;
        uint64 updatedAt;
    }

    struct MetadataVersion {
        string ipfsHash;
        uint64 timestamp;
        uint256 version;
    }

    struct PendingTransfer {
        address from;
        address to;
        string ipfsHash;
        bool active;
        uint64 initiatedAt;
    }

    // Admin controls
    address public admin;
    
    // Primary storage keyed by landKey
    mapping(bytes32 => Parcel) private parcels;

    // Metadata versioning per landKey
    mapping(bytes32 => MetadataVersion[]) private metadataHistory;

    // Pending transfers per landKey
    mapping(bytes32 => PendingTransfer) private pendingTransfers;

    // Transfer history per landKey
    mapping(bytes32 => address[]) private transferHistory;

    // Owner -> list of landKeys they currently own
    mapping(address => bytes32[]) private parcelsByOwner;

    // landKey -> index of that key in parcelsByOwner[currentOwner]
    mapping(bytes32 => uint256) private ownerIndex;

    // Events
    event ParcelRegistered(bytes32 indexed landKey, string landId, address indexed owner, string ipfsHash);
    event TransferInitiated(bytes32 indexed landKey, address indexed from, address indexed to, string ipfsHash);
    event TransferAccepted(bytes32 indexed landKey, address indexed from, address indexed to);
    event ParcelFrozen(bytes32 indexed landKey, bool frozen, address indexed by);
    event MetadataVersioned(bytes32 indexed landKey, string ipfsHash, uint256 version, uint64 timestamp);
    event AdminTransferred(address indexed previousAdmin, address indexed newAdmin);

    // Modifiers
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }

    modifier onlyOwner(bytes32 landKey) {
        require(parcels[landKey].owner == msg.sender, "Only owner");
        _;
    }

    modifier notFrozen(bytes32 landKey) {
        require(!parcels[landKey].frozen, "Parcel frozen");
        _;
    }

    modifier parcelExists(bytes32 landKey) {
        require(parcels[landKey].owner != address(0), "Parcel not found");
        _;
    }

    constructor() {
        admin = msg.sender;
    }

    // ---------------------- Admin Functions ----------------------

    /// @notice Register a new parcel with initial owner and IPFS hash (admin only)
    function registerParcel(
        string calldata landId, 
        address initialOwner, 
        string calldata ipfsHash
    ) external onlyAdmin {
        bytes32 key = _keyOf(landId);
        require(bytes(landId).length > 0, "Land ID required");
        require(initialOwner != address(0), "Invalid initial owner");
        require(bytes(ipfsHash).length > 0, "IPFS hash required");
        require(parcels[key].owner == address(0), "Parcel already registered");

        parcels[key] = Parcel({
            landKey: key,
            owner: initialOwner,
            frozen: false,
            landId: landId,
            createdAt: uint64(block.timestamp),
            updatedAt: uint64(block.timestamp)
        });

        // Add initial metadata version
        metadataHistory[key].push(MetadataVersion({
            ipfsHash: ipfsHash,
            timestamp: uint64(block.timestamp),
            version: 1
        }));

        // Index owner holdings
        ownerIndex[key] = parcelsByOwner[initialOwner].length;
        parcelsByOwner[initialOwner].push(key);

        // Initialize transfer history
        transferHistory[key].push(initialOwner);

        emit ParcelRegistered(key, landId, initialOwner, ipfsHash);
        emit MetadataVersioned(key, ipfsHash, 1, uint64(block.timestamp));
    }

    /// @notice Admin override to transfer any parcel (admin only)
    function adminTransfer(
        string calldata landId, 
        address newOwner, 
        string calldata ipfsHash
    ) external onlyAdmin {
        bytes32 key = _keyOf(landId);
        require(parcels[key].owner != address(0), "Parcel not found");
        require(newOwner != address(0), "Invalid new owner");
        
        address currentOwner = parcels[key].owner;
        require(newOwner != currentOwner, "Cannot transfer to current owner");

        // Remove from current owner's list
        _removeFromOwnerList(currentOwner, key);

        // Update parcel ownership
        parcels[key].owner = newOwner;
        parcels[key].updatedAt = uint64(block.timestamp);

        // Add to new owner's list
        ownerIndex[key] = parcelsByOwner[newOwner].length;
        parcelsByOwner[newOwner].push(key);

        // Update transfer history
        transferHistory[key].push(newOwner);

        // Add metadata version if provided
        if (bytes(ipfsHash).length > 0) {
            uint256 newVersion = metadataHistory[key].length + 1;
            metadataHistory[key].push(MetadataVersion({
                ipfsHash: ipfsHash,
                timestamp: uint64(block.timestamp),
                version: newVersion
            }));
            emit MetadataVersioned(key, ipfsHash, newVersion, uint64(block.timestamp));
        }

        // Clear any pending transfer
        if (pendingTransfers[key].active) {
            delete pendingTransfers[key];
        }

        emit TransferAccepted(key, currentOwner, newOwner);
    }

    /// @notice Add a new metadata version (admin only)
    function addMetadataVersion(string calldata landId, string calldata ipfsHash) external onlyAdmin {
        bytes32 key = _keyOf(landId);
        require(parcels[key].owner != address(0), "Parcel not found");
        require(bytes(ipfsHash).length > 0, "IPFS hash required");

        uint256 newVersion = metadataHistory[key].length + 1;
        metadataHistory[key].push(MetadataVersion({
            ipfsHash: ipfsHash,
            timestamp: uint64(block.timestamp),
            version: newVersion
        }));

        parcels[key].updatedAt = uint64(block.timestamp);

        emit MetadataVersioned(key, ipfsHash, newVersion, uint64(block.timestamp));
    }

    /// @notice Freeze or unfreeze a parcel (admin only)
    function freezeParcel(string calldata landId, bool freeze_) external onlyAdmin {
        bytes32 key = _keyOf(landId);
        require(parcels[key].owner != address(0), "Parcel not found");

        parcels[key].frozen = freeze_;
        parcels[key].updatedAt = uint64(block.timestamp);

        emit ParcelFrozen(key, freeze_, msg.sender);
    }

    /// @notice Transfer admin role
    function transferAdmin(address newAdmin) external onlyAdmin {
        require(newAdmin != address(0), "Invalid new admin");
        address previousAdmin = admin;
        admin = newAdmin;
        emit AdminTransferred(previousAdmin, newAdmin);
    }

    // ---------------------- Transfer Functions ----------------------

    /// @notice Initiate a transfer to a new owner (current owner only)
    function initiateTransfer(
        string calldata landId, 
        address nominee, 
        string calldata ipfsHash
    ) external {
        bytes32 key = _keyOf(landId);
        
        require(parcels[key].owner != address(0), "Parcel not found");
        require(msg.sender == parcels[key].owner, "Only owner");
        require(!parcels[key].frozen, "Parcel frozen");
        require(nominee != address(0), "Invalid nominee");
        require(nominee != parcels[key].owner, "Cannot transfer to self");
        require(!pendingTransfers[key].active, "Transfer already pending");

        pendingTransfers[key] = PendingTransfer({
            from: msg.sender,
            to: nominee,
            ipfsHash: ipfsHash,
            active: true,
            initiatedAt: uint64(block.timestamp)
        });

        emit TransferInitiated(key, msg.sender, nominee, ipfsHash);
    }

    /// @notice Accept a pending transfer (nominee only)
    function acceptTransfer(string calldata landId) external {
        bytes32 key = _keyOf(landId);
        PendingTransfer storage pending = pendingTransfers[key];
        
        require(parcels[key].owner != address(0), "Parcel not found");
        require(pending.active, "No pending transfer");
        require(msg.sender == pending.to, "Only nominated recipient");
        require(!parcels[key].frozen, "Parcel frozen");

        address from = pending.from;
        address to = pending.to;
        string memory ipfsHash = pending.ipfsHash;

        // Verify the current owner hasn't changed since initiation
        require(parcels[key].owner == from, "Owner changed since initiation");

        // Remove from previous owner's list (swap & pop)
        _removeFromOwnerList(from, key);

        // Update parcel ownership
        parcels[key].owner = to;
        parcels[key].updatedAt = uint64(block.timestamp);

        // Add to new owner's list
        ownerIndex[key] = parcelsByOwner[to].length;
        parcelsByOwner[to].push(key);

        // Update transfer history
        transferHistory[key].push(to);

        // Add metadata version if provided
        if (bytes(ipfsHash).length > 0) {
            uint256 newVersion = metadataHistory[key].length + 1;
            metadataHistory[key].push(MetadataVersion({
                ipfsHash: ipfsHash,
                timestamp: uint64(block.timestamp),
                version: newVersion
            }));
            emit MetadataVersioned(key, ipfsHash, newVersion, uint64(block.timestamp));
        }

        // Clear pending transfer
        delete pendingTransfers[key];

        emit TransferAccepted(key, from, to);
    }

    /// @notice Cancel a pending transfer (current owner only)
    function cancelTransfer(string calldata landId) external {
        bytes32 key = _keyOf(landId);
        PendingTransfer storage pending = pendingTransfers[key];
        
        require(pending.active, "No pending transfer");
        require(msg.sender == pending.from, "Only initiator can cancel");

        delete pendingTransfers[key];
    }

    // ---------------------- Read Functions ----------------------

    /// @notice View parcel details by landId
    function getParcel(string calldata landId)
        external
        view
        returns (
            string memory outLandId,
            bytes32 landKey,
            address owner,
            bool frozen,
            string memory latestIpfsHash,
            uint64 createdAt,
            uint64 updatedAt,
            uint256 metadataVersions
        )
    {
        bytes32 key = _keyOf(landId);
        Parcel memory p = parcels[key];
        
        string memory ipfsHash = "";
        uint256 versions = metadataHistory[key].length;
        if (versions > 0) {
            ipfsHash = metadataHistory[key][versions - 1].ipfsHash;
        }
        
        return (p.landId, p.landKey, p.owner, p.frozen, ipfsHash, p.createdAt, p.updatedAt, versions);
    }

    /// @notice View parcel details by landKey (bytes32)
    function getParcelByKey(bytes32 key)
        external
        view
        returns (
            string memory outLandId,
            bytes32 landKey,
            address owner,
            bool frozen,
            string memory latestIpfsHash,
            uint64 createdAt,
            uint64 updatedAt,
            uint256 metadataVersions
        )
    {
        Parcel memory p = parcels[key];
        
        string memory ipfsHash = "";
        uint256 versions = metadataHistory[key].length;
        if (versions > 0) {
            ipfsHash = metadataHistory[key][versions - 1].ipfsHash;
        }
        
        return (p.landId, p.landKey, p.owner, p.frozen, ipfsHash, p.createdAt, p.updatedAt, versions);
    }

    /// @notice Get specific metadata version by landKey and version index
    function getMetadataVersion(bytes32 landKey, uint256 versionIndex)
        external
        view
        returns (
            string memory ipfsHash,
            uint64 timestamp,
            uint256 version
        )
    {
        require(versionIndex < metadataHistory[landKey].length, "Version index out of bounds");
        MetadataVersion memory mv = metadataHistory[landKey][versionIndex];
        return (mv.ipfsHash, mv.timestamp, mv.version);
    }

    /// @notice Get all metadata versions for a landKey
    function getAllMetadataVersions(bytes32 landKey)
        external
        view
        returns (MetadataVersion[] memory)
    {
        return metadataHistory[landKey];
    }

    /// @notice Get pending transfer details
    function getPendingTransfer(string calldata landId)
        external
        view
        returns (
            address from,
            address to,
            string memory ipfsHash,
            bool active,
            uint64 initiatedAt
        )
    {
        bytes32 key = _keyOf(landId);
        PendingTransfer memory pending = pendingTransfers[key];
        return (pending.from, pending.to, pending.ipfsHash, pending.active, pending.initiatedAt);
    }

    /// @notice Get transfer history by landId
    function getTransferHistory(string calldata landId) external view returns (address[] memory) {
        return transferHistory[_keyOf(landId)];
    }

    /// @notice Get transfer history by landKey
    function getTransfers(bytes32 landKey) external view returns (address[] memory) {
        return transferHistory[landKey];
    }

    /// @notice Check registration by landId
    function isParcelRegistered(string calldata landId) external view returns (bool) {
        return parcels[_keyOf(landId)].owner != address(0);
    }

    /// @notice List all parcel keys currently owned by an address
    function getParcelsByOwner(address owner_) external view returns (bytes32[] memory) {
        return parcelsByOwner[owner_];
    }

    /// @notice Get total number of parcels owned by an address
    function getOwnerParcelCount(address owner_) external view returns (uint256) {
        return parcelsByOwner[owner_].length;
    }

    // ---------------------- Internal Functions ----------------------

    function _keyOf(string memory landId) internal pure returns (bytes32) {
        // NOTE: callers should normalize landId off-chain (trim/case/format) before calling.
        return keccak256(abi.encodePacked(landId));
    }

    function _removeFromOwnerList(address owner_, bytes32 key) internal {
        bytes32[] storage list = parcelsByOwner[owner_];
        uint256 idx = ownerIndex[key];
        uint256 last = list.length - 1;

        if (idx != last) {
            bytes32 lastKey = list[last];
            list[idx] = lastKey;
            ownerIndex[lastKey] = idx;
        }
        list.pop();
        // ownerIndex[key] will be overwritten when added to the new owner's list
    }
}