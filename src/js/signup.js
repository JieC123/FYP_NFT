function validatePassword(password) {
    const minLength = 8;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    
    return {
        length: password.length >= minLength,
        uppercase: hasUpperCase,
        lowercase: hasLowerCase,
        special: hasSpecialChar,
        isValid: password.length >= minLength && hasUpperCase && hasLowerCase && hasSpecialChar
    };
}

function updatePasswordRequirements(password) {
    const requirements = validatePassword(password);
    
    Object.keys(requirements).forEach(req => {
        if (req !== 'isValid') {
            const element = document.getElementById(req);
            if (element) {
                if (requirements[req]) {
                    element.classList.add('requirement-met');
                } else {
                    element.classList.remove('requirement-met');
                }
            }
        }
    });
    
    return requirements.isValid;
}

document.getElementById('password').addEventListener('input', function(e) {
    updatePasswordRequirements(e.target.value);
});

document.getElementById('signupForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    if (!updatePasswordRequirements(password)) {
        alert('Please meet all password requirements');
        return;
    }

    if (password !== confirmPassword) {
        alert('Passwords do not match');
        return;
    }

    try {
        const formData = new FormData();
        formData.append('email', email);
        formData.append('password', password);
        formData.append('confirmPassword', confirmPassword);

        const response = await fetch('/signup', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (data.success) {
            alert(data.message);
            window.location.href = data.redirect;
        } else {
            alert(data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred during signup. Please try again.');
    }
});

const passwordInput = document.getElementById('password');
const requirementsDiv = document.querySelector('.password-requirements');

passwordInput.addEventListener('focus', function() {
    requirementsDiv.classList.add('show');
});

passwordInput.addEventListener('blur', function() {
    if (this.value.length === 0) {
        requirementsDiv.classList.remove('show');
    }
});