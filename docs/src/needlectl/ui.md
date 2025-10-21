# UI Component

The UI component of `needlectl` manages the web-based user interface for Needle. It allows you to start and stop the web UI, which provides a graphical interface for interacting with Needle's features.

## Commands Overview

### `start`

Starts the Needle web UI on a specified port.

- **Options:**
  - **`--port`** or **`-p`**: Port to run the UI on (default: 3000)

- **What it does:**
  - Starts the web UI server
  - Serves the React-based interface
  - Provides access to all Needle features through a web browser

- **Usage Examples:**
  ```bash
  # Start UI on default port (3000)
  needlectl ui start
  
  # Start UI on custom port
  needlectl ui start --port 8080
  ```

- **Output:**
  Displays the URL where the UI is accessible (e.g., `http://localhost:3000`)

### `stop`

Stops the running Needle web UI.

- **What it does:**
  - Stops the web UI server
  - Frees up the port for other uses

- **Usage Example:**
  ```bash
  needlectl ui stop
  ```

- **Output:**
  Confirms that the UI has been stopped

## Web UI Features

The web interface provides:

- **Search Interface**: Interactive query interface with sample queries
- **Directory Management**: Visual management of image directories
- **Generator Configuration**: Easy configuration of image generators
- **System Status**: Real-time monitoring of service health
- **Results Visualization**: Rich display of search results and generated images

## Accessing the UI

Once started, you can access the web UI by opening your browser and navigating to:

- **Default URL**: `http://localhost:3000`
- **Custom Port**: `http://localhost:[PORT]` (where [PORT] is your chosen port)

The UI will automatically connect to your running Needle backend service.
