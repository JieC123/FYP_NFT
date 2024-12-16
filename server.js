const Web3 = require('web3');
const app = express();
const port = 3000;
const fs = require('fs');
const path = require('path');


// Connect to Ganache
const web3 = new Web3('http://localhost:7545'); // Use your Ganache RPC URL

let contractAddress;
let contractABI;

// Function to load contract data
async function loadContractData() {
    try {
        const contractData = require('../build/contracts/Tickets.json');
        
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

const contract = new web3.eth.Contract(contractABI, contractAddress);


app.get('/api/ticket/:ticketId', async (req, res) => {
    const ticketId = req.params.ticketId;

    try {
        // Fetch ticket details from the smart contract
        const ticket = await contract.methods.getTicketDetails(ticketId).call();

        if (!ticket || ticket.ticketId === '') {
            return res.status(404).json({ error: 'Ticket not found' });
        }

        const metadata = {
            name: `Event Ticket #${ticketId}`,
            description: `Ticket for ${ticket.eventName}`,
            image: 'src/image/logo.png', // Updated image URL
            attributes: [
                {
                    trait_type: 'Event Date',
                    value: new Date(ticket.eventDate * 1000).toISOString().split('T')[0]
                },
                {
                    trait_type: 'Ticket ID',
                    value: ticketId
                },
                {
                    trait_type: 'Price',
                    value: web3.utils.fromWei(ticket.price, 'ether') + ' ETH'
                }
            ]
        };

        res.json(metadata);
    } catch (error) {
        console.error('Error fetching ticket details:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

app.listen(port, () => {
    console.log(`Ticket metadata server listening at http://localhost:${port}`);
});
