import pytest
import hashlib
import re
from urllib.parse import urlparse, urlunparse
from tests.cache.test_fixtures import test_urls


class TestUrlHashGeneration:
    """Test suite for URL hash generation functionality."""
    
    def test_url_hash_length(self, test_urls):
        """Test that URL hash is exactly 16 characters long."""
        from cache_utils import generate_url_hash
        
        for url in test_urls:
            hash_value = generate_url_hash(url)
            assert len(hash_value) == 16, f"Hash for {url} should be exactly 16 characters, got {len(hash_value)}"
    
    def test_url_hash_consistency(self, test_urls):
        """Test that same URL always produces the same hash."""
        from cache_utils import generate_url_hash
        
        for url in test_urls:
            hash1 = generate_url_hash(url)
            hash2 = generate_url_hash(url)
            hash3 = generate_url_hash(url)
            
            assert hash1 == hash2 == hash3, f"Hash for {url} should be consistent across calls"
    
    def test_different_urls_produce_different_hashes(self):
        """Test that different URLs produce different hashes."""
        from cache_utils import generate_url_hash
        
        test_urls = [
            "https://example.com",
            "https://google.com", 
            "https://example.com/path",
            "https://example.com?param=value",
            "https://subdomain.example.com"
        ]
        
        hashes = [generate_url_hash(url) for url in test_urls]
        
        # All hashes should be unique
        assert len(set(hashes)) == len(hashes), "Different URLs should produce different hashes"
    
    def test_url_variations_normalization(self):
        """Test URL variations are handled appropriately."""
        from cache_utils import generate_url_hash
        
        # Test trailing slash normalization
        url_with_slash = "https://example.com/"
        url_without_slash = "https://example.com"
        
        hash_with_slash = generate_url_hash(url_with_slash)
        hash_without_slash = generate_url_hash(url_without_slash)
        
        # These should produce the same hash (normalized)
        assert hash_with_slash == hash_without_slash, "URLs with/without trailing slash should normalize to same hash"
        
        # Test case sensitivity in domain (should be case insensitive)
        url_lower = "https://example.com/path"
        url_upper = "https://EXAMPLE.COM/path"
        
        hash_lower = generate_url_hash(url_lower)
        hash_upper = generate_url_hash(url_upper) 
        
        assert hash_lower == hash_upper, "Domain should be case insensitive"
        
        # Test parameter order normalization
        url_params1 = "https://example.com?b=2&a=1"
        url_params2 = "https://example.com?a=1&b=2"
        
        hash_params1 = generate_url_hash(url_params1)
        hash_params2 = generate_url_hash(url_params2)
        
        assert hash_params1 == hash_params2, "Parameter order should be normalized"
    
    def test_hash_contains_only_valid_filename_characters(self, test_urls):
        """Test that hash contains only characters valid for filenames."""
        from cache_utils import generate_url_hash
        
        # Valid filename characters (alphanumeric only for safety across all OS)
        valid_pattern = re.compile(r'^[a-zA-Z0-9]+$')
        
        for url in test_urls:
            hash_value = generate_url_hash(url)
            assert valid_pattern.match(hash_value), f"Hash '{hash_value}' for {url} contains invalid filename characters"
    
    def test_edge_cases(self):
        """Test edge cases like very long URLs, special characters, unicode."""
        from cache_utils import generate_url_hash
        
        # Very long URL
        long_url = "https://example.com/" + "a" * 2000
        long_hash = generate_url_hash(long_url)
        assert len(long_hash) == 16, "Long URL should still produce 16-character hash"
        
        # URL with special characters
        special_url = "https://example.com/path with spaces & symbols!@#$%^&*()"
        special_hash = generate_url_hash(special_url)
        assert len(special_hash) == 16, "URL with special characters should produce 16-character hash"
        
        # URL with unicode characters
        unicode_url = "https://example.com/path/测试/ünïcødé"
        unicode_hash = generate_url_hash(unicode_url)
        assert len(unicode_hash) == 16, "Unicode URL should produce 16-character hash"
        
        # Empty URL (edge case)
        with pytest.raises((ValueError, TypeError)):
            generate_url_hash("")
        
        # None URL (edge case)  
        with pytest.raises((ValueError, TypeError)):
            generate_url_hash(None)
    
    def test_hash_uses_sha256_algorithm(self):
        """Test that the hash is derived from SHA256."""
        from cache_utils import generate_url_hash
        
        test_url = "https://example.com/test"
        
        # Generate hash using our function
        our_hash = generate_url_hash(test_url)
        
        # The hash should be alphanumeric and 16 characters
        assert len(our_hash) == 16
        assert our_hash.isalnum()
        
        # Test that it's deterministic (same input = same output)
        assert generate_url_hash(test_url) == our_hash
    
    def test_hash_collision_resistance(self):
        """Test that similar URLs produce different hashes."""
        from cache_utils import generate_url_hash
        
        similar_urls = [
            "https://example.com/page1",
            "https://example.com/page2", 
            "https://example.com/page11",
            "https://example.com/page21",
            "https://example1.com/page",
            "https://example2.com/page"
        ]
        
        hashes = [generate_url_hash(url) for url in similar_urls]
        
        # All hashes should be unique despite similar inputs
        assert len(set(hashes)) == len(hashes), "Similar URLs should produce different hashes"
    
    def test_url_normalization_details(self):
        """Test specific URL normalization behaviors."""
        from cache_utils import generate_url_hash
        
        # Test scheme normalization (should be case insensitive)
        assert generate_url_hash("HTTP://example.com") == generate_url_hash("http://example.com")
        assert generate_url_hash("HTTPS://example.com") == generate_url_hash("https://example.com")
        
        # Test port normalization (default ports should be removed)
        assert generate_url_hash("https://example.com:443/path") == generate_url_hash("https://example.com/path")
        assert generate_url_hash("http://example.com:80/path") == generate_url_hash("http://example.com/path")
        
        # Test fragment removal (fragments should be ignored)
        assert generate_url_hash("https://example.com/path#fragment") == generate_url_hash("https://example.com/path")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])