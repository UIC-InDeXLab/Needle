# needlectl Command Line Tool

needlectl is the primary command-line interface that connects to the Needle backend service and performs a variety of tasks to manage and interact with Needle. It provides both general options and component-specific commands.

## General Options

The following options are available with needlectl:

- **`--api-url`**: Specifies the backend URL to connect to.  
  _Default:_ `127.0.0.1:8000`

- **`--output`**: Determines the format of the output.  
  _Supported formats:_ human-readable, JSON, YAML.  
  _Default:_ human-readable.

- **`--version`**: Prints the version information for both the Needle backend and the needlectl tool.

- **`--install-completion`**: Installs auto-completion for your current shell.


> **Note:** `--api-url` and `--output` are accessible globally and in all commands, for example, in order to get the outputs of a query in JSON format you can use following command: 
> ```bash
> needlectl --output json query run "a wolf howling"
> ```



## Components Overview

needlectl is organized into several components, each dedicated to specific functions within the Needle system. For more detailed information, please refer to the corresponding pages for each component.

### [Service](service.md)
Manages Needle's core service operations, including:
- Starting the service
- Restarting the service
- Stopping the service
- Viewing logs
- Upgrading the service

### [Directory](directory.md)
Handles image directory management tasks, such as:
- Adding directories
- Removing directories
- Indexing images

### [Query](query.md)
Executes natural language queries against the image database, providing flexible and powerful search capabilities.

### [Generator](generator.md)
Manages image generation operations, allowing you to adjust parameters and generate images as needed.

