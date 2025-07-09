class PDFViewer {
    constructor(options = {}) {
        // Default configuration
        this.config = {
            // DOM Elements
            container: options.container || '#pdf-viewer-container',
            canvas: options.canvas || '#pdf-canvas',
            pageNumEl: options.pageNumEl || '#page-num',
            pageCountEl: options.pageCountEl || '#page-count',
            prevBtn: options.prevBtn || '#prev-page',
            nextBtn: options.nextBtn || '#next-page',
            zoomInBtn: options.zoomInBtn || '#zoom-in',
            zoomOutBtn: options.zoomOutBtn || '#zoom-out',
            zoomLevelEl: options.zoomLevelEl || '#zoom-level',
            fitWidthBtn: options.fitWidthBtn || '#fit-width',
            fitPageBtn: options.fitPageBtn || '#fit-page',
            retryBtn: options.retryBtn || '#retry-btn',
            loadingEl: options.loadingEl || '#loading-message',
            errorEl: options.errorEl || '#error-message',
            errorTextEl: options.errorTextEl || '#error-text',
            
            // Viewer settings
            defaultScale: options.defaultScale || 1.0,
            maxScale: options.maxScale || 3.0,
            minScale: options.minScale || 0.3,
            scaleStep: options.scaleStep || 0.1,
            
            // UI settings
            rtl: options.rtl !== undefined ? options.rtl : true, // RTL by default
            showPageNumbers: options.showPageNumbers !== false, // Show page numbers by default
            showZoomControls: options.showZoomControls !== false, // Show zoom controls by default
            
            // Callbacks
            onDocumentLoad: options.onDocumentLoad || null,
            onPageChange: options.onPageChange || null,
            onZoomChange: options.onZoomChange || null,
            onError: options.onError || null
        };
        
        // Localization
        this.i18n = {
            loading: 'جاري التحميل...',
            error: 'حدث خطأ',
            retry: 'إعادة المحاولة',
            page: 'صفحة',
            of: 'من',
            zoomIn: 'تكبير',
            zoomOut: 'تصغير',
            fitWidth: 'تناسب العرض',
            fitPage: 'تناسب الصفحة',
            previousPage: 'الصفحة السابقة',
            nextPage: 'الصفحة التالية',
            download: 'تحميل',
            ...(options.i18n || {})
        };

        // State
        this.state = {
            pdfDoc: null,
            pageNum: 1,
            pageRendering: false,
            pageNumPending: null,
            scale: this.config.defaultScale,
            isInitialized: false,
            resizeObserver: null,
            isRTL: this.config.rtl,
            totalPages: 0,
            currentPage: 0,
            currentZoom: 100,
            isFullscreen: false,
            isLoading: false,
            hasError: false,
            errorMessage: '',
            renderOptions: {
                // Default PDF.js render options
                scale: this.config.defaultScale,
                printResolution: 150,
                backgroundColor: 0xFFFFFF,
                disableAutoFetch: false,
                disableFontFace: false,
                enableXfa: true,
                isEvalSupported: true,
                useSystemFonts: false,
                cMapUrl: 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.4.120/cmaps/',
                cMapPacked: true,
                standardFontDataUrl: 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.4.120/standard_fonts/'
            },
            // Store references to DOM elements
            elements: {},
            fitToWidthScale: null,
            fitToPageScale: null
        };

        // Bind methods
        this.init = this.init.bind(this);
        this.loadDocument = this.loadDocument.bind(this);
        this.renderPage = this.renderPage.bind(this);
        this.queueRenderPage = this.queueRenderPage.bind(this);
        this.onPrevPage = this.onPrevPage.bind(this);
        this.onNextPage = this.onNextPage.bind(this);
        this.zoomIn = this.zoomIn.bind(this);
        this.zoomOut = this.zoomOut.bind(this);
        this.fitWidth = this.fitWidth.bind(this);
        this.fitPage = this.fitPage.bind(this);
        this.handleKeyDown = this.handleKeyDown.bind(this);
        this.handleResize = this.handleResize.bind(this);
        this.cleanup = this.cleanup.bind(this);
        this.showLoading = this.showLoading.bind(this);
        this.hideLoading = this.hideLoading.bind(this);
        this.showError = this.showError.bind(this);
        this.hideError = this.hideError.bind(this);
        this.setZoom = this.setZoom.bind(this);
        this.updateButtonStates = this.updateButtonStates.bind(this);
        this.updateZoomLevel = this.updateZoomLevel.bind(this);
        this.updateLoadingProgress = this.updateLoadingProgress.bind(this);
        this.clearCanvas = this.clearCanvas.bind(this);
        this.updatePageCount = this.updatePageCount.bind(this);
    }

    async init() {
        try {
            // Initialize PDF.js worker
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';

            // Get DOM elements
            this.elements = {
                container: document.querySelector(this.config.container),
                canvas: document.querySelector(this.config.canvas),
                ctx: document.querySelector(this.config.canvas)?.getContext('2d'),
                pageNumEl: document.querySelector(this.config.pageNumEl),
                pageCountEl: document.querySelector(this.config.pageCountEl),
                zoomLevelEl: document.querySelector(this.config.zoomLevelEl),
                prevBtn: document.querySelector(this.config.prevBtn),
                nextBtn: document.querySelector(this.config.nextBtn),
                zoomInBtn: document.querySelector(this.config.zoomInBtn),
                zoomOutBtn: document.querySelector(this.config.zoomOutBtn),
                fitWidthBtn: document.querySelector(this.config.fitWidthBtn),
                fitPageBtn: document.querySelector(this.config.fitPageBtn),
                retryBtn: document.querySelector(this.config.retryBtn),
                loadingEl: document.querySelector(this.config.loadingEl),
                errorEl: document.querySelector(this.config.errorEl),
                errorTextEl: document.querySelector(this.config.errorTextEl)
            };

            // Check if required elements exist
            if (!this.elements.canvas || !this.elements.ctx) {
                throw new Error('Canvas element not found');
            }
            
            // Set initial UI state
            this.updateUIState();
            
            // Set RTL direction if enabled
            if (this.config.rtl && this.elements.container) {
                this.elements.container.dir = 'rtl';
            }

            // Set initial state
            this.state.isInitialized = true;
            
            // Initialize event listeners
            this.initEventListeners();
            
            // Initialize resize observer
            this.initResizeObserver();
            
            // Dispatch initialized event
            this.dispatchEvent('initialized');
            
            return true;
            
        } catch (error) {
            console.error('Error initializing PDF viewer:', error);
            this.showError('Failed to initialize PDF viewer: ' + (error.message || 'Unknown error'));
            this.dispatchEvent('error', { error });
            return false;
        }
    }

    initEventListeners() {
        // Navigation buttons
        if (this.elements.prevBtn) {
            this.elements.prevBtn.addEventListener('click', this.onPrevPage);
        }
        if (this.elements.nextBtn) {
            this.elements.nextBtn.addEventListener('click', this.onNextPage);
        }

        // Zoom controls
        if (this.elements.zoomInBtn) {
            this.elements.zoomInBtn.addEventListener('click', this.zoomIn);
        }
        if (this.elements.zoomOutBtn) {
            this.elements.zoomOutBtn.addEventListener('click', this.zoomOut);
        }
        if (this.elements.fitWidthBtn) {
            this.elements.fitWidthBtn.addEventListener('click', this.fitWidth);
        }
        if (this.elements.fitPageBtn) {
            this.elements.fitPageBtn.addEventListener('click', this.fitPage);
        }

        // Keyboard navigation
        document.addEventListener('keydown', this.handleKeyDown);

        // Handle window resize with debounce
        this.resizeTimer = null;
        window.addEventListener('resize', this.handleResize);

        // Handle page visibility changes
        document.addEventListener('visibilitychange', this.handleVisibilityChange);

        // Handle beforeunload for cleanup
        window.addEventListener('beforeunload', this.cleanup);
    }

    zoomIn() {
        if (this.state.scale >= this.config.maxScale) return;
        
        // Calculate new scale with rounding to avoid floating point precision issues
        const newScale = Math.min(
            Math.round((this.state.scale + this.config.scaleStep) * 100) / 100, 
            this.config.maxScale
        );
        
        this.setZoom(newScale);
    }
    
    zoomOut() {
        if (this.state.scale <= this.config.minScale) return;
        
        // Calculate new scale with rounding to avoid floating point precision issues
        const newScale = Math.max(
            Math.round((this.state.scale - this.config.scaleStep) * 100) / 100, 
            this.config.minScale
        );
        
        this.setZoom(newScale);
    }
    
    setZoom(scale) {
        if (scale === this.state.scale) return;
        
        // Clamp scale to min/max values
        scale = Math.max(this.config.minScale, Math.min(scale, this.config.maxScale));
        
        // Update state
        this.state.scale = scale;
        this.state.currentZoom = Math.round(scale * 100);
        
        // Re-render the current page with new scale
        this.queueRenderPage(this.state.pageNum);
        
        // Update UI
        this.updateZoomLevel();
        this.updateButtonStates();
        
        // Dispatch zoom change event
        this.dispatchEvent('zoomChanged', { 
            scale: this.state.scale,
            zoomLevel: this.state.currentZoom
        });
        
        // Call the onZoomChange callback if provided
        if (typeof this.config.onZoomChange === 'function') {
            this.config.onZoomChange({
                scale: this.state.scale,
                zoomLevel: this.state.currentZoom
            });
        }
    }

    async loadDocument(url) {
        try {
            this.showLoading();
            this.state.isLoading = true;
            this.state.hasError = false;
            this.hideError();
            
            // Reset state
            this.state.pdfDoc = null;
            this.state.pageNum = 1;
            this.state.scale = this.config.defaultScale;
            this.state.totalPages = 0;
            this.state.currentPage = 0;
            
            // Clear canvas
            this.clearCanvas();
            
            // Load the PDF document with progress tracking
            const loadingTask = pdfjsLib.getDocument({
                url: url,
                cMapUrl: this.state.renderOptions.cMapUrl,
                cMapPacked: this.state.renderOptions.cMapPacked,
                standardFontDataUrl: this.state.renderOptions.standardFontDataUrl,
                disableAutoFetch: this.state.renderOptions.disableAutoFetch,
                disableFontFace: this.state.renderOptions.disableFontFace,
                enableXfa: this.state.renderOptions.enableXfa,
                isEvalSupported: this.state.renderOptions.isEvalSupported,
                useSystemFonts: this.state.renderOptions.useSystemFonts
            });
            
            // Show loading progress if available
            if (loadingTask.onProgress) {
                loadingTask.onProgress((progress) => {
                    const percent = Math.round((progress.loaded / progress.total) * 100);
                    this.updateLoadingProgress(percent);
                });
            }
            
            // Load the document
            this.state.pdfDoc = await loadingTask.promise;
            this.state.totalPages = this.state.pdfDoc.numPages;
            
            // Update UI
            this.updatePageCount();
            this.updateZoomLevel();
            
            // Render the first page
            await this.renderPage(1);
            
            // Update state
            this.state.isLoading = false;
            this.hideLoading();
            
            // Dispatch document loaded event
            this.dispatchEvent('documentLoaded', {
                pages: this.state.totalPages,
                url: url
            });
            
            // Auto-fit width on initial load
            this.fitWidth();
            
            return this.state.pdfDoc;
            
        } catch (error) {
            console.error('Error loading PDF:', error);
            this.state.isLoading = false;
            this.state.hasError = true;
            this.state.errorMessage = error.message || 'Failed to load PDF document';
            
            this.showError(this.state.errorMessage);
            this.dispatchEvent('error', { 
                error: error,
                message: this.state.errorMessage
            });
            
            throw error;
        }
    }

    hideLoading() {
        if (this.elements.loadingEl) {
            this.elements.loadingEl.style.display = 'none';
        }
    }

    showError(message) {
        if (this.elements.errorEl && this.elements.errorTextEl) {
            this.elements.errorTextEl.textContent = message;
            this.elements.errorEl.style.display = 'block';
        }
    }

    hideError() {
        if (this.elements.errorEl) {
            this.elements.errorEl.style.display = 'none';
        }
    }

    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(`pdfViewer:${eventName}`, { 
            detail: { ...detail, viewer: this }
        });
        document.dispatchEvent(event);
    }

    cleanup() {
        // Remove event listeners
        if (this.elements.prevBtn) {
            this.elements.prevBtn.removeEventListener('click', this.onPrevPage);
        }
        if (this.elements.nextBtn) {
            this.elements.nextBtn.removeEventListener('click', this.onNextPage);
        }
        if (this.elements.zoomInBtn) {
            this.elements.zoomInBtn.removeEventListener('click', this.zoomIn);
        }
        if (this.elements.zoomOutBtn) {
            this.elements.zoomOutBtn.removeEventListener('click', this.zoomOut);
        }
        if (this.elements.fitWidthBtn) {
            this.elements.fitWidthBtn.removeEventListener('click', this.fitWidth);
        }
        if (this.elements.fitPageBtn) {
            this.elements.fitPageBtn.removeEventListener('click', this.fitPage);
        }

        // Remove window event listeners
        document.removeEventListener('keydown', this.handleKeyDown);
        window.removeEventListener('resize', this.handleResize);
        document.removeEventListener('visibilitychange', this.handleVisibilityChange);
        window.removeEventListener('beforeunload', this.cleanup);

        // Clear any pending timeouts
        if (this.resizeTimer) {
            clearTimeout(this.resizeTimer);
        }

        // Clean up PDF document
        if (this.state.pdfDoc) {
            this.state.pdfDoc.cleanup();
            this.state.pdfDoc = null;
        }

        // Clear canvas
        if (this.elements.ctx) {
            this.elements.ctx.clearRect(
                0, 
                0, 
                this.elements.canvas.width, 
                this.elements.canvas.height
            );
        }

        // Reset state
        this.state = {
            pdfDoc: null,
            pageNum: 1,
            pageRendering: false,
            pageNumPending: null,
            scale: this.config.defaultScale,
            isInitialized: false,
            resizeObserver: null,
            isRTL: this.config.rtl,
            totalPages: 0,
            currentPage: 0,
            currentZoom: 100,
            isFullscreen: false,
            isLoading: false,
            hasError: false,
            errorMessage: '',
            renderOptions: {
                // Default PDF.js render options
                scale: this.config.defaultScale,
                printResolution: 150,
                backgroundColor: 0xFFFFFF,
                disableAutoFetch: false,
                disableFontFace: false,
                enableXfa: true,
                isEvalSupported: true,
                useSystemFonts: false,
                cMapUrl: 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.4.120/cmaps/',
                cMapPacked: true,
                standardFontDataUrl: 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.4.120/standard_fonts/'
            },
            // Store references to DOM elements
            elements: {},
            fitToWidthScale: null,
            fitToPageScale: null
        };
    }

    async renderPage(num, scale = null) {
        // Don't re-render if already rendering
        if (this.state.pageRendering) {
            this.state.pageNumPending = num;
            return;
        }

        this.state.pageRendering = true;
        this.state.currentPage = num;
        
        // Update page number display
        if (this.elements.pageNumEl) {
            this.elements.pageNumEl.value = num;
        }

        try {
            // Get the page
            const page = await this.state.pdfDoc.getPage(num);
            
            // Set scale if provided
            if (scale !== null) {
                this.state.scale = scale;
            }
            
            // Calculate viewport
            const viewport = page.getViewport({ 
                scale: this.state.scale,
                rotation: 0,
                offsetX: 0,
                offsetY: 0,
                dontFlip: false
            });
            
            // Set canvas dimensions
            const canvas = this.elements.canvas;
            const context = this.elements.ctx;
            const outputScale = window.devicePixelRatio || 1;
            
            // Set canvas dimensions
            canvas.width = Math.floor(viewport.width * outputScale);
            canvas.height = Math.floor(viewport.height * outputScale);
            canvas.style.width = `${Math.floor(viewport.width)}px`;
            canvas.style.height = `${Math.floor(viewport.height)}px`;
            
            // Scale the canvas context
            context.setTransform(outputScale, 0, 0, outputScale, 0, 0);
            
            // Render PDF page
            const renderContext = {
                canvasContext: context,
                viewport: viewport,
                intent: 'display',
                renderInteractiveForms: true,
                enableWebGL: false,
                transform: null,
                imageLayer: null,
                canvasContext: context,
                viewport: viewport,
                background: this.state.renderOptions.backgroundColor,
                disableAutoFetch: this.state.renderOptions.disableAutoFetch,
                disableFontFace: this.state.renderOptions.disableFontFace,
                enableXfa: this.state.renderOptions.enableXfa,
                isEvalSupported: this.state.renderOptions.isEvalSupported,
                useSystemFonts: this.state.renderOptions.useSystemFonts,
                printResolution: this.state.renderOptions.printResolution
            };
            
            // Clear the canvas
            context.clearRect(0, 0, canvas.width, canvas.height);
            
            // Render the page
            await page.render(renderContext).promise;
            
            // Update state
            this.state.pageRendering = false;
            this.state.pageNum = num;
            this.updateButtonStates();
            
            // Render next page if pending
            if (this.state.pageNumPending !== null) {
                const nextPageNum = this.state.pageNumPending;
                this.state.pageNumPending = null;
                await this.renderPage(nextPageNum);
            }
            
            // Dispatch page rendered event
            this.dispatchEvent('pageRendered', { 
                pageNumber: num,
                totalPages: this.state.totalPages,
                scale: this.state.scale
            });
            
        } catch (error) {
            console.error('Error rendering page:', error);
            this.state.pageRendering = false;
            this.showError('Error rendering PDF page: ' + (error.message || 'Unknown error'));
            this.dispatchEvent('error', { 
                error: error,
                message: 'Failed to render page',
                pageNumber: num
            });
        }
    }
    
    queueRenderPage(num) {
        if (this.state.pageRendering) {
            this.state.pageNumPending = num;
        } else {
            this.renderPage(num);
        }
    }
    
    onPrevPage() {
        if (this.state.pageNum <= 1) return;
        this.renderPage(this.state.pageNum - 1);
    }
    
    onNextPage() {
        if (!this.state.pdfDoc || this.state.pageNum >= this.state.totalPages) return;
        this.renderPage(this.state.pageNum + 1);
    }
    
    fitWidth() {
        if (!this.state.pdfDoc || !this.elements.container) return;
        
        // Get container width (accounting for padding)
        const container = this.elements.container;
        const containerWidth = container.clientWidth - 40; // Adjust padding as needed
        
        // Get the current page to calculate scale
        this.state.pdfDoc.getPage(this.state.pageNum).then(page => {
            const viewport = page.getViewport(1.0);
            const scale = containerWidth / viewport.width;
            
            // Store the fit-to-width scale
            this.state.fitToWidthScale = scale;
            this.state.fitToPageScale = null;
            
            // Apply the scale
            this.setZoom(scale);
        });
    }
    
    fitPage() {
        if (!this.state.pdfDoc || !this.elements.container) return;
        
        // Get container dimensions (accounting for padding and UI elements)
        const container = this.elements.container;
        const containerWidth = container.clientWidth - 40; // Adjust padding as needed
        const containerHeight = window.innerHeight - 200; // Account for UI elements
        
        // Get the current page to calculate scale
        this.state.pdfDoc.getPage(this.state.pageNum).then(page => {
            const viewport = page.getViewport(1.0);
            
            // Calculate scale to fit both width and height
            const scale = Math.min(
                containerWidth / viewport.width,
                containerHeight / viewport.height
            );
            
            // Store the fit-to-page scale
            this.state.fitToPageScale = scale;
            this.state.fitToWidthScale = null;
            
            // Apply the scale
            this.setZoom(scale);
        });
    }
    
    updateButtonStates() {
        if (!this.state.pdfDoc) return;
        
        const { prevBtn, nextBtn, zoomInBtn, zoomOutBtn, fitWidthBtn, fitPageBtn } = this.elements;
        
        // Update previous/next buttons
        if (prevBtn) {
            prevBtn.disabled = this.state.pageNum <= 1;
            prevBtn.title = this.i18n.previousPage;
        }
        
        if (nextBtn) {
            nextBtn.disabled = this.state.pageNum >= this.state.totalPages;
            nextBtn.title = this.i18n.nextPage;
        }
        
        // Update zoom buttons
        if (zoomInBtn) {
            zoomInBtn.disabled = this.state.scale >= this.config.maxScale;
            zoomInBtn.title = this.i18n.zoomIn;
        }
        
        if (zoomOutBtn) {
            zoomOutBtn.disabled = this.state.scale <= this.config.minScale;
            zoomOutBtn.title = this.i18n.zoomOut;
        }
        
        // Update fit buttons
        if (fitWidthBtn) {
            fitWidthBtn.title = this.i18n.fitWidth;
            fitWidthBtn.classList.toggle('active', this.state.scale === this.state.fitToWidthScale);
        }
        
        if (fitPageBtn) {
            fitPageBtn.title = this.i18n.fitPage;
            fitPageBtn.classList.toggle('active', this.state.scale === this.state.fitToPageScale);
        }
        
        // Update zoom level display
        this.updateZoomLevel();
    }
    
    updateZoomLevel() {
        if (this.elements.zoomLevelEl) {
            this.elements.zoomLevelEl.textContent = `${Math.round(this.state.scale * 100)}%`;
        }
    }
    
    updatePageCount() {
        if (this.elements.pageCountEl) {
            this.elements.pageCountEl.textContent = this.state.totalPages;
        }
    }
    
    updateLoadingProgress(percent) {
        if (this.elements.loadingEl) {
            const progressEl = this.elements.loadingEl.querySelector('.progress');
            if (progressEl) {
                progressEl.style.width = `${percent}%`;
            }
            
            const textEl = this.elements.loadingEl.querySelector('.loading-text');
            if (textEl) {
                textEl.textContent = `${this.i18n.loading} ${percent}%`;
            }
        }
    }
    
    clearCanvas() {
        const canvas = this.elements.canvas;
        if (canvas) {
            const context = canvas.getContext('2d');
            context.clearRect(0, 0, canvas.width, canvas.height);
        }
    }
    
    showLoading(message = this.i18n.loading) {
        if (this.elements.loadingEl) {
            const textEl = this.elements.loadingEl.querySelector('.loading-text');
            if (textEl) {
                textEl.textContent = message;
            }
            this.elements.loadingEl.style.display = 'flex';
        }
    }
    
    hideLoading() {
        if (this.elements.loadingEl) {
            this.elements.loadingEl.style.display = 'none';
        }
    }
    
    showError(message) {
        if (this.elements.errorEl && this.elements.errorTextEl) {
            this.elements.errorTextEl.textContent = message || this.i18n.error;
            this.elements.errorEl.style.display = 'block';
            
            // Auto-hide error after 5 seconds
            if (this.errorTimeout) {
                clearTimeout(this.errorTimeout);
            }
            
            this.errorTimeout = setTimeout(() => {
                this.hideError();
            }, 5000);
        }
    }
    
    hideError() {
        if (this.elements.errorEl) {
            this.elements.errorEl.style.display = 'none';
        }
        
        if (this.errorTimeout) {
            clearTimeout(this.errorTimeout);
            this.errorTimeout = null;
        }
    }
    
    initEventListeners() {
        // Window events
        window.addEventListener('resize', this.handleResize);
        document.addEventListener('visibilitychange', this.handleVisibilityChange);
        document.addEventListener('keydown', this.handleKeyDown);
        window.addEventListener('beforeunload', this.cleanup);
        
        // Container events
        if (this.elements.container) {
            this.elements.container.addEventListener('wheel', this.handleWheel, { passive: false });
        }
        
        // Navigation buttons
        if (this.elements.prevBtn) {
            this.elements.prevBtn.addEventListener('click', () => this.onPrevPage());
        }
        
        if (this.elements.nextBtn) {
            this.elements.nextBtn.addEventListener('click', () => this.onNextPage());
        }
        
        // Zoom controls
        if (this.elements.zoomInBtn) {
            this.elements.zoomInBtn.addEventListener('click', () => this.zoomIn());
        }
        
        if (this.elements.zoomOutBtn) {
            this.elements.zoomOutBtn.addEventListener('click', () => this.zoomOut());
        }
        
        // Fit controls
        if (this.elements.fitWidthBtn) {
            this.elements.fitWidthBtn.addEventListener('click', () => this.fitWidth());
        }
        
        if (this.elements.fitPageBtn) {
            this.elements.fitPageBtn.addEventListener('click', () => this.fitPage());
        }
        
        // Page number input
        if (this.elements.pageNumEl) {
            this.elements.pageNumEl.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    this.handlePageInput(e);
                }
            });
            
            this.elements.pageNumEl.addEventListener('blur', (e) => {
                this.handlePageInputBlur(e);
            });
        }
        
        // Retry button
        if (this.elements.retryBtn) {
            this.elements.retryBtn.addEventListener('click', () => {
                if (this.state.lastErrorUrl) {
                    this.loadDocument(this.state.lastErrorUrl);
                }
            });
        }
    }
    
    initResizeObserver() {
        if (typeof ResizeObserver !== 'undefined' && this.elements.container) {
            this.state.resizeObserver = new ResizeObserver((entries) => {
                for (const entry of entries) {
                    if (entry.target === this.elements.container) {
                        this.handleResize();
                    }
                }
            });
            
            this.state.resizeObserver.observe(this.elements.container);
        }
    }
    
    updateUIState() {
        // Update button states
        this.updateButtonStates();
        
        // Update page count display
        if (this.elements.pageCountEl) {
            this.elements.pageCountEl.textContent = this.state.totalPages || '--';
        }
        
        // Update page number input
        if (this.elements.pageNumEl) {
            this.elements.pageNumEl.value = this.state.pageNum || '';
            this.elements.pageNumEl.placeholder = this.i18n.page;
        }
        
        // Update zoom level display
        this.updateZoomLevel();
        
        // Show/hide loading state
        if (this.state.isLoading) {
            this.showLoading();
        } else {
            this.hideLoading();
        }
        
        // Show/hide error state
        if (this.state.hasError) {
            this.showError(this.state.errorMessage);
        } else {
            this.hideError();
        }
    }
    
    dispatchEvent(eventName, detail = {}) {
        // Create and dispatch a custom event
        const event = new CustomEvent(`pdfviewer:${eventName}`, {
            detail: {
                ...detail,
                viewer: this,
                pageNumber: this.state.pageNum,
                totalPages: this.state.totalPages,
                scale: this.state.scale,
                isFullscreen: this.state.isFullscreen
            },
            bubbles: true,
            cancelable: true
        });
        
        // Dispatch the event on the container element
        if (this.elements.container) {
            this.elements.container.dispatchEvent(event);
        }
        
        // Call the corresponding callback if provided
        const callbackName = `on${eventName.charAt(0).toUpperCase() + eventName.slice(1)}`;
        if (typeof this.config[callbackName] === 'function') {
            try {
                this.config[callbackName]({
                    ...detail,
                    viewer: this,
                    pageNumber: this.state.pageNum,
                    totalPages: this.state.totalPages,
                    scale: this.state.scale,
                    isFullscreen: this.state.isFullscreen
                });
            } catch (error) {
                console.error(`Error in ${callbackName} callback:`, error);
            }
        }
    }
    
    handleKeyDown(event) {
        // Only handle keyboard events when the viewer is focused
        if (!this.state.pdfDoc || !this.elements.container.contains(document.activeElement)) {
            return;
        }
        
        // Don't handle keyboard shortcuts when typing in an input field
        const activeElement = document.activeElement;
        if (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA' || activeElement.isContentEditable) {
            return;
        }
        
        // Handle keyboard shortcuts
        switch (event.key) {
            case 'ArrowLeft':
            case 'ArrowUp':
            case 'PageUp':
                event.preventDefault();
                this.onPrevPage();
                break;
                
            case 'ArrowRight':
            case 'ArrowDown':
            case 'PageDown':
            case ' ':
                event.preventDefault();
                this.onNextPage();
                break;
                
            case 'Home':
                event.preventDefault();
                this.renderPage(1);
                break;
                
            case 'End':
                event.preventDefault();
                this.renderPage(this.state.totalPages);
                break;
                
            case '+':
            case '=':
                event.preventDefault();
                this.zoomIn();
                break;
                
            case '-':
            case '_':
                event.preventDefault();
                this.zoomOut();
                break;
                
            case '0':
                event.preventDefault();
                this.fitWidth();
                break;
                
            case '1':
                event.preventDefault();
                this.setZoom(1.0);
                break;
                
            case 'f':
            case 'F':
                event.preventDefault();
                this.toggleFullscreen();
                break;
                
            case 'Escape':
                if (document.fullscreenElement) {
                    document.exitFullscreen();
                }
                break;
        }
    }
    
    handleResize() {
        // Debounce resize events
        if (this.resizeTimer) {
            clearTimeout(this.resizeTimer);
        }
        
        this.resizeTimer = setTimeout(() => {
            if (this.state.pdfDoc && !this.state.pageRendering) {
                // If we're in fit-to-width or fit-to-page mode, re-apply the fit
                if (this.state.fitToWidthScale !== null) {
                    this.fitWidth();
                } else if (this.state.fitToPageScale !== null) {
                    this.fitPage();
                } else {
                    // Otherwise, just re-render at the current scale
                    this.queueRenderPage(this.state.pageNum);
                }
            }
        }, 250);
    }
    
    handleVisibilityChange() {
        if (document.visibilityState === 'visible' && this.state.pdfDoc) {
            // Re-render the current page when the tab becomes visible again
            this.queueRenderPage(this.state.pageNum);
        }
    }
    
    toggleFullscreen() {
        if (!document.fullscreenElement) {
            // Enter fullscreen
            if (this.elements.container.requestFullscreen) {
                this.elements.container.requestFullscreen();
            } else if (this.elements.container.webkitRequestFullscreen) { /* Safari */
                this.elements.container.webkitRequestFullscreen();
            } else if (this.elements.container.msRequestFullscreen) { /* IE11 */
                this.elements.container.msRequestFullscreen();
            }
            this.state.isFullscreen = true;
        } else {
            // Exit fullscreen
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) { /* Safari */
                document.webkitExitFullscreen();
            } else if (document.msExitFullscreen) { /* IE11 */
                document.msExitFullscreen();
            }
            this.state.isFullscreen = false;
        }
        
        // Dispatch fullscreen change event
        this.dispatchEvent('fullscreenChange', { isFullscreen: this.state.isFullscreen });
    }
    
    handlePageInput(event) {
        if (!this.state.pdfDoc) return;
        
        let pageNum = parseInt(event.target.value, 10);
        
        // Validate input
        if (isNaN(pageNum) || pageNum < 1) {
            pageNum = 1;
        } else if (pageNum > this.state.totalPages) {
            pageNum = this.state.totalPages;
        }
        
        // Update the input field with the validated value
        event.target.value = pageNum;
        
        // Navigate to the specified page
        if (pageNum !== this.state.pageNum) {
            this.renderPage(pageNum);
        }
    }
    
    handlePageInputBlur(event) {
        // Reset the input to the current page number
        if (this.elements.pageNumEl) {
            this.elements.pageNumEl.value = this.state.pageNum;
        }
    }
    
    handleWheel(event) {
        // Handle zoom with Ctrl + Mouse Wheel (or Cmd + Mouse Wheel on Mac)
        if ((event.ctrlKey || event.metaKey) && this.state.pdfDoc) {
            event.preventDefault();
            
            // Determine zoom direction based on wheel delta
            const delta = Math.sign(event.deltaY);
            
            if (delta < 0) {
                this.zoomIn();
            } else {
                this.zoomOut();
            }
        }
    }
    
    cleanup() {
        // Clean up event listeners
        window.removeEventListener('resize', this.handleResize);
        document.removeEventListener('visibilitychange', this.handleVisibilityChange);
        document.removeEventListener('keydown', this.handleKeyDown);
        window.removeEventListener('beforeunload', this.cleanup);
        
        // Remove container event listeners
        if (this.elements.container) {
            this.elements.container.removeEventListener('wheel', this.handleWheel);
        }
        
        // Clean up resize observer
        if (this.state.resizeObserver) {
            if (this.elements.container) {
                this.state.resizeObserver.unobserve(this.elements.container);
            }
            this.state.resizeObserver.disconnect();
            this.state.resizeObserver = null;
        }
        
        // Clear timeouts
        if (this.resizeTimer) {
            clearTimeout(this.resizeTimer);
            this.resizeTimer = null;
        }
        
        if (this.errorTimeout) {
            clearTimeout(this.errorTimeout);
            this.errorTimeout = null;
        }
        
        // Release PDF document resources
        if (this.state.pdfDoc) {
            this.state.pdfDoc.cleanup();
            this.state.pdfDoc = null;
        }
        
        // Clear canvas
        this.clearCanvas();
        
        // Reset state
        this.state = {
            pdfDoc: null,
            pageNum: 1,
            pageRendering: false,
            pageNumPending: null,
            scale: this.config.defaultScale,
            isInitialized: false,
            resizeObserver: null,
            isRTL: this.config.rtl,
            totalPages: 0,
            currentPage: 0,
            currentZoom: 100,
            isFullscreen: false,
            isLoading: false,
            hasError: false,
            errorMessage: '',
            renderOptions: { ...this.state.renderOptions },
            elements: {},
            fitToWidthScale: null,
            fitToPageScale: null
        };
    }
}

// Export for CommonJS and ES modules
if (typeof module !== 'undefined' && typeof module.exports !== 'undefined') {
    module.exports = PDFViewer;
} else if (typeof define === 'function' && define.amd) {
    define([], function() { return PDFViewer; });
} else {
    window.PDFViewer = PDFViewer;
}
