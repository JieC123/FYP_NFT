document.addEventListener('DOMContentLoaded', function() {
    const printOrderBtn = document.getElementById('printOrderBtn');
    const sendEmailBtn = document.getElementById('sendEmailBtn');
    const cancelOrderBtn = document.getElementById('cancelOrderBtn');

    printOrderBtn.addEventListener('click', function() {
        // Add a print-specific class to the body
        document.body.classList.add('printing');
        
        // Print the document
        window.print();
        
        // Remove the print-specific class after printing
        window.onafterprint = function() {
            document.body.classList.remove('printing');
        };
    });

    sendEmailBtn.addEventListener('click', function() {
        // In a real application, you would typically make an API call to your backend here
        // For this example, we'll just show an alert
        const orderNumber = document.querySelector('.admin-header h2').textContent.split('#')[1];
        const customerEmail = document.querySelector('.detail-section p:nth-child(3)').textContent.split(': ')[1];
        
        alert(`Email sent to ${customerEmail} for order ${orderNumber}`);
    });

    cancelOrderBtn.addEventListener('click', function() {
        // This is a placeholder for the cancel order functionality
        if (confirm('Are you sure you want to cancel this order?')) {
            alert('Order cancelled successfully');
            // In a real application, you would make an API call to your backend here
            // and then update the UI based on the response
        }
    });
});
