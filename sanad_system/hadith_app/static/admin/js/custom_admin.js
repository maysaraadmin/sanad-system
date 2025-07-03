// Custom admin JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Add tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Enhance form validation feedback
    const forms = document.querySelectorAll('.form-row');
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                if (this.checkValidity()) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                    this.classList.add('is-invalid');
                }
            });
        });
    });

    // Add loading spinner for form submissions
    const submitButtons = document.querySelectorAll('.submit-row input[type="submit"]');
    submitButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const spinner = document.createElement('span');
            spinner.className = 'spinner-border spinner-border-sm me-2';
            this.insertAdjacentElement('beforebegin', spinner);
            this.disabled = true;
        });
    });

    // Add table sorting
    const tables = document.querySelectorAll('.changelist table');
    tables.forEach(table => {
        const headers = table.querySelectorAll('th');
        headers.forEach(header => {
            if (header.textContent.trim()) {
                header.addEventListener('click', function() {
                    const table = this.closest('table');
                    const tbody = table.querySelector('tbody');
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    
                    const index = Array.from(this.parentNode.children).indexOf(this);
                    const isNumeric = rows.every(row => !isNaN(row.cells[index].textContent));
                    
                    rows.sort((a, b) => {
                        const aValue = a.cells[index].textContent;
                        const bValue = b.cells[index].textContent;
                        
                        if (isNumeric) {
                            return parseFloat(aValue) - parseFloat(bValue);
                        }
                        return aValue.localeCompare(bValue);
                    });
                    
                    tbody.innerHTML = '';
                    rows.forEach(row => tbody.appendChild(row));
                });
            }
        });
    });
});
