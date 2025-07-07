/**
 * Document Search JavaScript
 * This file provides initialization for the document search functionality
 * using the Stimulus controller pattern.
 */

// Import the Stimulus application
import { Application } from '@hotwired/stimulus';

// Import controllers
import DocumentSearchController from './controllers/document_search_controller';

// Initialize Stimulus
const application = Application.start();

// Register controllers
application.register('document-search', DocumentSearchController);

// Export for potential manual initialization
export { application };

// Legacy jQuery code for fallback support
if (window.jQuery) {
    (function($) {
        'use strict';

        // Initialize tooltips
        $(function() {
            $('[data-bs-toggle="tooltip"]').tooltip({
                container: 'body',
                trigger: 'hover focus'
            });
        });

        // Initialize Select2 if available
        if ($.fn.select2) {
            $('.form-select.select2').select2({
                theme: 'bootstrap-5',
                width: '100%',
                allowClear: true,
                language: {
                    noResults: function() { return 'No results found'; },
                    searching: function() { return 'Searching...'; }
                }
            });
        }
    })(jQuery);
}
