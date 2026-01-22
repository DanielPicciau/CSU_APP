"""
Caching utilities for performance optimization.
"""

from functools import wraps
from django.core.cache import cache
from django.conf import settings


# Default cache timeouts (in seconds)
CACHE_TIMEOUTS = getattr(settings, 'CACHE_TIMEOUTS', {
    'user_profile': 300,      # 5 minutes
    'dashboard_stats': 120,   # 2 minutes
    'entry_list': 300,        # 5 minutes
    'static_pages': 3600,     # 1 hour
})


def get_user_cache_key(user_id, prefix, extra=''):
    """Generate a cache key for user-specific data."""
    return f"user:{user_id}:{prefix}:{extra}"


def cache_user_data(prefix, timeout_key='dashboard_stats'):
    """
    Decorator to cache user-specific view data.
    
    Usage:
        @cache_user_data('home_stats')
        def get_home_stats(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return func(request, *args, **kwargs)
            
            cache_key = get_user_cache_key(
                request.user.id, 
                prefix,
                str(args) + str(sorted(kwargs.items()))
            )
            
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            result = func(request, *args, **kwargs)
            timeout = CACHE_TIMEOUTS.get(timeout_key, 300)
            cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


def invalidate_user_cache(user_id, prefix=None):
    """
    Invalidate cache for a user.
    If prefix is None, this is a no-op (can't invalidate all keys easily).
    """
    if prefix:
        # Invalidate specific cache key prefix
        # Note: This requires cache backend that supports key deletion by pattern
        # For simple cases, we just delete the specific key
        cache_key = get_user_cache_key(user_id, prefix, '*')
        cache.delete(cache_key)


def cached_property_with_ttl(ttl=300):
    """
    A cached property decorator with time-to-live support.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self):
            cache_key = f"{self.__class__.__name__}:{id(self)}:{func.__name__}"
            result = cache.get(cache_key)
            if result is None:
                result = func(self)
                cache.set(cache_key, result, ttl)
            return result
        return property(wrapper)
    return decorator


class CacheManager:
    """
    Helper class for managing cache in views.
    """
    
    @staticmethod
    def get_or_set(key, callback, timeout=300):
        """Get value from cache or compute and store it."""
        value = cache.get(key)
        if value is None:
            value = callback()
            cache.set(key, value, timeout)
        return value
    
    @staticmethod
    def invalidate_user_entries(user_id):
        """Invalidate all entry-related caches for a user."""
        prefixes = ['home_stats', 'history_stats', 'dashboard_stats', 'entry_list']
        for prefix in prefixes:
            cache_key = get_user_cache_key(user_id, prefix, '')
            cache.delete(cache_key)
    
    @staticmethod
    def warm_cache(user):
        """Pre-warm cache for a user (call after login)."""
        from datetime import date, timedelta
        from django.utils import timezone
        import pytz
        from tracking.models import DailyEntry
        
        # Get user's today
        user_tz = pytz.timezone(user.profile.default_timezone)
        today = timezone.now().astimezone(user_tz).date()
        
        # Pre-fetch common queries
        week_ago = today - timedelta(days=6)
        
        # Cache today's entry
        today_entry = DailyEntry.objects.filter(user=user, date=today).first()
        cache_key = get_user_cache_key(user.id, 'today_entry', str(today))
        cache.set(cache_key, today_entry, CACHE_TIMEOUTS['dashboard_stats'])
        
        # Cache week entries
        week_entries = list(DailyEntry.objects.filter(
            user=user,
            date__gte=week_ago,
            date__lte=today,
        ).order_by("date"))
        cache_key = get_user_cache_key(user.id, 'week_entries', str(today))
        cache.set(cache_key, week_entries, CACHE_TIMEOUTS['dashboard_stats'])


# Signals to invalidate cache when entries are modified
def setup_cache_invalidation_signals():
    """
    Set up signals to invalidate cache when data changes.
    Call this in AppConfig.ready()
    """
    from django.db.models.signals import post_save, post_delete
    from tracking.models import DailyEntry
    
    def invalidate_entry_cache(sender, instance, **kwargs):
        CacheManager.invalidate_user_entries(instance.user_id)
    
    post_save.connect(invalidate_entry_cache, sender=DailyEntry)
    post_delete.connect(invalidate_entry_cache, sender=DailyEntry)
