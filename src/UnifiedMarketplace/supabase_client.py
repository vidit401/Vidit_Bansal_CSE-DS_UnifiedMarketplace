import os
import logging
from supabase import create_client

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Checking if we have the necessary Supabase credentials
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Custom table names for Supabase
USERS_TABLE = "unified_marketplace_users"
SEARCH_HISTORY_TABLE = "unified_marketplace_searches"
CACHE_TABLE = "unified_marketplace_cache"

# If we have environment variables, initializing the client
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logging.info("Supabase client initialized successfully")
        
        # Ensuring tables exist by checking for their presence
        def check_table_exists(table_name):
            try:
                # Just fetching one row to see if table exists
                response = supabase_client.table(table_name).select("*").limit(1).execute()
                return True
            except Exception as e:
                if "404" in str(e) or "does not exist" in str(e).lower():
                    logging.warning(f"Checking if table {table_name} exists in Supabase")
                    return False
                else:
                    # Some other error
                    logging.error(f"Error checking table {table_name}: {e}")
                    return False
                    
        # Supabase table creation requires using the dashboard
# We can't create tables programmatically through the REST API without setting up custom functions
        def create_table_if_not_exists(table_name, schema):
            """Checking if a table exists in Supabase"""
            if check_table_exists(table_name):
                logging.info(f"Table {table_name} already exists in Supabase")
                return True
                
            # We can't create tables programmatically without special setup
            logging.warning(f"Table {table_name} doesn't exist in Supabase.")
            logging.warning(f"Please create it manually in the Supabase dashboard.")
            return False
            
        # Defining our table schemas - these should match our SQLAlchemy models
        users_schema = {
            "id": "serial primary key",
            "username": "varchar(64) unique not null", 
            "email": "varchar(120) unique not null",
            "password_hash": "varchar(256) not null",
            "created_at": "timestamp default now()"
        }
        
        search_history_schema = {
            "id": "serial primary key",
            "user_id": "int not null",
            "query": "varchar(255) not null",
            "parameters": "text",
            "created_at": "timestamp default now()"
        }
        
        cache_schema = {
            "id": "serial primary key",
            "cache_key": "varchar(512) unique not null",
            "results": "text not null",
            "created_at": "timestamp default now()",
            "expires_at": "timestamp not null"
        }
        
        # Checking if required tables exist
        tables_exist = (
            check_table_exists(USERS_TABLE) and
            check_table_exists(SEARCH_HISTORY_TABLE) and
            check_table_exists(CACHE_TABLE)
        )
        
        if not tables_exist:
            logging.warning("One or more required Supabase tables don't exist.")
            logging.warning("To use Supabase for data storage, please create the following tables in the Supabase dashboard:")
            logging.warning(f"- {USERS_TABLE}")
            logging.warning(f"- {SEARCH_HISTORY_TABLE}")
            logging.warning(f"- {CACHE_TABLE}")
            logging.warning("Using PostgreSQL via SQLAlchemy as fallback for now.")
            
    except Exception as e:
        logging.error(f"Error initializing Supabase client: {e}")
        supabase_client = None
else:
    logging.warning("Supabase URL and/or key not found in environment variables. Using SQLAlchemy with PostgreSQL.")
    supabase_client = None

def get_user_by_email(email):
    """
    Fetching a user from Supabase by email.
    
    Args:
        email (str): User email to search for
    
    Returns:
        dict: User data if found, None otherwise
    """
    if not supabase_client:
        logging.warning("Supabase client not initialized. Cannot fetch user.")
        return None
        
    try:
        # Trying to fetch user, handling case where table doesn't exist
        try:
            response = supabase_client.table(USERS_TABLE).select("*").eq("email", email).execute()
            data = response.data
            
            if data and len(data) > 0:
                return data[0]
            return None
        except Exception as inner_e:
            # If this is a 404 error (table doesn't exist), logging and returning None
            if "404" in str(inner_e) or "does not exist" in str(inner_e).lower():
                logging.warning(f"Table {USERS_TABLE} doesn't exist. Falling back to SQLAlchemy.")
                return None
            # Otherwise re-raising the exception
            raise inner_e
            
    except Exception as e:
        logging.error(f"Error fetching user by email: {e}")
        return None

