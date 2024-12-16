// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/utils/Strings.sol";
import "@openzeppelin/contracts/utils/Base64.sol";

contract Tickets is ERC721 {
    using Counters for Counters.Counter;
    using Strings for uint256;

    Counters.Counter private _tokenIds;

    struct TicketMetadata {
        string eventName;
        uint256 eventDate;
        string ticketType;
        string eventVenue;
        string metadataURI;
        string qrCodeURI;
        string verificationHash;
        bool isTransferrable;
    }

    struct TicketSales {
        uint256 price;
        address owner;
        bool isSold;
        address currentOwner;
        uint256 mintedQuantity;
        uint256 resalePrice;
    }

    struct BatchTicketData {
        string metadataURI;
        string qrCodeURI;
        string verificationHash;
    }

    struct TicketUsage {
        bool isUsed;
        uint256 usedTime;
        address usedBy;
    }

    mapping(string => TicketMetadata) public ticketMetadata;
    mapping(string => TicketSales) public ticketSales;
    mapping(uint256 => string) public tokenIdToTicketId;
    mapping(string => bool) private usedQRCodes;
    mapping(string => bool) private usedVerificationHashes;
    mapping(uint256 => string) private tokenURIs;
    mapping(uint256 => BatchTicketData) private batchTokenData;
    mapping(uint256 => TicketUsage) public ticketUsage;
    mapping(uint256 => bool) private _hasBeenPurchased;
    
    address public contractOwner;

    event TicketCreated(string ticketId, uint256[] tokenIds, string[] metadataURIs, string[] qrCodeURIs, bool isTransferrable);
    event TicketPurchased(string ticketId, address buyer, uint256 tokenId);
    event TicketUsed(string ticketId, uint256 tokenId, string verificationHash);
    event TicketVerified(string ticketId, uint256 tokenId, bool isValid);
    event TicketValidated(uint256 indexed tokenId, address indexed user, uint256 timestamp);
    event TicketListedForResale(uint256 tokenId, uint256 price, address seller);
    event TicketResaleCanceled(uint256 tokenId, address seller);
    event TicketResold(uint256 tokenId, address seller, address buyer, uint256 price);

    constructor() ERC721("EventTicket", "EVTK") {
        contractOwner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == contractOwner, "Only contract owner");
        _;
    }

    function initializeTicket(
        string memory ticketId,
        uint256 price,
        string memory eventName,
        uint256 eventDate,
        string memory ticketType,
        string memory eventVenue,
        bool isTransferrable
    ) internal {
        if (bytes(ticketMetadata[ticketId].eventName).length == 0) {
            ticketMetadata[ticketId] = TicketMetadata({
                eventName: eventName,
                eventDate: eventDate,
                ticketType: ticketType,
                eventVenue: eventVenue,
                metadataURI: "",
                qrCodeURI: "",
                verificationHash: "",
                isTransferrable: isTransferrable
            });

            ticketSales[ticketId] = TicketSales({
                price: price,
                owner: msg.sender,
                isSold: false,
                currentOwner: msg.sender,
                mintedQuantity: 0,
                resalePrice: 0
            });
        }
    }

    function createTicketsInBatch(
        string memory ticketId,
        uint256 price,
        string memory eventName,
        uint256 eventDate,
        string memory ticketType,
        string memory eventVenue,
        BatchTicketData[] memory batchData,
        bool isTransferrable
    ) public onlyOwner returns (uint256[] memory) {
        require(bytes(ticketMetadata[ticketId].eventName).length == 0, "Ticket already exists");
        require(price > 0, "Invalid price");
        require(batchData.length > 0, "No ticket data provided");
        
        initializeTicket(
            ticketId,
            price,
            eventName,
            eventDate,
            ticketType,
            eventVenue,
            isTransferrable
        );
        
        uint256[] memory newTokenIds = new uint256[](batchData.length);
        string[] memory metadataURIs = new string[](batchData.length);
        string[] memory qrCodeURIs = new string[](batchData.length);
        
        for (uint256 i = 0; i < batchData.length; i++) {
            _tokenIds.increment();
            uint256 newTokenId = _tokenIds.current();
            
            tokenIdToTicketId[newTokenId] = ticketId;
            batchTokenData[newTokenId] = BatchTicketData({
                metadataURI: "",
                qrCodeURI: "",
                verificationHash: ""
            });
            _safeMint(msg.sender, newTokenId);
            
            tokenCurrentOwner[newTokenId] = msg.sender;
            
            ticketSales[ticketId].mintedQuantity++;
            newTokenIds[i] = newTokenId;
            metadataURIs[i] = "";
            qrCodeURIs[i] = "";
        }

        emit TicketCreated(
            ticketId,
            newTokenIds,
            metadataURIs,
            qrCodeURIs,
            isTransferrable
        );
        
        return newTokenIds;
    }

    function verifyTicket(
        string memory ticketId, 
        uint256 tokenId, 
        string memory verificationHash
    ) public returns (bool) {
        require(_exists(tokenId), "Invalid token");
        require(bytes(ticketMetadata[ticketId].eventName).length > 0, "Invalid ticket");
        
        bool isValid = keccak256(abi.encodePacked(batchTokenData[tokenId].verificationHash)) == 
                      keccak256(abi.encodePacked(verificationHash));
        
        emit TicketVerified(ticketId, tokenId, isValid);
        return isValid;
    }

    function getTicketBatchData(uint256 tokenId) public view returns (BatchTicketData memory) {
        require(_exists(tokenId), "Token does not exist");
        return batchTokenData[tokenId];
    }

    function setTicketForResale(string memory ticketId, uint256 tokenId, uint256 newPrice) public {
        require(_exists(tokenId), "Token does not exist");
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        require(keccak256(bytes(tokenIdToTicketId[tokenId])) == keccak256(bytes(ticketId)), 
            "Token ID does not match ticket ID");
        require(!ticketUsage[tokenId].isUsed, "Ticket already used");
        
        require(newPrice <= ticketSales[ticketId].price, "Resale price cannot exceed original price");
        
        ticketSales[ticketId].resalePrice = newPrice;
        ticketSales[ticketId].isSold = false;
    }

    function buyTicket(string memory ticketId, uint256 quantity) public payable {
        require(bytes(ticketMetadata[ticketId].eventName).length >  0, "Invalid ticket");
        require(!ticketSales[ticketId].isSold, "Sold out");
        require(msg.sender != ticketSales[ticketId].currentOwner, "Owner cannot buy");
        require(quantity > 0, "Invalid quantity");
        
        uint256 availableTickets = ticketSales[ticketId].mintedQuantity - getNumberOfSoldTokens(ticketId);
        require(availableTickets >= quantity, "Not enough tickets available");

        uint256[] memory purchasedTokenIds = new uint256[](quantity);
        uint256 foundCount = 0;
        uint256 totalTokens = _tokenIds.current();

        for (uint256 i = 1; i <= totalTokens && foundCount < quantity; i++) {
            if (keccak256(bytes(tokenIdToTicketId[i])) == keccak256(bytes(ticketId))) {
                if (!isTokenSold(i)) {
                    purchasedTokenIds[foundCount] = i;
                    foundCount++;
                }
            }
        }

        require(foundCount == quantity, "Not enough available tickets");

        uint256 priceToUse = ticketSales[ticketId].resalePrice > 0 ? 
            ticketSales[ticketId].resalePrice : 
            ticketSales[ticketId].price;

        uint256 totalPayment = priceToUse * quantity;
        require(msg.value >= totalPayment, "Insufficient payment");

        address previousOwner = ticketSales[ticketId].owner;

        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = purchasedTokenIds[i];
            
            _approvedMarketplaceTransfer[tokenId] = true;
            
            _approve(msg.sender, tokenId);
            _transfer(previousOwner, msg.sender, tokenId);
            
            _hasBeenPurchased[tokenId] = true;
            _approvedMarketplaceTransfer[tokenId] = false;

            emit TicketPurchased(ticketId, msg.sender, tokenId);
        }

        payable(previousOwner).transfer(totalPayment);
    }

    function isTokenSold(uint256 tokenId) internal view returns (bool) {
        return ownerOf(tokenId) != ticketSales[tokenIdToTicketId[tokenId]].owner;
    }

    function markTokenAsSold(uint256 tokenId) internal {
        // No need to set a global sold flag anymore, 
        // ownership transfer is enough to track sold status
    }

    function getNumberOfSoldTokens(string memory ticketId) internal view returns (uint256) {
        uint256 soldCount = 0;
        uint256 totalTokens = _tokenIds.current();
        
        for (uint256 i = 1; i <= totalTokens; i++) {
            if (keccak256(bytes(tokenIdToTicketId[i])) == keccak256(bytes(ticketId))) {
                if (isTokenSold(i)) {
                    soldCount++;
                }
            }
        }
        
        return soldCount;
    }

    function getTicketDetails(string memory ticketId) public view returns (TicketSales memory) {
        require(bytes(ticketMetadata[ticketId].eventName).length > 0, "Does not have ticket");
        return ticketSales[ticketId];
    }

    function validateAndUseTicket(string memory ticketId, uint256 tokenId) public returns (bool) {
        require(_exists(tokenId), "Token does not exist");
        require(ownerOf(tokenId) == msg.sender, "Not ticket owner");
        
        require(bytes(ticketMetadata[ticketId].eventName).length > 0, "Invalid ticket");
        
        require(keccak256(bytes(tokenIdToTicketId[tokenId])) == keccak256(bytes(ticketId)), 
            "Token ID does not match ticket ID");
        
        require(!ticketUsage[tokenId].isUsed, "This specific ticket has already been used");

        ticketUsage[tokenId] = TicketUsage({
            isUsed: true,
            usedTime: block.timestamp,
            usedBy: msg.sender
        });

        emit TicketValidated(tokenId, msg.sender, block.timestamp);
        return true;
    }

    function getTokenUsageStatus(uint256 tokenId) public view returns (TicketUsage memory) {
        require(_exists(tokenId), "Token does not exist");
        return ticketUsage[tokenId];
    }

    function isTokenValidForUse(string memory ticketId, uint256 tokenId) public view returns (bool) {
        if (!_exists(tokenId)) return false;
        if (bytes(ticketMetadata[ticketId].eventName).length == 0) return false;
        if (keccak256(bytes(tokenIdToTicketId[tokenId])) != keccak256(bytes(ticketId))) return false;
        if (ticketUsage[tokenId].isUsed) return false;
        return true;
    }

    function getTicketUsageDetails(uint256 tokenId) public view returns (TicketUsage memory) {
        require(_exists(tokenId), "Token does not exist");
        return ticketUsage[tokenId];
    }

    struct ResaleListing {
        uint256 tokenId;
        uint256 price;
        bool isActive;
        address seller;
    }

    mapping(uint256 => ResaleListing) public resaleListings;
    mapping(address => uint256[]) public userListings;

    function listTicketForResale(uint256 tokenId, uint256 price) public {
        require(_exists(tokenId), "Token does not exist");
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        require(!ticketUsage[tokenId].isUsed, "Ticket already used");
        
        string memory ticketId = tokenIdToTicketId[tokenId];
        require(
            ticketMetadata[ticketId].isTransferrable || !_hasBeenPurchased[tokenId],
            "This ticket cannot be listed for resale after initial purchase"
        );

        uint256 originalPrice = ticketSales[ticketId].price;
        require(price <= originalPrice, "Price exceeds original");
        require(!resaleListings[tokenId].isActive, "Already listed");

        resaleListings[tokenId] = ResaleListing({
            tokenId: tokenId,
            price: price,
            isActive: true,
            seller: msg.sender
        });
        
        userListings[msg.sender].push(tokenId);
        
        emit TicketListedForResale(tokenId, price, msg.sender);
    }

    function cancelResaleListing(uint256 tokenId) public {
        require(resaleListings[tokenId].isActive, "Not listed");
        require(resaleListings[tokenId].seller == msg.sender, "Not seller");
        
        resaleListings[tokenId].isActive = false;
        
        emit TicketResaleCanceled(tokenId, msg.sender);
    }

    function buyResaleTicket(uint256 tokenId) public payable {
        ResaleListing memory listing = resaleListings[tokenId];
        require(listing.isActive, "Not listed for resale");
        require(msg.sender != listing.seller, "Cannot buy own ticket");
        require(msg.value >= listing.price, "Insufficient payment");
        require(!ticketUsage[tokenId].isUsed, "Ticket already used");

        string memory ticketId = tokenIdToTicketId[tokenId];
        require(
            ticketMetadata[ticketId].isTransferrable || !_hasBeenPurchased[tokenId],
            "This ticket cannot be transferred after initial purchase"
        );

        address seller = listing.seller;
        uint256 price = listing.price;

        _approvedMarketplaceTransfer[tokenId] = true;
        
        _approve(msg.sender, tokenId);
        _transfer(seller, msg.sender, tokenId);
        
        _hasBeenPurchased[tokenId] = true;
        _approvedMarketplaceTransfer[tokenId] = false;

        resaleListings[tokenId].isActive = false;

        tokenCurrentOwner[tokenId] = msg.sender;

        payable(seller).transfer(price);

        emit TicketResold(tokenId, seller, msg.sender, price);
    }

    function getActiveResaleListings() public view returns (uint256[] memory) {
        uint256 totalTokens = _tokenIds.current();
        uint256 activeCount = 0;
        
        for (uint256 i = 1; i <= totalTokens; i++) {
            if (resaleListings[i].isActive) {
                activeCount++;
            }
        }
        
        uint256[] memory activeListings = new uint256[](activeCount);
        uint256 currentIndex = 0;
        
        for (uint256 i = 1; i <= totalTokens && currentIndex < activeCount; i++) {
            if (resaleListings[i].isActive) {
                activeListings[currentIndex] = i;
                currentIndex++;
            }
        }
        
        return activeListings;
    }

    function getResaleListingDetails(uint256 tokenId) public view returns (ResaleListing memory) {
        require(resaleListings[tokenId].isActive, "Not listed for resale");
        return resaleListings[tokenId];
    }

    function updateBatchMetadata(
        uint256[] memory tokenIds,
        BatchTicketData[] memory batchData
    ) public onlyOwner {
        require(tokenIds.length == batchData.length, "Arrays length mismatch");
        
        for (uint256 i = 0; i < tokenIds.length; i++) {
            require(_exists(tokenIds[i]), "Token does not exist");
            
            batchTokenData[tokenIds[i]] = batchData[i];
            tokenURIs[tokenIds[i]] = batchData[i].metadataURI;
        }
    }

    mapping(uint256 => address) public tokenCurrentOwner;

    function getTokenCurrentOwner(uint256 tokenId) public view returns (address) {
        require(_exists(tokenId), "Token does not exist");
        return tokenCurrentOwner[tokenId] != address(0) ? tokenCurrentOwner[tokenId] : ownerOf(tokenId);
    }

    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 tokenId,
        uint256 batchSize
    ) internal virtual override {
        super._beforeTokenTransfer(from, to, tokenId, batchSize);
        
        if (from != address(0) && to != address(0)) {
            string memory ticketId = tokenIdToTicketId[tokenId];
            
            require(bytes(ticketMetadata[ticketId].eventName).length > 0, "Invalid ticket");
            
            if (!ticketMetadata[ticketId].isTransferrable && _hasBeenPurchased[tokenId]) {
                require(
                    _approvedMarketplaceTransfer[tokenId] ||
                    msg.sender == contractOwner,
                    "Non-transferrable tickets cannot be transferred directly"
                );
            }
            
            _approvedMarketplaceTransfer[tokenId] = false;
        }
    }

    function isTicketTransferrable(uint256 tokenId) public view returns (bool) {
        require(_exists(tokenId), "Token does not exist");
        string memory ticketId = tokenIdToTicketId[tokenId];
        return ticketMetadata[ticketId].isTransferrable;
    }

    modifier onlyMarketplace() {
        require(
            msg.sender == contractOwner || 
            msg.sender == address(this), 
            "Only marketplace can perform this operation"
        );
        _;
    }

    mapping(uint256 => bool) private _approvedMarketplaceTransfer;

    function transferFrom(
        address from,
        address to,
        uint256 tokenId
    ) public virtual override {
        string memory ticketId = tokenIdToTicketId[tokenId];
        require(
            ticketMetadata[ticketId].isTransferrable || 
            !_hasBeenPurchased[tokenId] ||
            _approvedMarketplaceTransfer[tokenId] ||
            msg.sender == contractOwner,
            "Transfers must be done through the marketplace"
        );
        super.transferFrom(from, to, tokenId);
    }

    function safeTransferFrom(
        address from,
        address to,
        uint256 tokenId
    ) public virtual override {
        string memory ticketId = tokenIdToTicketId[tokenId];
        require(
            ticketMetadata[ticketId].isTransferrable || 
            !_hasBeenPurchased[tokenId] ||
            _approvedMarketplaceTransfer[tokenId] ||
            msg.sender == contractOwner,
            "Transfers must be done through the marketplace"
        );
        super.safeTransferFrom(from, to, tokenId);
    }

    function safeTransferFrom(
        address from,
        address to,
        uint256 tokenId,
        bytes memory data
    ) public virtual override {
        string memory ticketId = tokenIdToTicketId[tokenId];
        require(
            ticketMetadata[ticketId].isTransferrable || 
            !_hasBeenPurchased[tokenId] ||
            _approvedMarketplaceTransfer[tokenId] ||
            msg.sender == contractOwner,
            "Transfers must be done through the marketplace"
        );
        super.safeTransferFrom(from, to, tokenId, data);
    }

    function approve(address to, uint256 tokenId) public virtual override {
        string memory ticketId = tokenIdToTicketId[tokenId];
        require(
            ticketMetadata[ticketId].isTransferrable || 
            !_hasBeenPurchased[tokenId] ||
            msg.sender == contractOwner,
            "Non-transferrable tickets cannot be approved for transfer"
        );
        super.approve(to, tokenId);
    }

    function setApprovalForAll(address operator, bool approved) public virtual override {
        require(
            msg.sender == contractOwner || 
            approved == false,  // Always allow removing approvals
            "Cannot set approval for all on non-transferrable tickets"
        );
        super.setApprovalForAll(operator, approved);
    }
}