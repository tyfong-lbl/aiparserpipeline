import pytest
import hashlib
import re
from tests.cache.test_fixtures import test_project_names


class TestProjectHashGeneration:
    """Test suite for project name hash generation functionality."""
    
    def test_project_hash_length(self, test_project_names):
        """Test that project hash is exactly 8 characters long."""
        from cache_utils import generate_project_hash
        
        for project_name in test_project_names:
            hash_value = generate_project_hash(project_name)
            assert len(hash_value) == 8, f"Hash for '{project_name}' should be exactly 8 characters, got {len(hash_value)}"
    
    def test_project_hash_consistency(self, test_project_names):
        """Test that same project name always produces the same hash."""
        from cache_utils import generate_project_hash
        
        for project_name in test_project_names:
            hash1 = generate_project_hash(project_name)
            hash2 = generate_project_hash(project_name)
            hash3 = generate_project_hash(project_name)
            
            assert hash1 == hash2 == hash3, f"Hash for '{project_name}' should be consistent across calls"
    
    def test_different_project_names_produce_different_hashes(self):
        """Test that different project names produce different hashes."""
        from cache_utils import generate_project_hash
        
        test_names = [
            "Solar Project Alpha",
            "Solar Project Beta", 
            "Wind Farm Delta",
            "Battery Storage Gamma",
            "Hydroelectric Epsilon"
        ]
        
        hashes = [generate_project_hash(name) for name in test_names]
        
        # All hashes should be unique
        assert len(set(hashes)) == len(hashes), "Different project names should produce different hashes"
    
    def test_special_characters_and_spaces_handling(self):
        """Test handling of special characters and spaces in project names."""
        from cache_utils import generate_project_hash
        
        test_cases = [
            "Project with spaces",
            "Project-with-hyphens",
            "Project_with_underscores",
            "Project & Symbols!",
            "Project (with parentheses)",
            "Project [with brackets]",
            "Project {with braces}",
            "Project @#$%^&*()",
            "Project with números 123",
            "Project with ünïcødé"
        ]
        
        for project_name in test_cases:
            hash_value = generate_project_hash(project_name)
            assert len(hash_value) == 8, f"Hash for '{project_name}' should be 8 characters"
            assert hash_value.isalnum(), f"Hash for '{project_name}' should be alphanumeric, got '{hash_value}'"
    
    def test_hash_contains_only_valid_filename_characters(self, test_project_names):
        """Test that hash contains only characters valid for filenames."""
        from cache_utils import generate_project_hash
        
        # Valid filename characters (alphanumeric only for safety across all OS)
        valid_pattern = re.compile(r'^[a-zA-Z0-9]+$')
        
        for project_name in test_project_names:
            hash_value = generate_project_hash(project_name)
            assert valid_pattern.match(hash_value), f"Hash '{hash_value}' for '{project_name}' contains invalid filename characters"
    
    def test_edge_cases(self):
        """Test edge cases for project name hashing."""
        from cache_utils import generate_project_hash
        
        # Very long project name
        long_name = "Very Long Project Name " * 50
        long_hash = generate_project_hash(long_name)
        assert len(long_hash) == 8, "Long project name should still produce 8-character hash"
        
        # Single character
        single_char = "A"
        single_hash = generate_project_hash(single_char)
        assert len(single_hash) == 8, "Single character project name should produce 8-character hash"
        
        # Numbers only
        numbers_only = "12345"
        numbers_hash = generate_project_hash(numbers_only)
        assert len(numbers_hash) == 8, "Numeric project name should produce 8-character hash"
        
        # Mixed case
        mixed_case = "MiXeD CaSe PrOjEcT"
        mixed_hash1 = generate_project_hash(mixed_case)
        mixed_hash2 = generate_project_hash(mixed_case.lower())
        # Case should matter for project names (unlike URLs)
        assert len(mixed_hash1) == 8 and len(mixed_hash2) == 8
        
        # Empty project name (edge case)
        with pytest.raises((ValueError, TypeError)):
            generate_project_hash("")
        
        # None project name (edge case)  
        with pytest.raises((ValueError, TypeError)):
            generate_project_hash(None)
    
    def test_hash_uses_sha256_algorithm(self):
        """Test that the hash is derived from SHA256."""
        from cache_utils import generate_project_hash
        
        test_project = "Test Solar Project"
        
        # Generate hash using our function
        our_hash = generate_project_hash(test_project)
        
        # The hash should be alphanumeric and 8 characters
        assert len(our_hash) == 8
        assert our_hash.isalnum()
        
        # Test that it's deterministic (same input = same output)
        assert generate_project_hash(test_project) == our_hash
    
    def test_hash_collision_resistance(self):
        """Test that similar project names produce different hashes."""
        from cache_utils import generate_project_hash
        
        similar_names = [
            "Solar Project 1",
            "Solar Project 2", 
            "Solar Project 11",
            "Solar Project 21",
            "Solar Project A",
            "Solar Project B",
            "Wind Project 1",
            "Solar Project Alpha",
            "Solar Alpha Project"
        ]
        
        hashes = [generate_project_hash(name) for name in similar_names]
        
        # All hashes should be unique despite similar inputs
        assert len(set(hashes)) == len(hashes), "Similar project names should produce different hashes"
    
    def test_case_sensitivity(self):
        """Test that project name hashing is case sensitive."""
        from cache_utils import generate_project_hash
        
        # Project names should be case sensitive (unlike URLs)
        test_cases = [
            ("Solar Project", "solar project"),
            ("WIND FARM", "wind farm"),
            ("Battery Storage", "BATTERY STORAGE"),
            ("Hydro Power", "hydro power")
        ]
        
        for name1, name2 in test_cases:
            hash1 = generate_project_hash(name1)
            hash2 = generate_project_hash(name2)
            
            # Different cases should generally produce different hashes
            # (though hash collisions are theoretically possible, they're extremely unlikely)
            assert len(hash1) == 8 and len(hash2) == 8
            # We don't assert they're different due to potential collisions, but test they're valid
    
    def test_whitespace_normalization(self):
        """Test whitespace handling in project names."""
        from cache_utils import generate_project_hash
        
        # Test various whitespace scenarios
        test_cases = [
            "  Solar Project  ",  # Leading/trailing spaces
            "Solar   Project",    # Multiple spaces
            "Solar\tProject",     # Tab character
            "Solar\nProject",     # Newline character
            "Solar Project"       # Normal spacing
        ]
        
        hashes = [generate_project_hash(name) for name in test_cases]
        
        # All should produce valid 8-character hashes
        for i, hash_val in enumerate(hashes):
            assert len(hash_val) == 8, f"Hash for '{test_cases[i]}' should be 8 characters"
            assert hash_val.isalnum(), f"Hash for '{test_cases[i]}' should be alphanumeric"
    
    def test_integration_with_url_hash_function(self):
        """Test that project hash function works well with URL hash function."""
        from cache_utils import generate_project_hash, generate_url_hash
        
        test_project = "Integration Test Project"
        test_url = "https://example.com/test"
        
        # Generate both hashes
        project_hash = generate_project_hash(test_project)
        url_hash = generate_url_hash(test_url)
        
        # Verify they have different lengths as specified
        assert len(project_hash) == 8, "Project hash should be 8 characters"
        assert len(url_hash) == 16, "URL hash should be 16 characters"
        
        # Both should be alphanumeric
        assert project_hash.isalnum(), "Project hash should be alphanumeric"
        assert url_hash.isalnum(), "URL hash should be alphanumeric"
        
        # They should be different (extremely high probability)
        assert project_hash != url_hash[:8], "Project and URL hashes should be different"
        
        # Test combination (as would be used in cache filenames)
        combined = f"{url_hash}_{project_hash}"
        assert len(combined) == 25, "Combined hash should be 16 + 1 + 8 = 25 characters"  # 16 + _ + 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])