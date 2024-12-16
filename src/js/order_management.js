document.addEventListener('DOMContentLoaded', function() {
    const viewButtons = document.querySelectorAll('.action-btn.view');
    
    viewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const transactionId = this.getAttribute('data-transaction-id');
            window.location.href = `order_detail.html?id=${transactionId}`;
        });
    });
});
