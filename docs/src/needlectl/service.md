# Service Component

The service component of `needlectl` manages the core operations of Needle. It connects to the Needle backend service and uses Docker Compose to start, stop, restart, check status, view logs, update components, and configure the service environment.

> **Note:** Most commands rely on the `--api-url` option (default: `http://127.0.0.1:8000`) to connect to the backend API. You can set this globally if needed.

## Commands Overview


### `start`
Starts the Needle services by launching the required Docker containers and waiting for the backend API to become available.

- **What it does:**
    - Uses the Docker Compose Manager to start containers.
    - Calls the backend API and waits until it is accessible.
- **Usage Example:**
  ```bash
  needlectl service start
  ```
  
- **Output:**
   Displays messages indicating that the services are starting, and if the backend API becomes available, it prints "Services started." If not, an error is shown.
  

### `stop`
Stops the Needle services by shutting down the Docker containers.

- **What it does:**
    - Uses the Docker Compose Manager to stop all running containers.

- **Usage Example:**
  ```bash
   needlectl service stop
  ```

- **Output:**
  A confirmation message "Services stopped." is printed once the containers are shut down.

### `restart`

Restarts the Needle services by first stopping and then starting the Docker containers again. It also waits for the backend API to be available after the restart.

- **Usage Example:**
  ```bash
  needlectl service restart
  ```

### `stop`
Stops the Needle services by shutting down the Docker containers.

- **What it does:**
  - Uses the Docker Compose Manager to restart containers.
  - Waits for the backend API to respond after restarting.


- **Output:**
  Displays messages for restarting and confirms when the services have been restarted successfully.
- 
- **Usage Example:**
  ```bash
  needlectl service stop
  ```

### `status`
Retrieves and displays the current status of Needle services using the backend API.

- **Usage Example:**
  ```bash
  needlectl service status
  ```

### `log`
Displays the logs from the Needle backend service.

- **Usage Example:**
  ```bash
  needlectl service log
  ```
  
### `update`
Updates Needle components to the latest versions.

- **Options:**
  - **`--force`** or **`-f`**: Force update even if already up to date
  - **`--component`** or **`-c`**: Update specific component (needlectl, backend, ui, or all)

- **What it does:**
  - Checks for the latest release information
  - Shows current versions of all components
  - Updates the specified components
  - Provides status updates during the process

- **Usage Examples:**
  ```bash
  # Update all components
  needlectl service update
  
  # Update only the backend
  needlectl service update --component backend
  
  # Force update even if up to date
  needlectl service update --force
  ```

- **Output:**
  Displays current and latest versions, then updates the specified components with progress indicators.

### `config`
Manages the configuration for the Needle service environment.

- **Usage Example:**
  ```bash
  needlectl service config
  ```
  
> **Warning:** Changes made via this command can affect service operations. Ensure you understand the impact before making modifications.