// Initialize the PDF viewer when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Configuration
    const config = {
        container: '#pdf-viewer-container',
        canvas: '#pdf-canvas',
        pageNumEl: '#page-num',
        pageCountEl: '#page-count',
        prevBtn: '#prev-page',
        nextBtn: '#next-page',
        zoomInBtn: '#zoom-in',
        zoomOutBtn: '#zoom-out',
        zoomLevelEl: '#zoom-level',
        fitWidthBtn: '#fit-width',
        fitPageBtn: '#fit-page',
        retryBtn: '#retry-btn',
        loadingEl: '#loading-message',
        errorEl: '#error-message',
        errorTextEl: '#error-text',
        defaultScale: 1.0,
        maxScale: 3.0,
        minScale: 0.3,
        scaleStep: 0.1,
        rtl: true,
        showPageNumbers: true,
        showZoomControls: true,
        onDocumentLoad: function() {
            console.log('Document loaded');
            const loadingEl = document.getElementById('loading-message');
            if (loadingEl) {
                loadingEl.style.opacity = '0';
                setTimeout(() => {
                    loadingEl.style.display = 'none';
                    const pdfViewer = document.getElementById('pdf-viewer');
                    if (pdfViewer) pdfViewer.style.display = 'flex';
                }, 300);
            }
            // Clear any existing timeouts to prevent multiple loads
            if (window.pdfLoadTimeout) {
                clearTimeout(window.pdfLoadTimeout);
                window.pdfLoadTimeout = null;
            }
        },
        onPageChange: function(pageNum, pageCount) {
            console.log(`Page ${pageNum} of ${pageCount}`);
        },
        onZoomChange: function(scale) {
            console.log(`Zoom: ${Math.round(scale * 100)}%`);
        },
        onError: function(error) {
            console.error('PDF error:', error);
            const errorEl = document.getElementById('error-message');
            const errorTextEl = document.getElementById('error-text');
            if (errorEl && errorTextEl) {
                let errorMessage = 'حدث خطأ أثناء تحميل المستند';
                if (error && error.message) {
                    errorMessage += `: ${error.message}`;
                    if (error.message.includes('Failed to fetch')) {
                        errorMessage = 'تعذر الاتصال بالخادم. يرجى التحقق من اتصال الشبكة والمحاولة مرة أخرى.';
                    } else if (error.message.includes('Invalid PDF structure')) {
                        errorMessage = 'ملف PDF تالف أو غير صالح.';
                    }
                }
                errorTextEl.textContent = errorMessage;
                errorEl.classList.remove('hidden');
                
                // Show the error message for at least 5 seconds
                setTimeout(() => {
                    if (errorEl) {
                        errorEl.classList.add('hidden');
                    }
                }, 5000);
            }
        }
    };

    // Initialize the PDF viewer
    const viewer = new PDFViewer(config);
    
    // Store the viewer instance globally for debugging
    window.pdfViewerInstance = viewer;
    
    // Get the PDF URL from the data attribute
    const pdfContainer = document.getElementById('pdf-viewer-container');
    if (!pdfContainer) return;
    
    const pdfUrl = pdfContainer.dataset.pdfUrl;
    if (!pdfUrl) {
        console.error('No PDF URL found');
        return;
    }
    
    const cacheBustedUrl = pdfUrl + (pdfUrl.includes('?') ? '&' : '?') + 't=' + new Date().getTime();
    console.log('PDF URL:', pdfUrl);
    console.log('Cache-busted URL:', cacheBustedUrl);
    
    // Try loading the PDF
    try {
        console.log('Attempting to load PDF...');
        
        // Add authentication headers if needed
        const headers = {};
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken.value;
        }
        
        // Pass headers as part of the options object
        const options = { 
            headers: headers,
            withCredentials: true
        };
        
        viewer.load(cacheBustedUrl, options);
    } catch (error) {
        console.error('Failed to load PDF:', error);
        const errorEl = document.getElementById('error-message');
        const errorTextEl = document.getElementById('error-text');
        if (errorEl && errorTextEl) {
            errorTextEl.textContent = 'فشل تحميل الملف. يرجى التأكد من صحة الرابط.';
            errorEl.classList.remove('hidden');
        }
    }
    
    // Handle window resize with debounce
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            if (viewer && typeof viewer.resize === 'function') {
                viewer.resize();
            }
        }, 250);
    });
    
    // Handle retry button
    const retryBtn = document.getElementById('retry-btn');
    if (retryBtn) {
        retryBtn.addEventListener('click', function() {
            const errorEl = document.getElementById('error-message');
            if (errorEl) errorEl.classList.add('hidden');
            if (viewer && typeof viewer.load === 'function') {
                viewer.load(cacheBustedUrl);
            }
        });
    }
    
    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (!viewer) return;
        
        if (e.key === 'ArrowLeft' && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            if (viewer.nextPage) viewer.nextPage();
        } else if (e.key === 'ArrowRight' && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            if (viewer.prevPage) viewer.prevPage();
        } else if (e.key === '+' || e.key === '=') {
            e.preventDefault();
            if (viewer.zoomIn) viewer.zoomIn();
        } else if (e.key === '-' || e.key === '_') {
            e.preventDefault();
            if (viewer.zoomOut) viewer.zoomOut();
        } else if (e.key === '0' || e.key === ')') {
            e.preventDefault();
            if (viewer.zoomReset) viewer.zoomReset();
        } else if (e.key === 'f') {
            e.preventDefault();
            if (viewer.fitWidth) viewer.fitWidth();
        } else if (e.key === 'p') {
            e.preventDefault();
            if (viewer.fitPage) viewer.fitPage();
        }
    });
});
