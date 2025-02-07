# Directory Component

The directory component of `needlectl` is responsible for managing image directories in the Needle system. It allows you
to add directories for image indexing, remove directories, list existing directories, modify directory configurations,
and view detailed information about a directory.

## Commands Overview

### `add`

This command adds a new image directory to Needle's indexing system.

- **Options:**
  - **`path`** (string): The path to the directory to be added.
  - **`--show-progress`** (boolean, optional): If enabled, displays a progress bar showing the indexing progress.

- **What It Does:**

  1. Connects to the backend API and adds the directory.
  2. If successful, returns a directory ID.
  3. If the `--show-progress` flag is set, a progress bar (powered by the `tqdm` library) is displayed. This progress bar
     periodically updates based on the indexing ratio reported by the backend and shows an estimated time for completion.

- **Usage Examples:**

   ```bash
   # Add a directory without displaying indexing progress
   needlectl directory add /path/to/my/images
   
   # Add a directory and display the indexing progress
   needlectl directory add /path/to/my/images --show-progress
   ```

### `remove`

This command removes an image directory from Needle.

- **Options:**
  - **`path`** (string): The path to the directory to be removed.

- **Usage Examples:**
   ```bash
   needlectl directory remove /path/to/my/images
   ```

### `list`

This command lists all the directories currently registered in Needle.

- **Usage Examples:**
   ```bash
   needlectl directory list
   ```

### `modify`
This command allows you to modify the configuration for your added directories, you can enable/disable them for
searching. Needle will not search in disabled directories.

- **Usage Examples:**
   ```bash
   needlectl directory modify
   ```

### `describe`
This command provides detailed information about a specific directory by its directory ID.

- **Options:**
  - **`did`** (integer):  The unique identifier of the directory.

- **Usage Examples:**
   ```bash
   needlectl directory describe 1
   ```

### `config`
This command manages the environmental configuration for the directory component.

- **Usage Examples:**
   ```bash
   needlectl directory config
   ```