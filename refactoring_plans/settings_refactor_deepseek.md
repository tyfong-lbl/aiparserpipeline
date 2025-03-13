```markdown
# Settings Refactor Development Plan

## Current State Analysis
- Hard-coded paths in main.py
- API settings directly in code
- Environment variable for API key
- Limited command line arguments
- Directory structures tied to script location

## Proposed Solution
Implement a hybrid configuration approach combining:
1. YAML configuration files
2. Environment variables
3. Command line arguments
4. Optional shell script wrapper

## Implementation Steps

### 1. Create Configuration Structure
- Create `config/` directory
- Add `config/default.yaml` for base configuration
- Add `config/development.yaml` for local development
- Add `config/production.yaml` for production settings
- Create `config.example.yaml` as template

### 2. Update Dependencies
- Add PyYAML to requirements.txt
- Add configuration management package (e.g., python-decouple)

### 3. Code Changes
- Create ConfigManager class
- Update main.py to use configuration system
- Add configuration validation
- Extend argument parser
- Add configuration override capability

### 4. Documentation
- Document configuration options
- Create example configurations
- Add configuration section to README
- Document environment variables

### 5. Helper Scripts
- Create shell script wrapper
- Add configuration generation script
- Add validation script

## Configuration Hierarchy
1. Command line arguments (highest priority)
2. Environment variables
3. YAML configuration file
4. Default values (lowest priority)

## Security Considerations
- Keep sensitive data in environment variables
- Add configuration validation
- Include security best practices in documentation
- Add configuration file to .gitignore

## Testing Plan
- Add configuration tests
- Test override functionality
- Validate error handling
- Test multiple environments

## Migration Plan
1. Create new configuration system
2. Add backward compatibility
3. Update documentation
4. Create migration guide
5. Phase out old configuration

## Timeline
1. Initial setup (1 day)
2. Core implementation (2-3 days)
3. Testing (1-2 days)
4. Documentation (1 day)
5. Review and refinement (1 day)
```
