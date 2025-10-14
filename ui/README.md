# Needle UI

A modern React frontend for the Needle image search and management system.

## Features

- **Image Search**: Natural language search with configurable parameters
- **Directory Management**: Add, remove, enable/disable image directories
- **Indexing Progress**: Monitor directory indexing status and progress
- **Generator Management**: View available image generation services
- **System Status**: Real-time monitoring of all system components

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Needle backend running on `http://localhost:8000`
- Image generator service running on `localhost:8010`

### Installation

1. Navigate to the UI directory:
   ```bash
   cd ui
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

### Building for Production

```bash
npm run build
```

This creates a `build` folder with the production-ready files.

## Configuration

The UI automatically connects to the Needle API at `http://localhost:8000`. To change this, set the `REACT_APP_API_URL` environment variable:

```bash
REACT_APP_API_URL=http://your-api-url:8000 npm start
```

## Features Overview

### Search Page
- Natural language query input
- Configurable search parameters (number of images, generation settings)
- Real-time search results with generated and retrieved images
- Search history and logs

### Directory Management
- Add new image directories
- View directory details and indexing progress
- Enable/disable directories
- Remove directories
- Monitor indexing status

### Generator Management
- View available image generation services
- Check generator configuration requirements
- Monitor generator service status

### System Status
- Real-time health monitoring
- Service status overview
- Directory and generator status
- Recent activity logs
- System information

## API Integration

The UI integrates with the following Needle API endpoints:

- `GET /health` - Health check
- `GET /service/status` - Service status
- `GET /directory` - List directories
- `POST /directory` - Add directory
- `PUT /directory/{id}` - Update directory
- `DELETE /directory` - Remove directory
- `GET /directory/{id}` - Get directory details
- `POST /query` - Create search query
- `POST /search` - Perform search
- `GET /generator` - List generators
- `GET /search/logs` - Get search history

## Technology Stack

- **React 18** - UI framework
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **Tailwind CSS** - Styling
- **Lucide React** - Icons

## Development

### Project Structure

```
src/
├── components/          # Reusable UI components
│   └── Layout.js       # Main layout with navigation
├── pages/              # Page components
│   ├── SearchPage.js   # Image search interface
│   ├── DirectoryPage.js # Directory management
│   ├── GeneratorPage.js # Generator management
│   └── StatusPage.js   # System status monitoring
├── services/           # API integration
│   └── api.js         # API client and endpoints
├── styles/            # Global styles
│   └── index.css      # Tailwind CSS and custom styles
├── App.js             # Main app component
└── index.js           # Entry point
```

### Available Scripts

- `npm start` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is part of the Needle image search system.
