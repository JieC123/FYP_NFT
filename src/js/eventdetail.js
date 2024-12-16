document.addEventListener('DOMContentLoaded', function() {
    const ticketQuantitySelect = document.getElementById('ticketQuantity');
    const totalCostSection = document.getElementById('totalCostSection');
    const totalCostSpan = document.getElementById('totalCost');
    const viewMoreBtn = document.querySelector('.view-more');
    const ticketDetails = document.querySelector('.ticket-details');
    const buyBtn = document.querySelector('.buy-btn');

    const ticketPrice = parseFloat(document.querySelector('.price').getAttribute('data-ticket-price'));

    ticketQuantitySelect.addEventListener('change', function() {
        const quantity = parseInt(this.value);
        if (quantity > 0) {
            const totalCost = (quantity * ticketPrice).toFixed(2);
            totalCostSpan.textContent = totalCost;
            totalCostSection.classList.remove('hidden');
            buyBtn.classList.add('hidden');
        } else {
            totalCostSection.classList.add('hidden');
            buyBtn.classList.remove('hidden');
        }
    });

    viewMoreBtn.addEventListener('click', function() {
        ticketDetails.classList.toggle('hidden');
        this.textContent = ticketDetails.classList.contains('hidden') ? 'View More' : 'Less';
    });

    const initialBuyBtn = document.getElementById('initialBuyBtn');
    
    function updateTotalCost() {
        const quantity = parseInt(ticketQuantitySelect.value);
        const total = (quantity * ticketPrice).toFixed(2);
        
        // Store additional event details in sessionStorage
        sessionStorage.setItem('ticketQuantity', quantity);
        sessionStorage.setItem('ticketTotal', total);
        sessionStorage.setItem('ticketUnitPrice', ticketPrice);
        sessionStorage.setItem('eventTitle', document.querySelector('h1').textContent);
        sessionStorage.setItem('ticketType', document.querySelector('.ticket-type span').textContent);
        
        // Update the display
        const totalCostElement = document.getElementById('totalCost');
        if (totalCostElement) {
            totalCostElement.textContent = total;
        }
    }
    
    ticketQuantitySelect.addEventListener('change', updateTotalCost);
    
    initialBuyBtn.addEventListener('click', function(e) {
        e.preventDefault();
        const quantity = parseInt(ticketQuantitySelect.value);
        if (quantity === 0) {
            alert('Please select at least 1 ticket');
            return;
        }
        updateTotalCost();
        window.location.href = this.parentElement.href;
    });
});
