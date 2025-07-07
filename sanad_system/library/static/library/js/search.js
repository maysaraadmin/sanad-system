document.addEventListener('DOMContentLoaded', function() {
    // Initialize Select2 for better dropdowns
    if (typeof $ !== 'undefined' && $.fn.select2) {
        $('.search-form select').select2({
            theme: 'bootstrap-5',
            width: '100%',
            placeholder: 'Select an option',
            allowClear: true
        });
    }

    // Handle search form submission
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const query = this.querySelector('input[name="query"]').value.trim();
            if (!query) {
                e.preventDefault();
                this.querySelector('input[name="query"]').focus();
            }
        });
    }

    // Add loading state to search button
    const searchButton = document.querySelector('.search-form button[type="submit"]');
    if (searchButton) {
        searchButton.addEventListener('click', function() {
            if (this.querySelector('.spinner-border')) return;
            
            const spinner = document.createElement('span');
            spinner.className = 'spinner-border spinner-border-sm me-1';
            spinner.setAttribute('role', 'status');
            spinner.setAttribute('aria-hidden', 'true');
            
            this.disabled = true;
            this.insertBefore(spinner, this.firstChild);
            this.querySelector('.btn-text').textContent = 'Searching...';
        });
    }

    // Handle clear search button
    const clearSearchButton = document.querySelector('.btn-clear-search');
    if (clearSearchButton) {
        clearSearchButton.addEventListener('click', function(e) {
            e.preventDefault();
            window.location.href = this.href;
        });
    }
});
