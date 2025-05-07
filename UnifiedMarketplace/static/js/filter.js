/**
 * Filter management for product search
 * Controls the filter form and "Apply Filters" functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const filterForm = document.getElementById('filter-form');
    const applyFiltersBtn = document.getElementById('apply-filters');
    const resetFiltersBtn = document.getElementById('reset-filters');
    
    // Track original filter values to detect changes
    let originalFilterValues = {};
    
    /**
     * Initialize filter tracking
     * Stores the initial values of all filters to detect changes
     */
    function initializeFilterTracking() {
        if (!filterForm) return;
        
        // Get all input, select elements in the form
        const formElements = filterForm.querySelectorAll('input, select');
        
        // Store original values
        formElements.forEach(element => {
            if (element.type === 'hidden') return;
            if (element.type === 'checkbox' || element.type === 'radio') {
                originalFilterValues[element.name] = element.checked;
            } else {
                originalFilterValues[element.name] = element.value;
            }
            
            // Add change event listener to highlight changes
            element.addEventListener('change', highlightChangedFilters);
            element.addEventListener('input', highlightChangedFilters);
        });
    }
    
    /**
     * Check which filters have been changed and update UI
     */
    function highlightChangedFilters() {
        if (!filterForm) return;
        
        let hasChanges = false;
        const formElements = filterForm.querySelectorAll('input, select');
        
        formElements.forEach(element => {
            if (element.type === 'hidden' || element.type === 'submit') return;
            
            let currentValue;
            if (element.type === 'checkbox' || element.type === 'radio') {
                currentValue = element.checked;
            } else {
                currentValue = element.value;
            }
            
            // Check if value has changed
            if (element.name in originalFilterValues && 
                originalFilterValues[element.name] !== currentValue) {
                
                // Add visual indicator for changed filter
                element.classList.add('filter-changed');
                hasChanges = true;
            } else {
                element.classList.remove('filter-changed');
            }
        });
        
        // Enable/disable apply button based on changes
        if (applyFiltersBtn) {
            applyFiltersBtn.disabled = !hasChanges;
        }
    }
    
    /**
     * Apply filters by submitting the form with an indicator
     */
    function applyFilters() {
        if (!filterForm) return;
        
        // Add a hidden field to indicate filter application
        let applyInput = document.getElementById('apply-filters-input');
        if (!applyInput) {
            applyInput = document.createElement('input');
            applyInput.type = 'hidden';
            applyInput.id = 'apply-filters-input';
            applyInput.name = 'apply_filters';
            filterForm.appendChild(applyInput);
        }
        
        // Set value to trigger API call
        applyInput.value = 'true';
        
        // Show loading indicator
        document.getElementById('loading-indicator').style.display = 'block';
        document.getElementById('results-container').style.opacity = '0.5';
        
        // Submit the form
        filterForm.submit();
    }
    
    /**
     * Reset all filters to default values
     */
    function resetFilters() {
        if (!filterForm) return;
        
        // Reset form
        filterForm.reset();
        
        // Update tracking
        initializeFilterTracking();
        
        // Apply the reset filters
        applyFilters();
    }
    
    // Event listeners
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', resetFilters);
    }
    
    // Initialize the filter tracking
    initializeFilterTracking();
    
    // Pagination without reloading content if cached
    const paginationButtons = document.querySelectorAll('.pagination-btn');
    paginationButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Get page number from button data
            const page = this.dataset.page;
            
            // Find and update page input in the filter form
            const pageInput = document.getElementById('page-input');
            if (pageInput) {
                pageInput.value = page;
            }
            
            // Add a hidden field to indicate we want to check cache
            let cacheCheckInput = document.getElementById('force-reload-input');
            if (!cacheCheckInput) {
                cacheCheckInput = document.createElement('input');
                cacheCheckInput.type = 'hidden';
                cacheCheckInput.id = 'force-reload-input';
                cacheCheckInput.name = 'force_reload';
                filterForm.appendChild(cacheCheckInput);
            }
            
            // Set to false to check cache first
            cacheCheckInput.value = 'false';
            
            // Show loading
            document.getElementById('loading-indicator').style.display = 'block';
            document.getElementById('results-container').style.opacity = '0.5';
            
            // Submit form
            filterForm.submit();
        });
    });
    
    // Show/hide filter on mobile
    const filterToggle = document.getElementById('filter-toggle');
    const filterSidebar = document.getElementById('filter-sidebar');
    
    if (filterToggle && filterSidebar) {
        filterToggle.addEventListener('click', function() {
            if (filterSidebar.classList.contains('show')) {
                filterSidebar.classList.remove('show');
                filterToggle.textContent = 'Show Filters';
            } else {
                filterSidebar.classList.add('show');
                filterToggle.textContent = 'Hide Filters';
            }
        });
    }
});
