import requests
import logging
import os
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# API details
API_URL = "https://real-time-product-search.p.rapidapi.com/search"
HEADERS = {
    "x-rapidapi-key": os.environ.get("RAPIDAPI_KEY", "6b1b80ff11msh2af18ab2e1eec8cp1e18bfjsn4b16b26af93e"),
    "x-rapidapi-host": "real-time-product-search.p.rapidapi.com"
}

def get_products(query, page=1, sort_by="BEST_MATCH", product_condition="NEW", 
                min_rating="ANY", min_price="0", max_price="1000000", 
                stores="Amazon", country="us", language="en"):
    """
    Fetch products from the RapidAPI product search endpoint
    
    Args:
        query (str): The search query
        page (int): The page number to fetch
        sort_by (str): How to sort the results
        product_condition (str): Filter by product condition (NEW, USED, REFURBISHED, ANY)
        min_rating (str): Minimum product rating
        min_price (str): Minimum price
        max_price (str): Maximum price
        stores (str): Comma-separated list of stores to search
        country (str): Country code
        language (str): Language code
        
    Returns:
        list: List of product dictionaries
    """
    if not query:
        logging.warning("Empty query provided")
        return []
    
    try:
        # Log API request details
        logging.info(f"Making API request for query: {query}, page: {page}, sort_by: {sort_by}, " +
                     f"condition: {product_condition}, stores: {stores}, country: {country}")
        
        # API query parameters
        params = {
            "q": query,
            "country": country,
            "language": language,
            "page": page,
            "limit": "50",
            "sort_by": sort_by,
            "product_condition": product_condition,
            "min_rating": min_rating,
            "min_price": min_price,
            "max_price": max_price,
            "stores": stores
        }

        # API request
        response = requests.get(API_URL, headers=HEADERS, params=params)
        
        # Handle response
        if response.status_code == 200:
            response_data = response.json()
            products = response_data.get("data", {}).get("products", [])
            
            # Log the number of products fetched
            logging.info(f"Successfully fetched {len(products)} products")
            
            return products
        else:
            logging.error(f"API request failed! Status code: {response.status_code}")
            logging.error(f"Error details: {response.text}")
            return []
            
    except Exception as e:
        logging.error(f"Error fetching products: {str(e)}")
        return []
