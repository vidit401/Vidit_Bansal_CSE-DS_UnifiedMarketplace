/**
 * Client-side cache manager for search results
 * Helps reduce API calls by storing search results in localStorage
 */

// Cache duration in minutes
const CACHE_DURATION = 60;

/**
 * Save search results to localStorage
 * @param {string} cacheKey - Unique identifier for the search
 * @param {Array} products - Product search results
 */
function saveToCache(cacheKey, products) {
    if (!cacheKey || !products) return;
    
    try {
        // Create cache object with expiration time
        const cacheObject = {
            timestamp: new Date().getTime(),
            expiry: new Date().getTime() + (CACHE_DURATION * 60 * 1000),
            products: products
        };
        
        // Save to localStorage
        localStorage.setItem(`search_${cacheKey}`, JSON.stringify(cacheObject));
        console.log(`Saved results to client cache with key: search_${cacheKey}`);
    } catch (error) {
        console.error('Error saving to cache:', error);
    }
}

/**
 * Retrieve search results from localStorage
 * @param {string} cacheKey - Unique identifier for the search
 * @returns {Array|null} - Cached products or null if not found/expired
 */
function getFromCache(cacheKey) {
    if (!cacheKey) return null;
    
    try {
        // Get cache from localStorage
        const cacheData = localStorage.getItem(`search_${cacheKey}`);
        
        if (!cacheData) return null;
        
        const cache = JSON.parse(cacheData);
        const currentTime = new Date().getTime();
        
        // Check if cache is expired
        if (currentTime > cache.expiry) {
            // Remove expired cache
            localStorage.removeItem(`search_${cacheKey}`);
            console.log(`Cache expired for key: search_${cacheKey}`);
            return null;
        }
        
        console.log(`Retrieved results from client cache for key: search_${cacheKey}`);
        return cache.products;
    } catch (error) {
        console.error('Error retrieving from cache:', error);
        return null;
    }
}

/**
 * Clear all expired cache entries from localStorage
 */
function cleanExpiredCache() {
    try {
        const currentTime = new Date().getTime();
        let count = 0;
        
        // Check all localStorage items
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            
            // Only process our search cache items
            if (key && key.startsWith('search_')) {
                try {
                    const cacheData = localStorage.getItem(key);
                    const cache = JSON.parse(cacheData);
                    
                    // Remove if expired
                    if (currentTime > cache.expiry) {
                        localStorage.removeItem(key);
                        count++;
                    }
                } catch (e) {
                    // If JSON parsing fails, remove the item
                    localStorage.removeItem(key);
                    count++;
                }
            }
        }
        
        if (count > 0) {
            console.log(`Cleaned ${count} expired cache entries`);
        }
    } catch (error) {
        console.error('Error cleaning cache:', error);
    }
}

// Clean expired cache on page load
document.addEventListener('DOMContentLoaded', cleanExpiredCache);

// Example usage in search functionality
document.addEventListener('DOMContentLoaded', function() {
    // Check if there's a cache key in the page
    const cacheKeyElement = document.getElementById('cache-key');
    if (cacheKeyElement) {
        const cacheKey = cacheKeyElement.value;
        
        // If search results are present on the page, save to cache
        const productsContainer = document.querySelector('.product-container');
        if (cacheKey && productsContainer && productsContainer.children.length > 0) {
            // We'll save the entire HTML content as the client-side cache
            // This is a simple approach that works for this specific case
            saveToCache(cacheKey, productsContainer.innerHTML);
        }
    }
});
