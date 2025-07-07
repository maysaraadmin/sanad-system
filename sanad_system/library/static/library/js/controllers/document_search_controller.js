// document_search_controller.js
import { Controller } from '@hotwired/stimulus';
import { debounce } from 'lodash';

export default class extends Controller {
    static targets = [
        'form', 
        'query', 
        'category', 
        'fileType', 
        'submitButton', 
        'clearButton'
    ];
    
    static values = {
        debounceDelay: { type: Number, default: 300 },
        minQueryLength: { type: Number, default: 2 },
        searchUrl: String
    };
    
    initialize() {
        // Debounce the search input handler
        this.debouncedSearch = debounce(this.performSearch.bind(this), this.debounceDelayValue);
        
        // Initialize state
        this.isSubmitting = false;
    }
    
    connect() {
        console.log('Document Search Controller connected');
        this.updateClearButtonState();
    }
    
    // Handle search input events with debouncing
    handleInput(event) {
        this.debouncedSearch();
    }
    
    // Handle category change events
    handleCategoryChange(event) {
        this.updateClearButtonState();
        this.performSearch();
    }
    
    // Handle file type change events
    handleFileTypeChange(event) {
        this.updateClearButtonState();
        this.performSearch();
    }
    
    // Handle form submission
    handleSubmit(event) {
        if (event) event.preventDefault();
        
        const query = this.queryTarget.value ? this.queryTarget.value.trim() : '';
        
        // Validate query length if there is a query
        if (query && query.length < this.minQueryLengthValue) {
            this.showValidationError(`Search query must be at least ${this.minQueryLengthValue} characters`);
            return false;
        }
        
        // Show loading state
        this.showLoadingState(true);
        
        // Submit the form
        this.formTarget.submit();
        return true;
    }
    
    // Clear all filters and reset the form
    clearFilters(event) {
        if (event) event.preventDefault();
        
        // Reset form fields
        if (this.queryTarget) this.queryTarget.value = '';
        if (this.categoryTarget) this.categoryTarget.value = '';
        if (this.fileTypeTarget) this.fileTypeTarget.value = '';
        
        // Trigger change events for Select2 if it's being used
        if (window.jQuery && window.jQuery.fn.select2) {
            if (this.categoryTarget) $(this.categoryTarget).trigger('change');
            if (this.fileTypeTarget) $(this.fileTypeTarget).trigger('change');
        }
        
        // Update UI
        this.updateClearButtonState();
        
        // If we're on a search results page, navigate to the base search URL
        if (this.searchUrlValue) {
            window.location.href = this.searchUrlValue;
        } else {
            // Otherwise, submit the form to show all results
            this.formTarget.submit();
        }
    }
    
    // Perform the search (debounced)
    performSearch() {
        // Only perform search if we have a query that meets the minimum length
        const query = this.queryTarget ? this.queryTarget.value.trim() : '';
        if (query && query.length < this.minQueryLengthValue) {
            return;
        }
        
        this.handleSubmit();
    }
    
    // Show loading state on the submit button
    showLoadingState(show = true) {
        if (!this.submitButtonTarget) return;
        
        if (show) {
            // Store original content if not already stored
            if (!this.originalButtonContent) {
                this.originalButtonContent = this.submitButtonTarget.innerHTML;
            }
            
            // Update button state
            this.submitButtonTarget.disabled = true;
            this.submitButtonTarget.innerHTML = `
                <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                <span class="button-text">${this.submitButtonTarget.dataset.searchingText || 'Searching...'}</span>
            `;
        } else if (this.originalButtonContent) {
            // Restore original content
            this.submitButtonTarget.disabled = false;
            this.submitButtonTarget.innerHTML = this.originalButtonContent;
        }
    }
    
    // Show validation error message
    showValidationError(message) {
        // Remove any existing error messages
        this.removeValidationError();
        
        // Create and show error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show mt-3';
        errorDiv.setAttribute('role', 'alert');
        errorDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insert error message at the top of the form
        this.formTarget.insertBefore(errorDiv, this.formTarget.firstChild);
        
        // Focus the search input
        if (this.queryTarget) this.queryTarget.focus();
    }
    
    // Remove validation error message
    removeValidationError() {
        const existingError = this.formTarget.querySelector('.alert-danger');
        if (existingError) {
            existingError.remove();
        }
    }
    
    // Update the clear button state based on form values
    updateClearButtonState() {
        if (!this.clearButtonTarget) return;
        
        let hasValue = false;
        
        // Check if any form control has a value
        if (this.queryTarget && this.queryTarget.value.trim() !== '') {
            hasValue = true;
        } else if (this.categoryTarget && this.categoryTarget.value !== '') {
            hasValue = true;
        } else if (this.fileTypeTarget && this.fileTypeTarget.value !== '') {
            hasValue = true;
        }
        
        // Toggle button state
        this.clearButtonTarget.disabled = !hasValue;
        this.clearButtonTarget.classList.toggle('disabled', !hasValue);
    }
}

// Register the controller
import { Application } from '@hotwired/stimulus';
const application = Application.start();
application.register('document-search', DocumentSearchController);
