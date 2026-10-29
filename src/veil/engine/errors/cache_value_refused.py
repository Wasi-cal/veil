class CacheValueRefused(ValueError):
    """The cache refuses to store this. The value or the key looks like a secret, or it has no lifetime.

    This is a mistake in the code that calls the cache. The message never repeats the value.
    """
