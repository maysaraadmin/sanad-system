document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the document change form
    const fileInput = document.querySelector('input[type="file"][id*="file"]');
    const previewContainer = document.createElement('div');
    previewContainer.id = 'document-preview';
    previewContainer.style.marginTop = '10px';
    
    if (fileInput) {
        // Insert preview container after the file input
        fileInput.parentNode.insertBefore(previewContainer, fileInput.nextSibling);
        
        // Handle file selection
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            // Clear previous preview
            previewContainer.innerHTML = '';
            
            // Check file type
            const fileType = file.type;
            const fileName = file.name.toLowerCase();
            
            if (fileType === 'application/pdf' || fileName.endsWith('.pdf')) {
                // For PDFs, use PDF.js to render a preview
                const url = URL.createObjectURL(file);
                const iframe = document.createElement('iframe');
                iframe.src = url + '#view=FitH';
                iframe.style.width = '100%';
                iframe.style.height = '500px';
                iframe.style.border = '1px solid #ddd';
                previewContainer.appendChild(iframe);
                
                // Add a note about the preview
                const note = document.createElement('p');
                note.textContent = 'Note: This is a preview. The actual file may look different after upload.';
                note.style.fontSize = '0.8em';
                note.style.color = '#666';
                previewContainer.appendChild(note);
                
            } else if (fileType.includes('image/')) {
                // For images, show a thumbnail preview
                const img = document.createElement('img');
                img.src = URL.createObjectURL(file);
                img.style.maxWidth = '100%';
                img.style.maxHeight = '300px';
                img.style.marginTop = '10px';
                img.style.border = '1px solid #ddd';
                previewContainer.appendChild(img);
                
            } else if (fileName.endsWith('.docx') || fileName.endsWith('.doc')) {
                // For Word documents, show a message
                const message = document.createElement('div');
                message.innerHTML = `
                    <div style="padding: 10px; background: #f5f5f5; border: 1px solid #ddd;">
                        <p>Word documents cannot be previewed directly. You can upload the file and a preview will be available after saving.</p>
                    </div>
                `;
                previewContainer.appendChild(message);
                
            } else {
                // For unsupported file types
                const message = document.createElement('div');
                message.innerHTML = `
                    <div style="padding: 10px; background: #fff3cd; border: 1px solid #ffeeba; color: #856404;">
                        <p>Preview not available for this file type. Only PDF and image previews are supported in the admin.</p>
                    </div>
                `;
                previewContainer.appendChild(message);
            }
        });
    }
    
    // Auto-populate title from filename if title is empty
    const titleInput = document.querySelector('input[type="text"][id*="title"]');
    if (titleInput && fileInput) {
        fileInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0 && !titleInput.value) {
                // Remove file extension and replace underscores/dashes with spaces
                const filename = e.target.files[0].name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ');
                titleInput.value = filename;
            }
        });
    }
});
