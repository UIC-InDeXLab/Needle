# Generator Component

The Generator Component of `needlectl` is used to manage image generators for Needle. It allows you to list all available generators from the backend and configure generator settings that are used during image queries.

## Commands Overview

### `list`

This command lists all available image generators as retrieved from the backend.

- **What It Does:**
    1. Connects to the backend API.
    2. Retrieves the list of available generators.
    3. Displays the result in the specified output format (human-readable, JSON, or YAML).

- **Usage Example:**
   ```bash
   needlectl generator list
   ```
  
### `config`
This command manages the configuration for image generators used by Needle.


- **Usage Example:**
   ```bash
   needlectl generator config
   ```