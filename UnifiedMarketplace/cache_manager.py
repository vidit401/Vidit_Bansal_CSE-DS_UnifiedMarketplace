import json
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Import models and db within functions to avoid circular imports

# Cache duration in hours
CACHE_DURATION = 24

def get_cached_results(cache_key):
    """
    Get cached search results from the database.
    
    Args:
        cache_key (str): The unique key for the search query
        
    Returns:
        list: The cached search results or None if not found/expired
    """
    # Import here to avoid circular imports
    from models import CachedSearch
    from app import db
    from supabase_client import get_cached_search, supabase_client
    
    try:
        # Try Supabase cache first if available
        if supabase_client:
            cached_data = get_cached_search(cache_key)
            if cached_data:
                logging.info(f"Supabase cache hit for key: {cache_key}")
                return json.loads(cached_data.get('results', '[]'))
        
        # Fall back to SQLAlchemy
        # Look for a cached entry using db.session.query
        cached_entry = db.session.query(CachedSearch).filter(
            CachedSearch.cache_key == cache_key
        ).first()
        
        # Check if we have a valid cache entry
        if cached_entry and cached_entry.expires_at > datetime.utcnow():
            logging.info(f"SQLAlchemy cache hit for key: {cache_key}")
            return json.loads(cached_entry.results)
        
        # If cache entry exists but is expired, remove it
        if cached_entry:
            logging.info(f"Removing expired cache for key: {cache_key}")
            db.session.delete(cached_entry)
            db.session.commit()
            
        return None
        
    except Exception as e:
        logging.error(f"Error retrieving cached results: {str(e)}")
        return None

def cache_results(cache_key, results):
    """
    Cache search results in the database.
    
    Args:
        cache_key (str): The unique key for the search query
        results (list): The search results to cache
        
    Returns:
        bool: True if caching was successful, False otherwise
    """
    # Import here to avoid circular imports
    from models import CachedSearch
    from app import db
    from supabase_client import cache_search_results, supabase_client
    
    try:
        # Convert results to JSON string
        results_json = json.dumps(results)
        
        # Try to cache in Supabase first if available
        supabase_success = False
        if supabase_client:
            supabase_cache = cache_search_results(cache_key, results_json, CACHE_DURATION)
            supabase_success = supabase_cache is not None
            if supabase_success:
                logging.info(f"Successfully cached results in Supabase for key: {cache_key}")
        
        # Always cache in SQLAlchemy too for local access
        # Check if we already have a cache entry for this key
        existing_cache = db.session.query(CachedSearch).filter(
            CachedSearch.cache_key == cache_key
        ).first()
        
        # Calculate the expiration time
        expires_at = datetime.utcnow() + timedelta(hours=CACHE_DURATION)
        
        # If entry exists, update it
        if existing_cache:
            existing_cache.results = results_json
            existing_cache.created_at = datetime.utcnow()
            existing_cache.expires_at = expires_at
        else:
            # Create a new cache entry
            new_cache = CachedSearch(
                cache_key=cache_key,
                results=results_json,
                created_at=datetime.utcnow(),
                expires_at=expires_at
            )
            db.session.add(new_cache)
            
        # Commit the changes
        db.session.commit()
        logging.info(f"Successfully cached results in SQLAlchemy for key: {cache_key}")
        return True
        
    except Exception as e:
        logging.error(f"Error caching results: {str(e)}")
        # Try to rollback if the error was in SQLAlchemy
        try:
            db.session.rollback()
        except:
            pass
        return False

def clear_old_cache():
    """
    Remove all expired cache entries from the database.
    
    Returns:
        bool: True if cache clearing was successful, False otherwise
    """
    # Import here to avoid circular imports
    from models import CachedSearch
    from app import db
    from supabase_client import clear_expired_cache, supabase_client
    
    # Initialize success flags
    supabase_success = False
    sqlalchemy_success = False
    
    # Part 1: Try to clear from Supabase
    try:
        if supabase_client:
            supabase_cleared = clear_expired_cache()
            if supabase_cleared >= 0:  # -1 indicates error
                supabase_success = True
                logging.info(f"Cleared {supabase_cleared} expired cache entries from Supabase")
            else:
                logging.warning("Failed to clear Supabase cache, continuing with SQLAlchemy")
    except Exception as e:
        logging.error(f"Error clearing Supabase cache: {str(e)}")
        # Continue to SQLAlchemy regardless of Supabase error
    
    # Part 2: Try to clear from SQLAlchemy
    try:
        # Find all expired cache entries with a timeout to avoid freezing
        expired_entries = db.session.query(CachedSearch).filter(
            CachedSearch.expires_at < datetime.utcnow()
        ).all()
        
        if expired_entries:
            entry_count = len(expired_entries)
            # Delete in smaller batches to reduce transaction size
            batch_size = 100
            for i in range(0, entry_count, batch_size):
                batch = expired_entries[i:i+batch_size]
                try:
                    for entry in batch:
                        db.session.delete(entry)
                    db.session.commit()
                    logging.info(f"Cleared batch of {len(batch)} expired cache entries")
                except Exception as batch_error:
                    db.session.rollback()
                    logging.error(f"Error clearing batch: {str(batch_error)}")
            
            sqlalchemy_success = True
            logging.info(f"Cleared {entry_count} expired cache entries from SQLAlchemy")
        else:
            sqlalchemy_success = True
            logging.info("No expired cache entries found in SQLAlchemy")
    except Exception as e:
        logging.error(f"Error clearing SQLAlchemy cache: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
    
    # Return True if either database was cleared successfully
    return supabase_success or sqlalchemy_success
