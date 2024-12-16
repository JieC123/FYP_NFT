let TicketsABI;
let contractAddress;
let currentQRData = null;
let currentTokenId = null;

async function loadContractData() {
    try {
        const response = await fetch('/get_contract_data');
        const data = await response.json();
        TicketsABI = data.abi;
        contractAddress = data.address;
        
        document.getElementById('contractAddress').textContent = contractAddress;
        
        // console.log('Contract data loaded successfully');
        // console.log('ABI:', TicketsABI);
        // console.log('Contract Address:', contractAddress);
    } catch (error) {
        console.error('Failed to load contract data:', error);
    }
}

document.addEventListener('DOMContentLoaded', loadContractData);

async function validateTicketInputs(ticketId, eventName, price, eventDate, ticketType, eventVenue, quantity) {
    // Input validation
    if (!ticketId || ticketId.trim() === '') {
        throw new Error('Ticket ID is required');
    }
    if (!eventName || eventName.trim() === '') {
        throw new Error('Event name is required');
    }
    if (!price || price <= 0) {
        throw new Error('Price must be greater than 0');
    }
    if (!eventDate) {
        throw new Error('Event date is required');
    }
    
    const eventTimestamp = new Date(eventDate).getTime();
    if (isNaN(eventTimestamp)) {
        throw new Error('Invalid event date');
    }
    
    if (!ticketType || ticketType.trim() === '') {
        throw new Error('Ticket type is required');
    }
    if (!eventVenue || eventVenue.trim() === '') {
        throw new Error('Event venue is required');
    }
    if (!quantity || quantity <= 0 || !Number.isInteger(Number(quantity))) {
        throw new Error('Quantity must be a positive integer');
    }
}

async function checkOwnershipAndNetwork() {
    if (typeof window.ethereum === 'undefined') {
        throw new Error('Please install MetaMask to use this feature.');
    }

    const web3 = new Web3(window.ethereum);
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    
    if (!accounts || accounts.length === 0) {
        throw new Error('No accounts found. Please connect your wallet.');
    }

    // Check if connected to the correct network
    const networkId = await web3.eth.net.getId();
    // Add your expected network ID here
    const expectedNetworkId = 5777; // Change this to match your deployment network
    if (networkId !== expectedNetworkId) {
        throw new Error('Please connect to the correct network');
    }

    return { web3, account: accounts[0] };
}

