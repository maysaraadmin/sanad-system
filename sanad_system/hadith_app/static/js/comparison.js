// Main comparison functionality
(function() {
    'use strict';
    
    document.addEventListener('DOMContentLoaded', function() {
        // Initialize elements
        const compareBtn = document.getElementById('compare-btn');
        const hadithSelect = document.getElementById('hadith-select');
        const comparisonResults = document.getElementById('comparison-results');
        const loadingIndicator = document.getElementById('comparison-loading');
        const narrationColumns = document.getElementById('narration-columns');
        const differencesContainer = document.getElementById('differences-container');

        // Initialize Select2 for better multi-select experience
        $(hadithSelect).select2({
            placeholder: 'اختر الأحاديث للمقارنة',
            allowClear: true,
            dir: 'rtl',
            width: '100%',
            language: {
                noResults: function() {
                    return 'لا توجد نتائج';
                },
                searching: function() {
                    return 'جاري البحث...';
                }
            },
            templateResult: formatHadithOption,
            templateSelection: formatHadithSelection
        });

        // Format how options are displayed in the dropdown
        function formatHadithOption(hadith) {
            if (!hadith.id) { return hadith.text; }
            const $container = $(
                '<div class="d-flex justify-content-between align-items-center">' +
                '   <span class="text-truncate"></span>' +
                '   <span class="badge bg-secondary ms-2"></span>' +
                '</div>'
            );
            
            $container.find('span:first').text(hadith.text);
            $container.find('.badge').text(hadith.element.dataset.source || '');
            
            return $container;
        }
        
        // Format how selected options are displayed
        function formatHadithSelection(hadith) {
            if (!hadith.id) { return hadith.text; }
            return $(`<span>${hadith.text} <small class="text-muted">${hadith.element.dataset.source || ''}</small></span>`);
        }

        // Handle comparison button click
        compareBtn.addEventListener('click', async function() {
            const selectedHadiths = Array.from(hadithSelect.selectedOptions).map(option => option.value);
            
            if (selectedHadiths.length < 2) {
                showAlert('الرجاء اختيار حديثين على الأقل للمقارنة', 'warning');
                return;
            }

            try {
                // Show loading indicator
                showLoading(true);

                // Call the API to get comparison data
                const response = await fetch(`/api/hadith/compare/${selectedHadiths.join(',')}/`);
                const data = await response.json();
                
                if (data.status === 'success') {
                    // Render comparison results
                    renderComparison(data.results);
                    
                    // Show differences
                    highlightDifferences(data.results);
                    
                    // Show the results section
                    comparisonResults.style.display = 'block';
                } else {
                    throw new Error(data.message || 'حدث خطأ غير معروف');
                }
                
            } catch (error) {
                console.error('Error comparing hadiths:', error);
                showAlert(`حدث خطأ: ${error.message}`, 'danger');
            } finally {
                showLoading(false);
            }
        });

        // Show or hide loading indicator
        function showLoading(show) {
            if (loadingIndicator) loadingIndicator.style.display = show ? 'block' : 'none';
            if (comparisonResults) comparisonResults.style.display = show ? 'none' : 'block';
        }

        // Show alert message
        function showAlert(message, type = 'info') {
            if (!comparisonResults) return;
            
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
            alertDiv.role = 'alert';
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            
            // Remove any existing alerts
            const existingAlert = comparisonResults.querySelector('.alert');
            if (existingAlert) {
                existingAlert.remove();
            }
            
            comparisonResults.prepend(alertDiv);
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
                    const bsAlert = new bootstrap.Alert(alertDiv);
                    bsAlert.close();
                } else {
                    alertDiv.remove();
                }
            }, 5000);
        }

        // Render comparison columns
        function renderComparison(hadiths) {
            if (!narrationColumns) return;
            
            narrationColumns.innerHTML = '';
            
            hadiths.forEach(hadith => {
                const col = document.createElement('div');
                col.className = 'col-md-6 col-lg-4 mb-4';
                
                // Format narrators list
                const narratorsList = hadith.narrators && hadith.narrators.length > 0
                    ? hadith.narrators.map(n => 
                        `<li class="mb-1">
                            ${n.name || 'غير معروف'} 
                            <span class="badge ${getReliabilityBadgeClass(n.reliability)}">${n.reliability || 'غير محدد'}</span>
                        </li>`
                      ).join('')
                    : '<li>غير متوفر</li>';
                
                col.innerHTML = `
                    <div class="card h-100">
                        <div class="card-header">
                            <h6 class="card-title">${hadith.book || 'غير محدد'}</h6>
                            <small class="text-muted">${hadith.source || 'مصدر غير محدد'}</small>
                        </div>
                        <div class="card-body">
                            <h6 class="card-subtitle mb-2 text-muted">النص:</h6>
                            <p class="card-text narration-text">${hadith.text || 'لا يوجد نص'}</p>
                            
                            <h6 class="card-subtitle mb-2 mt-3 text-muted">سند الحديث:</h6>
                            <p class="card-text text-muted">${hadith.sanad || 'غير متوفر'}</p>
                            
                            <h6 class="card-subtitle mb-2 mt-3 text-muted">الرواة:</h6>
                            <ul class="list-unstyled">
                                ${narratorsList}
                            </ul>
                            
                            ${hadith.grade ? `
                                <div class="mt-3">
                                    <h6 class="card-subtitle mb-2 text-muted">درجة الحديث:</h6>
                                    <span class="badge ${getGradeBadgeClass(hadith.grade)}">
                                        ${hadith.grade}
                                    </span>
                                </div>
                            ` : ''}
                        </div>
                        <div class="card-footer bg-transparent">
                            <small class="text-muted">
                                <i class="far fa-calendar-alt me-1"></i>
                                ${hadith.created_at || 'تاريخ غير معروف'}
                            </small>
                        </div>
                    </div>
                `;
                
                narrationColumns.appendChild(col);
            });
        }

        // Highlight differences between narrations
        function highlightDifferences(hadiths) {
            if (!differencesContainer) return;
            
            if (!hadiths || hadiths.length < 2) {
                differencesContainer.innerHTML = '<p class="text-muted">يجب اختيار أكثر من رواية للمقارنة.</p>';
                return;
            }
            
            // For now, we'll do a simple text comparison
            // In a production environment, you might want to use a more sophisticated diffing algorithm
            const baseText = hadiths[0].text || '';
            const baseWords = baseText.split(/\s+/);
            
            let diffHTML = '<div class="table-responsive"><table class="table table-bordered">';
            diffHTML += '<thead><tr><th>الرقم</th><th>الاختلاف</th><th>الرواية</th></tr></thead><tbody>';
            
            // Compare each hadith with the first one
            for (let i = 1; i < hadiths.length; i++) {
                const currentText = hadiths[i].text || '';
                const currentWords = currentText.split(/\s+/);
                
                // Find differences
                const maxLength = Math.max(baseWords.length, currentWords.length);
                const differences = [];
                
                for (let j = 0; j < maxLength; j++) {
                    const baseWord = baseWords[j] || '';
                    const currentWord = currentWords[j] || '';
                    
                    if (baseWord !== currentWord) {
                        differences.push({
                            position: j,
                            base: baseWord,
                            current: currentWord
                        });
                    }
                }
                
                // Add to the differences table
                if (differences.length > 0) {
                    diffHTML += `<tr><td rowspan="${differences.length}" class="align-middle">${i + 1}</td>`;
                    
                    differences.forEach((diff, idx) => {
                        if (idx > 0) diffHTML += '<tr>';
                        
                        diffHTML += `
                            <td>كلمة ${diff.position + 1}</td>
                            <td>
                                <span class="text-danger"><del>${diff.base || '---'}</del></span>
                                <i class="fas fa-arrow-left mx-2 text-muted"></i>
                                <span class="text-success">${diff.current || '---'}</span>
                            </td>
                        `;
                        
                        if (idx === 0) {
                            diffHTML += `<td rowspan="${differences.length}" class="align-middle">
                                <div class="text-truncate" style="max-width: 200px;" title="${currentText}">
                                    ${currentText.substring(0, 100)}${currentText.length > 100 ? '...' : ''}
                                </div>
                            </td>`;
                        }
                        
                        diffHTML += '</tr>';
                    });
                }
            }
            
            diffHTML += '</tbody></table></div>';
            
            if (diffHTML.includes('text-danger')) {
                differencesContainer.innerHTML = `
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        تم العثور على اختلافات بين الروايات المحددة.
                    </div>
                    ${diffHTML}
                `;
            } else {
                differencesContainer.innerHTML = `
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle me-2"></i>
                        لا توجد اختلافات نصية بين الروايات المحددة.
                    </div>
                `;
            }
        }
        
        // Helper function to get badge class based on hadith grade
        function getGradeBadgeClass(grade) {
            if (!grade) return 'bg-secondary';
            
            const lowerGrade = String(grade).toLowerCase();
            
            if (lowerGrade.includes('صحيح')) {
                return 'bg-success';
            } else if (lowerGrade.includes('حسن')) {
                return 'bg-primary';
            } else if (lowerGrade.includes('ضعيف')) {
                return 'bg-warning';
            } else if (lowerGrade.includes('موضوع') || lowerGrade.includes('باطل')) {
                return 'bg-danger';
            } else if (lowerGrade.includes('جيد')) {
                return 'bg-info';
            } else {
                return 'bg-secondary';
            }
        }
        
        // Helper function to get badge class based on narrator reliability
        function getReliabilityBadgeClass(reliability) {
            if (!reliability) return 'bg-secondary';
            
            const lowerReliability = String(reliability).toLowerCase();
            
            if (lowerReliability.includes('ثقة') || lowerReliability.includes('صدوق')) {
                return 'bg-success';
            } else if (lowerReliability.includes('ضعيف') || lowerReliability.includes('متروك')) {
                return 'bg-danger';
            } else if (lowerReliability.includes('مقبول') || lowerReliability.includes('مستور')) {
                return 'bg-warning';
            } else if (lowerReliability.includes('كذاب') || lowerReliability.includes('وضاع')) {
                return 'bg-dark';
            } else {
                return 'bg-secondary';
            }
        }
    });
})();
