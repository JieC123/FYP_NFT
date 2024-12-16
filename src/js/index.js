let web3;
let contract;
let userAccount;

let contractAddress;
let contractABI;

// Function to load contract data
async function loadContractData() {
    try {
        const response = await fetch('/build/contracts/Tickets.json');
        const contractData = await response.json();
        
        // Get the network ID
        const networkId = await web3.eth.net.getId();
        
        // Get the deployed address for this network
        contractAddress = contractData.networks[networkId].address;
        
        // Get the ABI
        contractABI = contractData.abi;
        
        console.log('Contract Address:', contractAddress);
        console.log('Contract ABI loaded');
    } catch (error) {
        console.error('Failed to load contract data:', error);
    }
}

async function connectWallet() {
    if (typeof window.ethereum !== 'undefined') {
        try {
            await window.ethereum.request({ method: 'eth_requestAccounts' });
            web3 = new Web3(window.ethereum);
            
            // Load contract data after connecting to the wallet
            await loadContractData();
            
            const accounts = await web3.eth.getAccounts();
            userAccount = accounts[0];
            contract = new web3.eth.Contract(contractABI, contractAddress);
            
            document.getElementById('connectWallet').style.display = 'none';
            document.getElementById('createTicketForm').style.display = 'block';
            document.getElementById('buyTicketForm').style.display = 'block';
        } catch (error) {
            console.error('Failed to connect wallet:', error);
        }
    } else {
        alert('Please install MetaMask to use this dApp!');
    }
}

async function createTicket() {
    const eventName = document.getElementById('eventName').value;
    const ticketPrice = web3.utils.toWei(document.getElementById('ticketPrice').value, 'ether');
    const eventDate = Math.floor(new Date(document.getElementById('eventDate').value).getTime() / 1000);

    try {
        const result = await contract.methods.createTicket(ticketPrice, eventName, eventDate).send({ from: userAccount });
        const ticketId = result.events.TicketCreated.returnValues.ticketId;
        alert(`Ticket created successfully! Ticket ID: ${ticketId}`);
    } catch (error) {
        console.error('Failed to create ticket:', error);
        alert('Failed to create ticket. See console for details.');
    }
}

async function buyTicket() {
    const ticketId = document.getElementById('ticketId').value;
    console.log("Attempting to buy ticket with ID:", ticketId);
    
    try {
        // Check if the ticket exists and log its details
        const ticketDetails = await contract.methods.getTicketDetails(ticketId).call();
        console.log("Ticket details:", ticketDetails);
        
        if (!ticketDetails || ticketDetails.ticketId === '') {
            throw new Error("Ticket does not exist");
        }

        const ticketPrice = await contract.methods.getTicketPrice(ticketId).call();
        console.log("Ticket price:", ticketPrice);
        
        // Attempt to buy the ticket
        const result = await contract.methods.buyTicket(ticketId).send({ 
            from: userAccount, 
            value: ticketPrice
        });
        console.log("Purchase result:", result);
        alert('Ticket purchased successfully!');
    } catch (error) {
        console.error('Failed to purchase ticket:', error);
        alert('Failed to purchase ticket. Error: ' + error.message);
    }
}

async function getTicketDetails() {
    const ticketId = document.getElementById('searchTicketId').value;
    
    try {
        const ticketDetails = await contract.methods.getTicketDetails(ticketId).call();
        displayTicketDetails(ticketDetails);
    } catch (error) {
        console.error('Failed to get ticket details:', error);
        alert('Failed to get ticket details. See console for details.');
    }
}

function displayTicketDetails(ticket) {
    const detailsDiv = document.getElementById('ticketDetails');
    detailsDiv.innerHTML = `
        <h3>Ticket Details</h3>
        <p>Ticket ID: ${ticket.ticketId}</p>
        <p>Event Name: ${ticket.eventName}</p>
        <p>Price: ${web3.utils.fromWei(ticket.price, 'ether')} ETH</p>
        <p>Sold: ${ticket.isSold ? 'Yes' : 'No'}</p>
        <p>Event Date: ${new Date(ticket.eventDate * 1000).toLocaleString()}</p>
    `;
}

// Wait for the DOM to be fully loaded before attaching event listeners
document.addEventListener('DOMContentLoaded', function() {
    const connectWalletButton = document.getElementById('connectWallet');
    const createTicketButton = document.getElementById('createTicket');
    const buyTicketButton = document.getElementById('buyTicket');

    if (connectWalletButton) {
        connectWalletButton.addEventListener('click', connectWallet);
    } else {
        console.error('Connect Wallet button not found');
    }

    if (createTicketButton) {
        createTicketButton.addEventListener('click', createTicket);
    } else {
        console.error('Create Ticket button not found');
    }

    if (buyTicketButton) {
        buyTicketButton.addEventListener('click', buyTicket);
    } else {
        console.error('Buy Ticket button not found');
    }

    const searchTicketButton = document.getElementById('searchTicket');
    if (searchTicketButton) {
        searchTicketButton.addEventListener('click', getTicketDetails);
    } else {
        console.error('Search Ticket button not found');
    }
});

async function searchNFT() {
    const tokenId = document.getElementById('searchTokenId').value;
    try {
        // Get the owner of the token
        const owner = await contract.methods.ownerOf(tokenId).call();
        
        // Get the token URI
        const tokenURI = await contract.methods.tokenURI(tokenId).call();
        
        // Get the ticket details (assuming you have a getTicketDetails function)
        const ticketId = await contract.methods.tokenIdToTicketId(tokenId).call();
        const ticketDetails = await contract.methods.getTicketDetails(ticketId).call();
        
        // Display the results
        const resultDiv = document.getElementById('searchResult');
        resultDiv.innerHTML = `
            <h3>NFT Details</h3>
            <p>Token ID: ${tokenId}</p>
            <p>Owner: ${owner}</p>
            <p>Token URI: ${tokenURI}</p>
            <p>Ticket ID: ${ticketId}</p>
            <p>Event Name: ${ticketDetails.eventName}</p>
            <p>Event Date: ${new Date(ticketDetails.eventDate * 1000).toLocaleString()}</p>
            <p>Price: ${web3.utils.fromWei(ticketDetails.price, 'ether')} ETH</p>
        `;
    } catch (error) {
        console.error('Error searching NFT:', error);
        alert('Error searching NFT. See console for details.');
    }
}

const searchNFTButton = document.getElementById('searchNFT');
if (searchNFTButton) {
    searchNFTButton.addEventListener('click', searchNFT);
} else {
    console.error('Search NFT button not found');
}

async function listOwnedNFTs() {
    try {
        const balance = await contract.methods.balanceOf(userAccount).call();
        const resultDiv = document.getElementById('ownedNFTs');
        resultDiv.innerHTML = '<h3>Your NFTs</h3>';
        
        for (let i = 0; i < balance; i++) {
            const tokenId = await contract.methods.tokenOfOwnerByIndex(userAccount, i).call();
            const ticketId = await contract.methods.tokenIdToTicketId(tokenId).call();
            const ticketDetails = await contract.methods.getTicketDetails(ticketId).call();
            
            resultDiv.innerHTML += `
                <p>Token ID: ${tokenId}, Ticket ID: ${ticketId}, Event: ${ticketDetails.eventName}</p>
            `;
        }
    } catch (error) {
        console.error('Error listing owned NFTs:', error);
    }
}

const listOwnedNFTsButton = document.getElementById('listOwnedNFTs');
if (listOwnedNFTsButton) {
    listOwnedNFTsButton.addEventListener('click', listOwnedNFTs);
} else {
    console.error('List Owned NFTs button not found');
}