async function mintNFT(ticketId, eventName, price, eventDate, ticketType, eventVenue, quantity, isTransferrable) {
    const mintingResult = document.getElementById('mintingResult');
    try {
        // Show loading state
        mintingResult.className = 'progress';
        mintingResult.innerHTML = `
            <div class="loading-spinner"></div>
            <span>Initializing NFT minting process...</span>
        `;

        // Get web3 instance and check network first
        const { web3, account } = await checkOwnershipAndNetwork();
        
        // Get contract instance
        const contract = new web3.eth.Contract(TicketsABI, contractAddress);

        // Convert price to wei
        const priceInWei = web3.utils.toWei(price.toString(), 'ether');
        const eventDateTimestamp = Math.floor(new Date(eventDate).getTime() / 1000);

        // First create the batch on blockchain to get token IDs
        mintingResult.innerHTML = `
            <div class="loading-spinner"></div>
            <span>Creating NFTs on blockchain...</span>
        `;

        // Create empty batch data array for initial creation
        const emptyBatchData = Array(parseInt(quantity)).fill({
            metadataURI: '',
            qrCodeURI: '',
            verificationHash: ''
        });

        // Estimate gas for the batch transaction
        const gasEstimate = await contract.methods.createTicketsInBatch(
            ticketId,
            priceInWei,
            eventName,
            eventDateTimestamp,
            ticketType,
            eventVenue,
            emptyBatchData,
            isTransferrable
        ).estimateGas({ from: account });

        // Execute batch creation to get token IDs
        const result = await contract.methods.createTicketsInBatch(
            ticketId,
            priceInWei,
            eventName,
            eventDateTimestamp,
            ticketType,
            eventVenue,
            emptyBatchData,
            isTransferrable
        ).send({
            from: account,
            gas: Math.floor(gasEstimate * 1.1)
        });

        // Extract token IDs from the event
        let tokenIds = [];
        if (result.events.TicketCreated) {
            const event = result.events.TicketCreated;
            if (Array.isArray(event)) {
                tokenIds = event.map(e => e.returnValues.tokenIds).flat();
            } else {
                tokenIds = event.returnValues.tokenIds.map(id => web3.utils.toBN(id).toString());
            }
            console.log('Extracted Token IDs:', tokenIds);
        }

        
        // Now generate metadata with real token IDs
        mintingResult.innerHTML = `
            <div class="loading-spinner"></div>
            <span>Generating NFT metadata...</span>
        `;

        const metadataResponse = await fetch('/generateNFTMetadata', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ticketId,
                eventName,
                price,
                eventDate,
                ticketType,
                eventVenue,
                quantity,
                tokenIds // Pass the real token IDs
            })
        });

        const metadataResult = await metadataResponse.json();
        if (!metadataResult.success) {
            throw new Error(metadataResult.message || 'Failed to generate metadata');
        }

        // Update batch data with real metadata
        const batchData = metadataResult.nftData.map(nft => ({
            metadataURI: `ipfs://${nft.metadataHash}`,
            qrCodeURI: `ipfs://${nft.qrHash}`,
            verificationHash: nft.verificationHash
        }));

        // Update the NFTs with metadata
        await contract.methods.updateBatchMetadata(
            tokenIds,
            batchData
        ).send({ from: account });

        // Send the token IDs to the backend
        const mintResponse = await fetch('/mintNFT', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ticketId,
                tokenIds,
                blockchainTxId: result.transactionHash,
                quantity: parseInt(quantity),
                ownerId: account,
                metadataInfo: metadataResult.nftData
            })
        });

        const mintResult = await mintResponse.json();
        if (!mintResult.success) {
            throw new Error(mintResult.message || 'Failed to store NFT data');
        }

        // Update the display with the correct token IDs
        await displayQRCodes(metadataResult.nftData.map((nft, index) => ({
            ...nft,
            tokenId: tokenIds[index]
        })));

        updateRecentMints(ticketId, metadataResult.nftData.map((nft, index) => ({
            ...nft,
            tokenId: tokenIds[index]
        })));

        const updateResponse = await fetch('/update_ticket_transferability', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ticketId: ticketId,
                isTransferrable: isTransferrable
            })
        });

        if (!updateResponse.ok) {
            throw new Error('Failed to update ticket transferability status');
        }

        // Show success message
        mintingResult.className = 'success';
        mintingResult.innerHTML = `
            <i class="fas fa-check-circle"></i>
            Successfully minted ${quantity} NFTs with Token IDs: ${tokenIds.join(', ')}
            <p>Transferability: ${isTransferrable ? 'Transferable' : 'Non-transferable'}</p>
        `;

        return { success: true, tokenIds };

    } catch (error) {
        console.error('Error in batch minting:', error);
        
        // Simplified error message handling
        let userFriendlyMessage = 'Failed to mint NFT tickets. ';
        
        if (error.message.includes('non-transferrable')) {
            userFriendlyMessage += 'This ticket type is non-transferrable and cannot be resold or transferred.';
        } else if (error.message.includes('Only contract owner')) {
            userFriendlyMessage += 'You do not have permission to mint tickets. Please use the contract owner account.';
        } else if (error.message.includes('insufficient funds')) {
            userFriendlyMessage += 'Insufficient funds to complete the transaction.';
        } else if (error.message.includes('user rejected')) {
            userFriendlyMessage += 'Transaction was rejected by user.';
        } else {
            userFriendlyMessage += 'An unexpected error occurred. Please try again.';
        }

        mintingResult.className = 'error';
        mintingResult.innerHTML = `
            <i class="fas fa-exclamation-circle"></i>
            ${userFriendlyMessage}
        `;
        throw error;
    }
}

function updateRecentMints(ticketId, nftData) {
    const recentMints = document.getElementById('recentMints');
    const mintEntry = document.createElement('div');
    mintEntry.className = 'recent-mint-entry';
    
    const timestamp = new Date().toLocaleString();
    mintEntry.innerHTML = `
        <div class="mint-header">
            <span class="mint-timestamp">${timestamp}</span>
            <span class="mint-ticket-id">Ticket ID: ${ticketId}</span>
        </div>
        <div class="mint-details">
            <span>Minted ${nftData.length} NFTs</span>
            <button onclick="toggleMintDetails(this)">Show Details</button>
        </div>
        <div class="mint-tokens" style="display: none;">
            ${nftData.map(nft => `
                <div class="token-entry">
                    <span>Token ID: ${nft.tokenId}</span>
                    <a href="https://ipfs.io/ipfs/${nft.metadataHash}" target="_blank">
                        View Metadata
                    </a>
                </div>
            `).join('')}
        </div>
    `;
    
    recentMints.insertBefore(mintEntry, recentMints.firstChild);
}

