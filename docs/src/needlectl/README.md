# needlectl Command Line Tool

needlectl is the primary command-line interface that connects to the Needle backend service and performs a variety of tasks to manage and interact with Needle. It provides both general options and component-specific commands.

## General Options

The following options are available with needlectl:

- **`--api-url`**: Specifies the backend URL to connect to.  
  _Default:_ `http://127.0.0.1:8000`

- **`--output`**: Determines the format of the output.  
  _Supported formats:_ human, json, yaml.  
  _Default:_ human.

- **`--version`** or **`-v`**: Prints the version information for both the Needle backend and the needlectl tool.

- **`--home`** or **`-H`**: Specifies the Needle installation directory.  
  _Default:_ Auto-detected from installation

- **`--profile`**: Selects the runtime profile (prod or dev).  
  _Default:_ prod

- **`--config-dir`**: Overrides the configuration directory path.

> **Note:** `--api-url` and `--output` are accessible globally and in all commands, for example, in order to get the outputs of a query in JSON format you can use following command: 
> ```bash
> needlectl --output json query run "a wolf howling"
> ```

## Profiles & Configuration

You can use the `--home`/`-H` flag to point needlectl at a custom Needle installation or local checkout, and select a runtime profile (`prod` or `dev`) that auto-configures the compose files and config directory.

### Development Profile
```bash
needlectl --home $(pwd) --profile dev service start
```
This uses:
- `NEEDLE_CONFIG_DIR=$NEEDLE_HOME/configs/fast`
- Infrastructure: `docker/docker-compose.infrastructure.yaml`
- Backend: Virtual environment
- Image Generator: Virtual environment

### Production Profile
```bash
needlectl --home /opt/needle --profile prod service start
```
This uses:
- `NEEDLE_CONFIG_DIR=$NEEDLE_HOME/configs/balanced` (or your chosen mode)
- Infrastructure: `docker/docker-compose.infrastructure.yaml`
- Backend: Virtual environment
- Image Generator: Virtual environment



## Components Overview

needlectl is organized into several components, each dedicated to specific functions within the Needle system. For more detailed information, please refer to the corresponding pages for each component.

### [Service](service.md)
Manages Needle's core service operations, including:
- Starting the service
- Restarting the service
- Stopping the service
- Viewing logs
- Updating components
- Managing configuration

### [Directory](directory.md)
Handles image directory management tasks, such as:
- Adding directories
- Removing directories
- Listing directories
- Modifying directory settings
- Viewing directory details

### [Query](query.md)
Executes natural language queries against the image database, providing flexible and powerful search capabilities:
- Running search queries
- Viewing query logs
- Managing query configuration

### [Generator](generator.md)
Manages image generation operations, allowing you to:
- List available generators
- Configure generator settings
- Manage image generation parameters

### [UI](ui.md)
Controls the web-based user interface:
- Starting the web UI
- Stopping the web UI
- Managing UI configuration

