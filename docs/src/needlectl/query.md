# Query Component

The Query Component of `needlectl` allows you to interact with Needle's image retrieval capabilities. It lets you execute natural language queries, view query logs, and configure query-related settings.

## Commands Overview

### `run`

This command executes a search query against the Needle image retrieval database.

- **Options:**
    - **`prompt`** (string): The search prompt in natural language.
    - **`-n` or `--n`** (integer, optional): Specifies the number of images to retrieve.
    - **`-m` or `--m`** (integer, optional): Specifies the number of images per engine.
    - **`-k` or `--k`** (integer, optional): Specifies the number of engines to use.
    - **`--image-size`** (integer, optional): Sets the desired image size for image generation.
    - **`--include-base-images`** (boolean, optional): Indicates whether to include base images in the results preview.
    - **`--use-fallback`** (boolean, optional): Indicates whether to use fallback mode if the primary engines set fails.

- **What It Does:**
    1. Retrieves the enabled and activated generator configurations using the Generator Config Manager.
    2. If no generator configuration is found, it displays an error message suggesting you use `needlectl generator config` to configure a generator.
    3. Executes the search query with the provided parameters via the backend API.
    4. Displays the search results in the specified output format (human-readable, JSON, or YAML).

- **Usage Examples:**
   ```bash
   # Run a basic query with a prompt
   needlectl query run "red cars"
   
   # Run a query with additional options
   needlectl query run "red cars" --n 5 --m 2 --k 3 --image-size 512 --include-base-images true --use-fallback false
   ```

### `log`
This command retrieves and displays the logs of search queries executed by Needle.

- **Usage Examples:**
   ```bash
   needlectl query log
   ```
  
### `config`
This command manages the environmental configuration for the query component.

- **Usage Examples:**
   ```bash
   needlectl query config
   ```
