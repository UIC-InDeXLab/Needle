# Needle UI Demo

This is a React-based demo of the Needle UI that showcases the interface with mock data instead of requiring a backend connection.

## Features

- **Sample Queries**: Click on predefined sample queries to see search results
- **Full UI Experience**: Complete Needle UI with all pages (Search, Directories, Generators, Status)
- **Mock Data**: All API calls are mocked with realistic sample data
- **Responsive Design**: Works on desktop and mobile devices

## Quick Start

### Option 1: Use Built Version (Recommended)
```bash
# Serve the built React app
npx serve -s build -l 8004
```

Then open http://localhost:8004 in your browser.

### Option 2: Development Mode
```bash
# Install dependencies
npm install

# Start development server
npm start
```

## Demo Structure

### Sample Queries
The demo includes 6 sample queries:
- "a cute cat"
- "mountain landscape" 
- "red sports car"
- "abstract art"
- "delicious food"
- "beautiful sunset"

Each query shows:
- Generated image (using Lorem Picsum)
- 5 similar retrieved images
- Performance timing data
- Search logs

### Mock Data
All API endpoints are mocked in `src/services/mockApi.js`:
- Search results with realistic timing data
- Directory management with LVIS dataset info
- Generator configuration
- Service status and health checks
- Search logs and activity

### Customization
To modify the demo data:
1. Edit `src/services/mockApi.js` to change sample queries, directories, generators, etc.
2. Run `npm run build` to rebuild
3. Serve the updated build

## Pages

- **Search**: Sample queries and results display
- **Directories**: Mock directory management (LVIS dataset)
- **Generators**: Mock generator configuration (Lorem Picsum)
- **Status**: System health and performance metrics

## Technical Details

- Built with React 18 and Tailwind CSS
- Uses Lucide React for icons
- Mock API simulates real backend responses
- Responsive design with mobile sidebar
- Production build optimized for deployment

## Deployment

The `build/` folder contains the production-ready static files that can be deployed to any static hosting service (GitHub Pages, Netlify, Vercel, etc.).