def get_user_by_username(username):
    """
    Fetching a user from Supabase by username.
    
    Args:
        username (str): Username to search for
    
    Returns:
        dict: User data if found, None otherwise
    """
    if not supabase_client:
        logging.warning("Supabase client not initialized. Cannot fetch user.")
        return None
        
    try:
        # Trying to fetch user, handling case where table doesn't exist
        try:
            response = supabase_client.table(USERS_TABLE).select("*").eq("username", username).execute()
            data = response.data
            
            if data and len(data) > 0:
                return data[0]
            return None
        except Exception as inner_e:
            # If this is a 404 error (table doesn't exist), logging and returning None
            if "404" in str(inner_e) or "does not exist" in str(inner_e).lower():
                logging.warning(f"Table {USERS_TABLE} doesn't exist. Falling back to SQLAlchemy.")
                return None
            # Otherwise re-raising the exception
            raise inner_e
            
    except Exception as e:
        logging.error(f"Error fetching user by username: {e}")
        return None

# Adding a function to manually create the Supabase tables when needed
# We cannot create tables directly in Supabase through the API without custom functions
# So we'll instead modifying our approach to insert rows directly, which will work if the tables
# have already been created in the Supabase dashboard

def create_supabase_tables():
    """
    Attempting to create tables in Supabase by direct inserts, 
    but this will only work if tables are already created in the Supabase dashboard
    
    Returns:
        bool: Always returns False as we rely on SQLAlchemy for now
    """
    logging.info("Creating tables in Supabase requires manually setting them up in the dashboard first.")
    logging.info("Falling back to SQLAlchemy for now.")
    return False

def create_user(username, email, password_hash):
    """
    Creating a new user in Supabase.
    
    Args:
        username (str): Username for new user
        email (str): Email for new user
        password_hash (str): Hashed password
        
    Returns:
        dict: Created user data, None if failed
    """
    if not supabase_client:
        logging.warning("Supabase client not initialized. Cannot create user.")
        return None
        
    try:
        user_data = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
        }
        
        # Trying to insert the user, and handling case where table doesn't exist
        try:
            response = supabase_client.table(USERS_TABLE).insert(user_data).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as inner_e:
            # If this is a 404 error (table doesn't exist), trying to create the table first
            if "404" in str(inner_e) or "does not exist" in str(inner_e).lower():
                logging.warning(f"Table {USERS_TABLE} doesn't exist. Attempting to create it...")
                
                # Trying to create all tables
                tables_created = create_supabase_tables()
                
                if tables_created:
                    # Trying to insert again
                    try:
                        response = supabase_client.table(USERS_TABLE).insert(user_data).execute()
                        
                        if response.data and len(response.data) > 0:
                            return response.data[0]
                        return None
                    except Exception as retry_e:
                        logging.error(f"Error creating user after creating tables: {retry_e}")
                        return None
                else:
                    logging.warning(f"Could not create Supabase tables. Falling back to SQLAlchemy.")
                    return None
            # Otherwise re-raising the exception
            raise inner_e
            
    except Exception as e:
        logging.error(f"Error creating user: {e}")
        return None

def get_search_history(user_id, limit=10):
    """
    Getting search history for a user.
    
    Args:
        user_id (int): User ID to get history for
        limit (int): Maximum number of results to return
        
    Returns:
        list: Search history items, empty list if none or error
    """
    if not supabase_client:
        logging.warning("Supabase client not initialized. Cannot fetch search history.")
        return []
        
    try:
        # Trying to fetch search history, handling case where table doesn't exist
        try:
            response = supabase_client.table(SEARCH_HISTORY_TABLE) \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
                
            return response.data or []
        except Exception as inner_e:
            # If this is a 404 error (table doesn't exist), logging and returning empty list
            if "404" in str(inner_e) or "does not exist" in str(inner_e).lower():
                logging.warning(f"Table {SEARCH_HISTORY_TABLE} doesn't exist. Falling back to SQLAlchemy.")
                return []
            # Otherwise re-raising the exception
            raise inner_e
            
    except Exception as e:
        logging.error(f"Error fetching search history: {e}")
        return []

def save_search(user_id, query, parameters):
    """
    Saving a search to history.
    
    Args:
        user_id (int): User ID who performed the search
        query (str): Search query string
        parameters (str): JSON string of search parameters
        
    Returns:
        dict: Created search record, None if failed
    """
    if not supabase_client:
        logging.warning("Supabase client not initialized. Cannot save search.")
        return None
        
    try:
        search_data = {
            "user_id": user_id,
            "query": query,
            "parameters": parameters
        }
        
        # Trying to insert the data, and handling case where table doesn't exist
        try:
            response = supabase_client.table(SEARCH_HISTORY_TABLE).insert(search_data).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as inner_e:
            # If this is a 404 error (table doesn't exist), logging and returning None
            if "404" in str(inner_e) or "does not exist" in str(inner_e).lower():
                logging.warning(f"Table {SEARCH_HISTORY_TABLE} doesn't exist. Falling back to SQLAlchemy.")
                return None
            # Otherwise re-raising the exception
            raise inner_e
            
    except Exception as e:
        logging.error(f"Error saving search: {e}")
        return None

