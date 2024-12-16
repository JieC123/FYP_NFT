function showAlert(message, type = 'error') {
    alert(message);
}

// Common error handler for fetch responses
async function handleResponse(response) {
    const data = await response.json();
    if (!data.success) {
        showAlert(data.message);
        return false;
    }
    if (data.message) {
        showAlert(data.message, 'success');
    }
    if (data.redirect) {
        window.location.href = data.redirect;
    }
    return true;
}

// Parse blockchain errors into user-friendly messages
function parseBlockchainError(error) {
    // Check if it's a MetaMask error
    if (error.code === 4001) {
        return 'Transaction was cancelled by user';
    }

    // Extract message from various error formats
    let message = '';
    if (error.data && error.data.message) {
        message = error.data.message;
    } else if (error.message) {
        message = error.message;
    } else {
        return 'An unknown error occurred';
    }

    // Convert message to lowercase for consistent matching
    message = message.toLowerCase();

    // Comprehensive contract error mappings
    const errorMappings = {
        // Ownership and Authorization Errors
        'only contract owner': 'Only the contract owner can perform this action',
        'only owner': 'Only the contract owner can perform this action',
        'owner cannot buy': 'You cannot buy your own ticket',
        'not token owner': 'You do not own this ticket',
        'not seller': 'You are not the seller of this ticket',
        
        // Purchase and Sale Errors
        'insufficient payment': 'You have insufficient funds for this purchase',
        'invalid price': 'The ticket price is invalid',
        'price exceeds original': 'Resale price cannot exceed the original price',
        'sold out': 'This ticket is sold out',
        'not enough tickets available': 'There are not enough tickets available',
        'not enough available tickets': 'There are not enough tickets available',
        
        // Ticket Status Errors
        'ticket already used': 'This ticket has already been used',
        'ticket already exists': 'This ticket has already been created',
        'invalid ticket': 'This ticket does not exist',
        'does not have ticket': 'This ticket does not exist',
        'token does not exist': 'This ticket token does not exist',
        
        // Resale Market Errors
        'not listed for resale': 'This ticket is not available for resale',
        'already listed': 'This ticket is already listed for resale',
        'cannot buy own ticket': 'You cannot buy your own ticket',
        
        // Validation Errors
        'invalid token': 'Invalid ticket token',
        'invalid quantity': 'Invalid ticket quantity',
        'invalid ticket id': 'Invalid ticket ID',
        'token id does not match ticket id': 'Ticket ID mismatch',
        
        // Transaction Errors
        'transaction failed': 'Transaction failed. Please try again',
        'execution reverted': 'Transaction was reverted. Please try again',
        'user rejected': 'Transaction was rejected by user',
        
        // Verification Errors
        'invalid verification': 'Invalid ticket verification',
        'verification failed': 'Ticket verification failed',
        'already verified': 'Ticket has already been verified',
        
        // Batch Operation Errors
        'no ticket data provided': 'No ticket data was provided',
        'arrays length mismatch': 'Invalid batch data provided',
        
        // Payment Errors
        'transfer failed': 'Payment transfer failed',
        'insufficient balance': 'Insufficient balance for this transaction',
        'exceeds allowance': 'Transaction exceeds approved amount',
        
        // General Contract Errors
        'contract paused': 'The contract is currently paused',
        'invalid address': 'Invalid wallet address',
        'zero address': 'Invalid wallet address provided',
        
        // Non-transferable ticket errors
        'This ticket cannot be transferred after purchase': 'This ticket is non-transferrable and cannot be resold',
        'Transfers must be done through the marketplace': 'This ticket can only be transferred through our marketplace',
        'This ticket cannot be listed for resale': 'This ticket was set as non-transferrable by the organizer',
        'Token does not exist': 'This ticket does not exist',
        'Not token owner': 'You do not own this ticket',
        'Ticket already used': 'This ticket has already been used',
        'Not listed for resale': 'This ticket is not available for resale',
        'Cannot buy own ticket': 'You cannot buy your own ticket'
    };

    // Check for known error messages
    for (const [key, value] of Object.entries(errorMappings)) {
        if (message.includes(key)) {
            return value;
        }
    }

    // Handle network/gas errors
    if (message.includes('network') || message.includes('connection')) {
        return 'Network error. Please check your connection and try again';
    }
    if (message.includes('gas')) {
        return 'Transaction failed due to gas estimation. Please try again';
    }
    if (message.includes('nonce')) {
        return 'Transaction error. Please reset your MetaMask account or try again';
    }
    if (message.includes('timeout')) {
        return 'Transaction timed out. Please try again';
    }
    if (message.includes('denied') || message.includes('rejected')) {
        return 'Transaction was rejected. Please try again';
    }

    // MetaMask specific errors
    if (message.includes('metamask')) {
        if (message.includes('unlock')) {
            return 'Please unlock your MetaMask wallet';
        }
        if (message.includes('not found')) {
            return 'Please install MetaMask to continue';
        }
    }

    // Return cleaned original message if no mapping found
    return message.charAt(0).toUpperCase() + message.slice(1).replace(/['"{}]/g, '');
}

// Export functions if using modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showAlert,
        handleResponse,
        parseBlockchainError
    };
}
