import os
import logging
import threading
import time
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timedelta
import json

# Import Supabase client
from supabase_client import (
    supabase_client, get_user_by_email, get_user_by_username, 
    create_user, get_search_history, save_search,
    get_cached_search, cache_search_results, clear_expired_cache
)

# Initialize logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Set up database base class
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Database operation error handler
def db_operation(func):
    """Decorator to handle database operation errors gracefully"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Database operation error in {func.__name__}: {e}")
            try:
                db.session.rollback()
            except:
                pass
            return None
    return wrapper

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Database configuration - Using Supabase PostgreSQL
# If environment variables are set individually (common for Supabase)
if all(os.environ.get(var) for var in ["PGUSER", "PGPASSWORD", "PGHOST", "PGPORT", "PGDATABASE"]):
    # Construct the database URL from individual components
    pguser = os.environ.get("PGUSER")
    pgpassword = os.environ.get("PGPASSWORD")
    pghost = os.environ.get("PGHOST")
    pgport = os.environ.get("PGPORT")
    pgdatabase = os.environ.get("PGDATABASE")
    
    # Format: postgresql://username:password@host:port/dbname
    database_url = f"postgresql://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}"
else:
    # Fall back to DATABASE_URL if the individual vars aren't set
    database_url = os.environ.get("DATABASE_URL")
    
# If URL starts with postgres://, replace with postgresql:// for SQLAlchemy 1.4+
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Configure SQLAlchemy with SSL options for Supabase
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_size": 5,  # Reduce pool size for better stability
    "max_overflow": 10,
    "connect_args": {
        "sslmode": "require",  # Force SSL connection
        "connect_timeout": 10,  # Shorter connection timeout
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database with the app
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Import after initializing db to avoid circular imports
from models import User, SearchHistory
from forms import RegistrationForm, LoginForm
from api_manager import get_products
from cache_manager import get_cached_results, cache_results

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create tables when app starts - with error handling
try:
    with app.app_context():
        logging.info("Attempting to create database tables...")
        db.create_all()
        logging.info("Database tables created successfully")
except Exception as e:
    logging.error(f"Error creating database tables: {e}")
    logging.warning("Application will continue, but database functionality may be limited")
    
# Background task to clear expired cache entries
def clear_cache_periodically():
    """Run a background thread that clears expired cache every hour"""
    from cache_manager import clear_old_cache
    
    while True:
        time.sleep(3600)  # Run every hour (3600 seconds)
        with app.app_context():
            try:
                logging.info("Running scheduled cache cleanup")
                clear_old_cache()
            except Exception as e:
                logging.error(f"Error in scheduled cache cleanup: {e}")

# Start the background task if running in production
if not app.debug or os.environ.get("FLASK_ENV") == "production":
    cache_cleaner = threading.Thread(target=clear_cache_periodically)
    cache_cleaner.daemon = True  # Thread will exit when the main process exits
    cache_cleaner.start()
    logging.info("Started background cache cleaning thread")

# Routes
@app.route("/", methods=["GET", "POST"])
def index():
    countries = {
        "us": "United States", "uk": "United Kingdom", "ar": "Argentina", "in": "India", 
        "ai": "Anguilla", "au": "Australia", "gb": "Great Britain", "bm": "Bermuda", 
        "br": "Brazil", "io": "British Indian Ocean Territory", "ca": "Canada", 
        "ky": "Cayman Islands", "cl": "Chile", "cx": "Christmas Island", 
        "cc": "Cocos Islands", "co": "Colombia", "fk": "Falkland Islands", 
        "hk": "Hong Kong", "hm": "Heard & McDonald Islands", "il": "Israel", 
        "jp": "Japan", "id": "Indonesia", "kr": "South Korea", "my": "Malaysia", 
        "ms": "Montserrat", "mx": "Mexico", "nz": "New Zealand", "nf": "Norfolk Island", 
        "ph": "Philippines", "ru": "Russia", "sa": "Saudi Arabia", "sg": "Singapore", 
        "gs": "South Georgia", "za": "South Africa", "ch": "Switzerland", 
        "tk": "Tokelau", "tw": "Taiwan", "th": "Thailand", "tc": "Turks & Caicos Islands", 
        "tr": "Turkey", "gb": "United Kingdom", "ae": "United Arab Emirates", 
        "ua": "Ukraine", "vg": "British Virgin Islands", "vn": "Vietnam"
    }
    
    # Default parameters
    query = ""
    page = 1
    sort_by = "BEST_MATCH"
    product_condition = "NEW"
    min_rating = "ANY"
    min_price = "0"
    max_price = "1000000"
    stores = "Amazon"
    country = "us"
    language = "en"
    products = []
    total_pages = 100
    
    # Cache key will be used for both server and client-side caching
    cache_key = None
    
    if request.method == "POST":
        # Get form parameters
        query = request.form.get("query", "")
        page = int(request.form.get("page", 1))
        sort_by = request.form.get("sort_by", "BEST_MATCH")
        product_condition = request.form.get("product_condition", "NEW")
        min_rating = request.form.get("min_rating", "ANY")
        min_price = request.form.get("min_price", "0")
        max_price = request.form.get("max_price", "1000000")
        stores = request.form.get("stores", "Amazon")
        country = request.form.get("country", "us")
        language = request.form.get("language", "en")
        
        # Generate cache key
        cache_key = f"{query}_{page}_{sort_by}_{product_condition}_{min_rating}_{min_price}_{max_price}_{stores}_{country}_{language}"
        
        # Only if "apply_filters" is true or cache doesn't exist, call the API
        if request.form.get("apply_filters") == "true" or request.form.get("force_reload") == "true":
            logging.info(f"Applying filters or forced reload for: {cache_key}")
            products = get_products(
                query=query,
                page=page,
                sort_by=sort_by,
                product_condition=product_condition,
                min_rating=min_rating,
                min_price=min_price,
                max_price=max_price,
                stores=stores,
                country=country,
                language=language
            )
            
            # Cache the results
            if products:
                cache_results(cache_key, products)
                
                # Save search to history if user is logged in
                if current_user.is_authenticated:
                    # Create parameters JSON string
                    parameters_json = json.dumps({
                        'sort_by': sort_by,
                        'product_condition': product_condition,
                        'min_rating': min_rating,
                        'min_price': min_price,
                        'max_price': max_price,
                        'stores': stores,
                        'country': country,
                        'language': language
                    })
                    
                    # Try to save to Supabase first if available
                    if supabase_client:
                        saved = save_search(current_user.id, query, parameters_json)
                        
                    # Always save to SQLAlchemy for Flask app functionality
                    try:
                        new_search = SearchHistory(
                            user_id=current_user.id,
                            query=query,
                            parameters=parameters_json,
                            created_at=datetime.now()
                        )
                        db.session.add(new_search)
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        logging.error(f"Error saving search history: {e}")
        else:
            # Try to get cached results
            logging.info(f"Looking for cached results for: {cache_key}")
            cached_data = get_cached_results(cache_key)
            if cached_data:
                products = cached_data
                logging.info(f"Found cached results for: {cache_key}")
            else:
                # If cache miss, call the API
                logging.info(f"Cache miss for: {cache_key}, calling API")
                products = get_products(
                    query=query,
                    page=page,
                    sort_by=sort_by,
                    product_condition=product_condition,
                    min_rating=min_rating,
                    min_price=min_price,
                    max_price=max_price,
                    stores=stores,
                    country=country,
                    language=language
                )
                
                # Cache the results
                if products:
                    cache_results(cache_key, products)
    
    return render_template(
        "index.html",
        products=products,
        query=query,
        page=page,
        total_pages=total_pages,
        sort_by=sort_by,
        product_condition=product_condition,
        min_rating=min_rating,
        min_price=min_price,
        max_price=max_price,
        stores=stores,
        country=country,
        language=language,
        countries=countries,
        cache_key=cache_key
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        
        # Check if Supabase client is available
        if supabase_client:
            # Check if username or email already exists in Supabase
            existing_user = get_user_by_username(username)
            existing_email = get_user_by_email(email)
            
            if existing_user:
                flash('Username already exists. Please choose another one.', 'danger')
            elif existing_email:
                flash('Email already registered. Please use another one.', 'danger')
            else:
                # Create new user in Supabase
                hashed_password = generate_password_hash(form.password.data)
                supabase_user = create_user(username, email, hashed_password)
                
                if supabase_user:
                    # Also create user in SQLAlchemy for Flask-Login with error handling
                    try:
                        user = User(
                            username=username,
                            email=email,
                            password_hash=hashed_password
                        )
                        db.session.add(user)
                        db.session.commit()
                        
                        flash('Your account has been created! You can now log in.', 'success')
                        return redirect(url_for('login'))
                    except Exception as e:
                        db.session.rollback()
                        logging.error(f"Error creating user in database: {e}")
                        flash('There was an error creating your account. Please try again.', 'danger')
                        return redirect(url_for('register'))
                else:
                    flash('Error creating user in Supabase.', 'danger')
        else:
            # Fall back to SQLAlchemy if Supabase client is not available
            # Check if username or email already exists using Supabase-compatible session queries
            existing_user = db.session.query(User).filter(User.username == username).first()
            existing_email = db.session.query(User).filter(User.email == email).first()
            
            if existing_user:
                flash('Username already exists. Please choose another one.', 'danger')
            elif existing_email:
                flash('Email already registered. Please use another one.', 'danger')
            else:
                # Create new user with error handling
                try:
                    hashed_password = generate_password_hash(form.password.data)
                    user = User(
                        username=username,
                        email=email,
                        password_hash=hashed_password
                    )
                    db.session.add(user)
                    db.session.commit()
                    
                    flash('Your account has been created! You can now log in.', 'success')
                    return redirect(url_for('login'))
                except Exception as e:
                    db.session.rollback()
                    logging.error(f"Error creating user in database: {e}")
                    flash('There was an error creating your account. Please try again.', 'danger')
                    return redirect(url_for('register'))
            
    return render_template('register.html', form=form, title='Register')

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        # Check if Supabase client is available
        if supabase_client:
            # Get user from Supabase
            supabase_user = get_user_by_email(email)
            
            if supabase_user and check_password_hash(supabase_user['password_hash'], password):
                # Get the corresponding SQLAlchemy user for Flask-Login
                user = db.session.query(User).filter(User.email == email).first()
                
                if not user:
                    # If user exists in Supabase but not in SQLAlchemy, create it with error handling
                    try:
                        user = User(
                            username=supabase_user['username'],
                            email=supabase_user['email'],
                            password_hash=supabase_user['password_hash']
                        )
                        db.session.add(user)
                        db.session.commit()
                        logging.info(f"Created SQLAlchemy user from Supabase data: {email}")
                    except Exception as e:
                        db.session.rollback()
                        logging.error(f"Error creating SQLAlchemy user from Supabase data: {e}")
                        flash('Error logging in. Please try again later.', 'danger')
                        return redirect(url_for('login'))
                
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                # Fall back to SQLAlchemy check
                user = db.session.query(User).filter(User.email == email).first()
                if user and check_password_hash(user.password_hash, password):
                    login_user(user, remember=form.remember.data)
                    next_page = request.args.get('next')
                    flash('Login successful!', 'success')
                    return redirect(next_page) if next_page else redirect(url_for('index'))
                else:
                    flash('Login failed. Please check your email and password.', 'danger')
        else:
            # Fall back to SQLAlchemy only if Supabase client is not available
            user = db.session.query(User).filter(User.email == email).first()
            
            if user and check_password_hash(user.password_hash, password):
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                flash('Login failed. Please check your email and password.', 'danger')
            
    return render_template('login.html', form=form, title='Login')

@app.route("/logout")
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route("/account")
@login_required
def account():
    # Get user's search history
    if supabase_client:
        # Try to get search history from Supabase
        search_history_list = get_search_history(current_user.id)
        
        if search_history_list:
            # Convert to SearchHistory objects for template compatibility
            search_history = []
            for item in search_history_list:
                history_obj = SearchHistory()
                history_obj.id = item.get('id')
                history_obj.user_id = item.get('user_id')
                history_obj.query = item.get('query')
                history_obj.parameters = item.get('parameters')
                history_obj.created_at = datetime.fromisoformat(item.get('created_at')) if item.get('created_at') else datetime.now()
                search_history.append(history_obj)
        else:
            # Fall back to SQLAlchemy
            search_history = db.session.query(SearchHistory).filter(
                SearchHistory.user_id == current_user.id
            ).order_by(SearchHistory.created_at.desc()).limit(10).all()
    else:
        # Use SQLAlchemy directly if Supabase is not available
        search_history = db.session.query(SearchHistory).filter(
            SearchHistory.user_id == current_user.id
        ).order_by(SearchHistory.created_at.desc()).limit(10).all()
        
    return render_template('account.html', title='Account', search_history=search_history)

# Footer pages
@app.route("/about")
def about():
    return render_template('about.html', title='About Us')

@app.route("/contact")
def contact():
    return render_template('contact.html', title='Contact Us')

@app.route("/privacy")
def privacy():
    return render_template('privacy.html', title='Privacy Policy')

@app.route("/terms")
def terms():
    return render_template('terms.html', title='Terms of Service')

@app.route("/faq")
def faq():
    return render_template('faq.html', title='FAQ')

@app.route("/admin/clear-cache", methods=["GET"])
@login_required
def clear_cache():
    """Admin endpoint to manually clear expired cache"""
    from cache_manager import clear_old_cache
    
    if not current_user.is_authenticated:
        flash('You must be logged in to perform this action.', 'danger')
        return redirect(url_for('login'))
        
    # Run the cache cleanup
    try:
        result = clear_old_cache()
        if result:
            flash('Cache cleared successfully!', 'success')
        else:
            flash('Failed to clear cache.', 'danger')
    except Exception as e:
        flash(f'Error clearing cache: {str(e)}', 'danger')
        
    return redirect(url_for('account'))

# Run the app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
