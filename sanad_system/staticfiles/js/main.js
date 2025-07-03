// Function to show toast messages
function showToast(icon, message) {
    const Toast = Swal.mixin({
        toast: true,
        position: 'top-start',
        showConfirmButton: false,
        timer: 5000,
        timerProgressBar: true,
        didOpen: function(toast) {
            toast.addEventListener('mouseenter', Swal.stopTimer);
            toast.addEventListener('mouseleave', Swal.resumeTimer);
        }
    });
    
    Toast.fire({
        icon: icon,
        title: message,
        background: 'var(--card-bg)',
        color: 'var(--text-color)',
        iconColor: 'var(--primary-color)'
    });
}

// Back to top function
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Back to Top Button
    const backToTopButton = document.getElementById('backToTop');
    
    if (backToTopButton) {
        window.onscroll = function() {
            if (document.body.scrollTop > 300 || document.documentElement.scrollTop > 300) {
                backToTopButton.style.display = 'block';
            } else {
                backToTopButton.style.display = 'none';
            }
        };
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            e.preventDefault();
            const target = document.querySelector(targetId);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add animation to cards on scroll
    const animateOnScroll = () => {
        const cards = document.querySelectorAll('.card, .card-hover');
        cards.forEach(card => {
            const cardPosition = card.getBoundingClientRect().top;
            const screenPosition = window.innerHeight / 1.3;
            
            if (cardPosition < screenPosition) {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }
        });
    };

    // Initialize animations
    window.addEventListener('scroll', animateOnScroll);
    animateOnScroll(); // Run once on page load

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Theme Switcher
    const themeBtns = document.querySelectorAll('.theme-btn');
    
    themeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const theme = this.getAttribute('data-theme');
            
            // Update active state
            document.querySelectorAll('.theme-btn').forEach(b => {
                b.classList.remove('active', 'bg-white', 'text-primary', 'bg-dark', 'text-white');
            });
            
            // Set active button styles based on theme
            if (theme === 'light') {
                this.classList.add('active', 'bg-white', 'text-primary');
            } else if (theme === 'dark') {
                this.classList.add('active', 'bg-dark', 'text-white');
            } else {
                this.classList.add('active', 'bg-white', 'text-primary');
            }
            
            // Set theme
            document.documentElement.setAttribute('data-bs-theme', theme);
            
            // Save preference
            fetch("/set-theme/", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                },
                body: JSON.stringify({theme: theme})
            }).then(() => {
                showToast('success', 'تم تغيير السمة بنجاح');
            }).catch(error => {
                console.error('Error setting theme:', error);
            });
        });
    });
});
