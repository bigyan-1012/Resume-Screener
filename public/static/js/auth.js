// ============================================================
// auth.js — All authentication page JavaScript
// Extracted from inline <script> block in auth.html
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    const signupPass = document.getElementById('signup-password');
    const strengthMeter = document.getElementById('strength-meter');
    const strengthFill = document.getElementById('strength-fill');
    const strengthText = document.getElementById('strength-text');
    const signupForm = document.getElementById('signup-form');

    if (signupPass) {
        signupPass.addEventListener('input', () => {
            const val = signupPass.value;
            if (val.length === 0) {
                strengthMeter.style.display = 'none';
                return;
            }
            
            strengthMeter.style.display = 'block';
            
            // Simple strength checks
            let score = 0;
            if (val.length >= 6) score += 1;
            if (val.length >= 10) score += 1;
            if (/[A-Z]/.test(val)) score += 1;
            if (/[0-9]/.test(val)) score += 1;
            if (/[^A-Za-z0-9]/.test(val)) score += 1;
            
            let percent = (score / 5) * 100;
            strengthFill.style.width = percent + '%';
            
            if (score <= 1) {
                strengthFill.className = 'strength-fill weak';
                strengthText.textContent = 'Weak Password';
                strengthText.style.color = '#ef4444';
            } else if (score <= 3) {
                strengthFill.className = 'strength-fill medium';
                strengthText.textContent = 'Medium Password';
                strengthText.style.color = '#f59e0b';
            } else {
                strengthFill.className = 'strength-fill strong';
                strengthText.textContent = 'Strong Password';
                strengthText.style.color = '#10b981';
            }
        });
    }

    // Toggle Password Visibility
    const toggleIcons = document.querySelectorAll('.password-toggle-icon');
    toggleIcons.forEach(icon => {
        icon.addEventListener('click', () => {
            const input = icon.parentElement.querySelector('input');
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            }
        });
    });
});
