function updateNoEventsMessage(hasVisibleEvents) {
    const eventList = document.querySelector('.event-list');
    const existingNoEvents = document.querySelector('.no-events');
    
    if (!hasVisibleEvents) {
        if (!existingNoEvents) {
            const noEventsHTML = `
                <div class="no-events">
                    <i class="fas fa-ticket-alt"></i>
                    <p>No tickets match your search criteria</p>
                    <button onclick="resetFilters()" class="reset-filters-btn">Reset Filters</button>
                </div>
            `;
            eventList.insertAdjacentHTML('beforeend', noEventsHTML);
        }
    } else if (existingNoEvents) {
        existingNoEvents.remove();
    }
}

function searchEvents() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const eventCards = document.querySelectorAll('.event-card');
    let hasVisibleEvents = false;

    eventCards.forEach(card => {
        const title = card.querySelector('h3').textContent.toLowerCase();
        const venue = card.querySelector('.location').textContent.toLowerCase();
        
        if (title.includes(searchTerm) || venue.includes(searchTerm)) {
            card.style.display = 'flex';
            hasVisibleEvents = true;
        } else {
            card.style.display = 'none';
        }
    });

    updateNoEventsMessage(hasVisibleEvents);
}

function applyFilters() {
    const priceFrom = parseFloat(document.getElementById('priceFrom').value) || 0;
    const priceTo = parseFloat(document.getElementById('priceTo').value) || Infinity;
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;

    if (priceTo < priceFrom) {
        showAlert('Maximum price cannot be less than minimum price.');
        return;
    }

    const eventCards = document.querySelectorAll('.event-card');
    let hasVisibleEvents = false;

    eventCards.forEach(card => {
        // Get price (remove 'ETH' and convert to number)
        const priceText = card.querySelector('.price').textContent;
        const price = parseFloat(priceText.replace(/[^\d.]/g, ''));

        // Get date (extract date string)
        const dateText = card.querySelector('.date').textContent;
        const dateMatch = dateText.match(/\d{4}-\d{2}-\d{2}/);
        const eventDate = dateMatch ? new Date(dateMatch[0]) : null;

        // Check price range
        const matchesPrice = price >= priceFrom && (priceTo === Infinity || price <= priceTo);

        // Check date range
        let matchesDate = true;
        if (dateFrom && dateTo && eventDate) {
            const fromDate = new Date(dateFrom);
            const toDate = new Date(dateTo);
            matchesDate = eventDate >= fromDate && eventDate <= toDate;
        }

        // Show/hide based on filters
        if (matchesPrice && matchesDate) {
            card.style.display = 'flex';
            hasVisibleEvents = true;
        } else {
            card.style.display = 'none';
        }
    });

    updateNoEventsMessage(hasVisibleEvents);
}

function resetFilters() {
    // Reset input values
    document.getElementById('priceFrom').value = '';
    document.getElementById('priceTo').value = '';
    document.getElementById('dateFrom').value = '';
    document.getElementById('dateTo').value = '';

    // Show all events
    document.querySelectorAll('.event-card').forEach(card => {
        card.style.display = 'flex';
    });

    // Remove no events message if it exists
    const noEventsDiv = document.querySelector('.no-events');
    if (noEventsDiv) {
        noEventsDiv.remove();
    }
}

// Add event listeners when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add listeners for filter buttons
    document.querySelector('.apply-btn').addEventListener('click', applyFilters);
    document.querySelector('.reset-btn').addEventListener('click', resetFilters);

    // Add listener for search input
    document.getElementById('searchInput').addEventListener('input', searchEvents);
});
