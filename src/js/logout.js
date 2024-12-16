document.addEventListener('DOMContentLoaded', function() {
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async function() {
            try {
                const response = await fetch('/logout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    cache: 'no-store'
                });
                const data = await response.json();
                
                if (data.success) {
                    window.localStorage.clear();
                    window.sessionStorage.clear();
                    
                    window.history.forward();
                    
                    window.location.replace(data.redirect);
                } else {
                    alert('Logout failed: ' + (data.message || 'Please try again.'));
                }
            } catch (error) {
                console.error('Error during logout:', error);
                alert('An error occurred during logout. Please try again.');
            }
        });
    }
});