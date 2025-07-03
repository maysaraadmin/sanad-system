// Admin Interface Enhancements

// Add smooth scrolling to all links
document.querySelectorAll('a').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        if (this.getAttribute('href') && this.getAttribute('href').startsWith('#')) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth' });
            }
        }
    });
});

// Add loading state to buttons
document.querySelectorAll('.button').forEach(button => {
    button.addEventListener('click', function() {
        this.classList.add('loading');
        setTimeout(() => {
            this.classList.remove('loading');
        }, 2000); // Remove loading state after 2 seconds
    });
});

// Add tooltips to icons
document.querySelectorAll('.fas').forEach(icon => {
    const tooltip = document.createElement('span');
    tooltip.className = 'tooltip';
    tooltip.textContent = icon.parentElement.textContent.trim();
    icon.parentElement.appendChild(tooltip);
    
    icon.parentElement.addEventListener('mouseenter', () => {
        tooltip.style.display = 'block';
    });
    
    icon.parentElement.addEventListener('mouseleave', () => {
        tooltip.style.display = 'none';
    });
});

// Add table sorting functionality
document.querySelectorAll('.changelist table th').forEach(th => {
    if (!th.querySelector('input')) { // Skip filter columns
        th.addEventListener('click', function() {
            const table = this.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.rows);
            const columnIndex = Array.from(this.parentElement.children).indexOf(this);
            const isAscending = !this.classList.contains('sorted-asc');
            
            rows.sort((a, b) => {
                const aValue = a.cells[columnIndex].textContent;
                const bValue = b.cells[columnIndex].textContent;
                return isAscending ? (aValue.localeCompare(bValue)) : (bValue.localeCompare(aValue));
            });
            
            // Clear existing sort indicators
            table.querySelectorAll('th').forEach(th => {
                th.classList.remove('sorted-asc', 'sorted-desc');
            });
            
            // Add new sort indicator
            this.classList.add(isAscending ? 'sorted-asc' : 'sorted-desc');
            
            // Reorder rows
            rows.forEach(row => tbody.appendChild(row));
        });
    }
});

// Add form validation feedback
document.querySelectorAll('.form-row').forEach(formRow => {
    const input = formRow.querySelector('input, select, textarea');
    if (input) {
        input.addEventListener('input', function() {
            if (this.checkValidity()) {
                this.style.borderColor = '#4a90e2';
                this.style.boxShadow = '0 0 0 2px rgba(74, 144, 226, 0.2)';
            } else {
                this.style.borderColor = '#dc3545';
                this.style.boxShadow = '0 0 0 2px rgba(220, 53, 69, 0.2)';
            }
        });
    }
});

// Add smooth transitions to module hover states
document.querySelectorAll('.module-list li').forEach(module => {
    module.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
        this.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.1)';
    });
    
    module.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.05)';
    });
});

// Add search suggestions
document.querySelector('#changelist-search input').addEventListener('input', function() {
    const searchValue = this.value.toLowerCase();
    const suggestions = document.createElement('div');
    suggestions.className = 'search-suggestions';
    
    if (searchValue.length > 2) {
        // Add your search suggestion logic here
        suggestions.innerHTML = `
            <div class="suggestion">
                <i class="fas fa-search"></i>
                <span>بحث عن "${searchValue}"</span>
            </div>
        `;
        
        this.parentElement.appendChild(suggestions);
    } else {
        const existingSuggestions = this.parentElement.querySelector('.search-suggestions');
        if (existingSuggestions) {
            existingSuggestions.remove();
        }
    }
});
