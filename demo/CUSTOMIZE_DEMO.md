# Customizing the Needle Demo

This guide explains how to customize the demo with your own sample queries and images.

## File Structure

```
demo/
├── src/
│   ├── sample-queries.json     # Your custom queries and results
│   └── services/
│       └── mockApi.js          # Imports the JSON file
├── public/
│   └── demo-images/            # Your custom images go here
│       ├── cat_generated.jpg
│       ├── cat_001.jpg
│       ├── cat_002.jpg
│       ├── mountain_generated.jpg
│       ├── mountain_001.jpg
│       └── ... (more images)
```

## 1. Adding Your Images

### Directory: `public/demo-images/`

Place all your images in the `public/demo-images/` directory. Use this naming convention:

**Generated Images (one per query):**
- `{theme}_generated.jpg` - The AI-generated image for each query
- Examples: `cat_generated.jpg`, `mountain_generated.jpg`, `car_generated.jpg`

**Retrieved Images (5 per query):**
- `{theme}_001.jpg` to `{theme}_005.jpg` - The similar images found
- Examples: `cat_001.jpg`, `cat_002.jpg`, `mountain_001.jpg`, etc.

### Image Requirements:
- **Format**: JPG, PNG, or WebP
- **Size**: Recommended 400x400px or larger
- **Quality**: High quality for best demo experience

## 2. Editing the JSON File

### File: `src/sample-queries.json`

Edit this file to add your own queries and results. Here's the structure:

```json
{
  "queries": [
    {
      "id": "query_1",
      "text": "your search query here",
      "generatedImage": {
        "url": "/demo-images/your_generated.jpg",
        "prompt": "your search query here"
      },
      "results": [
        {
          "id": "img_1_1",
          "url": "/demo-images/your_001.jpg",
          "filename": "your_001.jpg",
          "similarity": 0.95
        },
        {
          "id": "img_1_2",
          "url": "/demo-images/your_002.jpg",
          "filename": "your_002.jpg",
          "similarity": 0.92
        }
        // ... add up to 5 results per query
      ]
    }
    // ... add more queries
  ]
}
```

### Field Descriptions:

- **`id`**: Unique identifier for each query (e.g., "query_1", "query_2")
- **`text`**: The search query text that users will see
- **`generatedImage.url`**: Path to the AI-generated image (must start with `/demo-images/`)
- **`generatedImage.prompt`**: The prompt used to generate the image
- **`results`**: Array of 5 similar images found
  - **`id`**: Unique identifier for each result image
  - **`url`**: Path to the result image (must start with `/demo-images/`)
  - **`filename`**: Display name for the image
  - **`similarity`**: Similarity score (0.0 to 1.0, higher = more similar)

## 3. Updating the Mock API

### File: `src/services/mockApi.js`

The file is already configured to import from `src/sample-queries.json`. No changes needed here.

## 4. Example: Adding a New Query

Let's say you want to add a query for "vintage cars":

1. **Add images to `public/demo-images/`:**
   - `vintage_car_generated.jpg` (the AI-generated image)
   - `vintage_car_001.jpg` to `vintage_car_005.jpg` (5 similar images)

2. **Add to `src/sample-queries.json`:**
```json
{
  "id": "query_7",
  "text": "vintage cars",
  "generatedImage": {
    "url": "/demo-images/vintage_car_generated.jpg",
    "prompt": "vintage cars"
  },
  "results": [
    {
      "id": "img_7_1",
      "url": "/demo-images/vintage_car_001.jpg",
      "filename": "vintage_car_001.jpg",
      "similarity": 0.94
    },
    {
      "id": "img_7_2",
      "url": "/demo-images/vintage_car_002.jpg",
      "filename": "vintage_car_002.jpg",
      "similarity": 0.91
    },
    {
      "id": "img_7_3",
      "url": "/demo-images/vintage_car_003.jpg",
      "filename": "vintage_car_003.jpg",
      "similarity": 0.88
    },
    {
      "id": "img_7_4",
      "url": "/demo-images/vintage_car_004.jpg",
      "filename": "vintage_car_004.jpg",
      "similarity": 0.85
    },
    {
      "id": "img_7_5",
      "url": "/demo-images/vintage_car_005.jpg",
      "filename": "vintage_car_005.jpg",
      "similarity": 0.82
    }
  ]
}
```

## 5. Testing Your Changes

After adding your images and updating the JSON:

1. **Development mode**: Run `npm start` to see changes immediately
2. **Production build**: Run `npm run build` then `npx serve -s build -l 8004`

## 6. Tips for Best Results

- **Consistent themes**: Group related images together (cats, mountains, cars, etc.)
- **High similarity scores**: Use 0.8+ for the most similar images, 0.6+ for moderately similar
- **Descriptive queries**: Use clear, specific search terms
- **Quality images**: Use high-resolution, well-composed images
- **Variety**: Include different angles, lighting, and compositions for each theme

## 7. Troubleshooting

- **Images not showing**: Check that paths start with `/demo-images/`
- **JSON errors**: Validate your JSON syntax using an online validator
- **Similarity scores**: Keep them between 0.0 and 1.0
- **File names**: Use lowercase with underscores, avoid spaces

That's it! You now have a complete guide to customize the Needle demo with your own data.
