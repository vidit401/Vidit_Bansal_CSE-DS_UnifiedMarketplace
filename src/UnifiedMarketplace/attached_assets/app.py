from flask import Flask, render_template, request
import requests
import logging

# Initialize Flask app
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# API details
API_URL = "https://real-time-product-search.p.rapidapi.com/search"
HEADERS = {
    "x-rapidapi-key": "6b1b80ff11msh2af18ab2e1eec8cp1e18bfjsn4b16b26af93e",
    "x-rapidapi-host": "real-time-product-search.p.rapidapi.com"
}

@app.route("/", methods=["GET", "POST"])
def index():
    products = []
    query = ""
    page = 1
    sort_by = "BEST_MATCH"  # Initialize sort_by with a default value

    product_condition = "NEW"  # Initialize product_condition with a default value
    min_rating = "ANY"  # Initialize min_rating with a default value
    min_price = "0"  # Initialize min_price with a default value
    max_price = "10000000000000000000000000000000000000000000000000000000000000000000000000000000000000"  # Initialize max_price with a default value
    stores = "Amazon"  # Initialize stores with a default value

    if request.method == "POST":
        query = request.form.get("query")
        page = request.form.get("page", 1)
        product_condition = request.form.get("product_condition", product_condition)
        sort_by = request.form.get("sort_by", sort_by)  # Ensure sort_by is updated correctly
        min_rating = request.form.get("min_rating", "ANY")
        min_price = request.form.get("min_price", "0")
        max_price = request.form.get("max_price", "10000000000000000000000000000000000000000000000000000000000000000000000000000000000000")
        product_condition = request.form.get("product_condition", "NEW")
        stores = request.form.get("stores", "Amazon")
        
        logging.info("Query: %s, Page: %s, Sort By: %s, Product Condition: %s, Min Rating: %s, Min Price: %s, Max Price: %s, Stores: %s", query, page, sort_by, product_condition, min_rating, min_price, max_price, stores)

        logging.info("Fetching products for query: %s, Page: %s", query, page)

        # API query parameters
        params = {
            "q": query,
            "country": "in",
            "language": "en",
            "page": page,
            "limit": "50",
            "sort_by": sort_by,
            "product_condition": product_condition,
            "min_rating": "ANY",
            "min_price": "0",
            "max_price": "10000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
            "stores": stores
        }

        # API request
        response = requests.get(API_URL, headers=HEADERS, params=params)
        
        if response.status_code == 200:
            response_data = response.json()
            products = response_data.get("data", {}).get("products", [])
            logging.debug("API Response: %s", response.json())  # Log API response
        else:
            logging.error("API request failed! Status code: %s", response.status_code)

    return render_template("index.html", products=products, query=query, page=int(page), total_pages=100, sort_by=sort_by, product_condition=product_condition, min_rating=min_rating, min_price=min_price, max_price=max_price, stores=stores)

if __name__ == "__main__":
    logging.info("Starting Flask app...")
    app.run(debug=True)