def get_cached_search(cache_key):
    """
    Getting cached search results.
    
    Args:
        cache_key (str): Unique identifier for the search
        
    Returns:
        dict: Cached search data if found and not expired, None otherwise
    """
    if not supabase_client:
        logging.warning("Supabase client not initialized. Cannot get cached search.")
        return None
        
    try:
        import datetime
        now = datetime.datetime.utcnow().isoformat()
        
        # Trying to fetch cached search, handling case where table doesn't exist
        try:
            response = supabase_client.table(CACHE_TABLE) \
                .select("*") \
                .eq("cache_key", cache_key) \
                .gt("expires_at", now) \
                .execute()
                
            data = response.data
            
            if data and len(data) > 0:
                return data[0]
            return None
        except Exception as inner_e:
            # If this is a 404 error (table doesn't exist), logging and returning None
            if "404" in str(inner_e) or "does not exist" in str(inner_e).lower():
                logging.warning(f"Table {CACHE_TABLE} doesn't exist. Falling back to SQLAlchemy.")
                return None
            # Otherwise re-raising the exception
            raise inner_e
            
    except Exception as e:
        logging.error(f"Error fetching cached search: {e}")
        return None

def cache_search_results(cache_key, results, duration_hours=24):
    """
    Caching search results.
    
    Args:
        cache_key (str): Unique identifier for the search
        results (str): JSON string of search results
        duration_hours (int): Number of hours until cache expires
        
    Returns:
        dict: Created cache record, None if failed
    """
    if not supabase_client:
        logging.warning("Supabase client not initialized. Cannot cache search results.")
        return None
        
    try:
        import datetime
        from datetime import timedelta
        
        now = datetime.datetime.utcnow()
        expires_at = (now + timedelta(hours=duration_hours)).isoformat()
        
        # Trying to cache the search results, handling case where table doesn't exist
        try:
            # Checking if this cache key already exists
            try:
                existing = supabase_client.table(CACHE_TABLE) \
                    .select("id") \
                    .eq("cache_key", cache_key) \
                    .execute()
                    
                if existing.data and len(existing.data) > 0:
                    # Updating existing cache
                    cache_id = existing.data[0]["id"]
                    update_data = {
                        "results": results,
                        "created_at": now.isoformat(),
                        "expires_at": expires_at
                    }
                    
                    response = supabase_client.table(CACHE_TABLE) \
                        .update(update_data) \
                        .eq("id", cache_id) \
                        .execute()
                else:
                    # Creating new cache entry
                    cache_data = {
                        "cache_key": cache_key,
                        "results": results,
                        "created_at": now.isoformat(),
                        "expires_at": expires_at
                    }
                    
                    response = supabase_client.table(CACHE_TABLE).insert(cache_data).execute()
            except Exception as inner_e:
                # If this is a 404 error (table doesn't exist), logging and returning None
                if "404" in str(inner_e) or "does not exist" in str(inner_e).lower():
                    logging.warning(f"Table {CACHE_TABLE} doesn't exist. Falling back to SQLAlchemy.")
                    return None
                # Otherwise re-raising the exception
                raise inner_e
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as inner_e:
            # If this is a 404 error (table doesn't exist), logging and returning None
            if "404" in str(inner_e) or "does not exist" in str(inner_e).lower():
                logging.warning(f"Table {CACHE_TABLE} doesn't exist. Falling back to SQLAlchemy.")
                return None
            # Otherwise re-raising the exception
            raise inner_e
            
    except Exception as e:
        logging.error(f"Error caching search results: {e}")
        return None

def clear_expired_cache():
    """
    Removing all expired cache entries.
    
    Returns:
        int: Number of removed entries, -1 if error
    """
    if not supabase_client:
        logging.warning("Supabase client not initialized. Cannot clear expired cache.")
        return -1
        
    try:
        import datetime
        now = datetime.datetime.utcnow().isoformat()
        
        response = supabase_client.table(CACHE_TABLE) \
            .delete() \
            .lt("expires_at", now) \
            .execute()
            
        return len(response.data) if response.data else 0
    except Exception as e:
        logging.error(f"Error clearing expired cache: {e}")
        return -1