function toggleMintDetails(button) {
    const detailsDiv = button.parentElement.nextElementSibling;
    if (detailsDiv.style.display === 'none') {
        detailsDiv.style.display = 'block';
        button.textContent = 'Hide Details';
    } else {
        detailsDiv.style.display = 'none';
        button.textContent = 'Show Details';
    }
}

async function displayQRCodes(nftData) {
    if (!Array.isArray(nftData)) {
        console.error('Invalid nftData format:', nftData);
        return;
    }

    const container = document.getElementById('qrCodesContainer') || 
                     document.createElement('div');
    container.id = 'qrCodesContainer';
    container.innerHTML = '<h3>Generated QR Codes:</h3>';

    nftData.forEach((nft, index) => {
        if (!nft.qrHash || !nft.tokenId || !nft.verificationHash) {
            console.error('Invalid NFT data format:', nft);
            return;
        }

        const qrDiv = document.createElement('div');
        qrDiv.className = 'qr-code-item';
        qrDiv.innerHTML = `
            <h4>Ticket #${index + 1}</h4>
            <img src="data:image/png;base64,${nft.qrBase64}" alt="QR Code ${index + 1}">
            <p>Token ID: ${nft.tokenId}</p>
            <p>Verification Hash: ${nft.verificationHash}</p>
            <p>IPFS Links:</p>
            <ul>
                <li><a href="http://localhost:8080/ipfs/${nft.qrHash}" target="_blank">View QR Code (Local IPFS)</a></li>
                <li><a href="http://localhost:8080/ipfs/${nft.metadataHash}" target="_blank">View Metadata (Local IPFS)</a></li>
                <li><a href="https://ipfs.io/ipfs/${nft.qrHash}" target="_blank">View QR Code (Public Gateway)</a></li>
                <li><a href="https://ipfs.io/ipfs/${nft.metadataHash}" target="_blank">View Metadata (Public Gateway)</a></li>
            </ul>
        `;
        container.appendChild(qrDiv);
    });

    if (!document.getElementById('qrCodesContainer')) {
        const mintingResult = document.getElementById('mintingResult');
        if (mintingResult) {
            mintingResult.after(container);
        } else {
            document.body.appendChild(container);
        }
    }
}

function updateRecentMints(ticketId, nftData) {
    const recentMints = document.getElementById('recentMints');
    const mintEntry = document.createElement('div');
    mintEntry.className = 'recent-mint-entry';
    
    const timestamp = new Date().toLocaleString();
    mintEntry.innerHTML = `
        <div class="mint-header">
            <span class="mint-timestamp">${timestamp}</span>
            <span class="mint-ticket-id">Ticket ID: ${ticketId}</span>
        </div>
        <div class="mint-details">
            <span>Minted ${nftData.length} NFTs</span>
            <button onclick="toggleMintDetails(this)">Show Details</button>
        </div>
        <div class="mint-tokens" style="display: none;">
            ${nftData.map(nft => `
                <div class="token-entry">
                    <span>Token ID: ${nft.tokenId}</span>
                    <a href="http://localhost:8080/ipfs/${nft.metadataHash}" target="_blank">
                        View Metadata (Local)
                    </a>
                    <a href="https://ipfs.io/ipfs/${nft.metadataHash}" target="_blank">
                        View Metadata (Public)
                    </a>
                </div>
            `).join('')}
        </div>
    `;
    
    recentMints.insertBefore(mintEntry, recentMints.firstChild);
}

// async function getTicketMetadata(ticketId) {
//     const response = await fetch(`/get_ticket_metadata/${ticketId}`);
//     if (!response.ok) {
//         throw new Error('Failed to fetch ticket metadata');
//     }
//     return await response.json();
// }

async function verifyTicket(tokenId, qrCode) {
    const contract = new web3.eth.Contract(TicketsABI, contractAddress);
    
    // Hash the QR code
    const qrHash = web3.utils.sha3(JSON.stringify(qrCode));
    
    // Verify on blockchain
    const isValid = await contract.methods.verifyTicketQR(tokenId, qrHash).call();
    
    if (isValid) {
        console.log('Valid ticket!');
        // Update UI to show valid ticket
    } else {
        console.log('Invalid ticket!');
        // Update UI to show invalid ticket
    }
}