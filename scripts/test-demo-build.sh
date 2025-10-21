#!/bin/bash
# Test script to build and serve the demo locally

set -e

echo "🔧 Testing Demo Build Process"
echo "=============================="

# Check if we're in the right directory
if [ ! -f "demo/package.json" ]; then
    echo "❌ Error: Please run this script from the Needle root directory"
    exit 1
fi

# Install dependencies
echo "📦 Installing demo dependencies..."
cd demo
npm ci

# Build the demo
echo "🏗️  Building demo..."
npm run build

# Check if build was successful
if [ -d "build" ]; then
    echo "✅ Demo build successful!"
    echo "📁 Build output: demo/build/"
    echo ""
    echo "🚀 To test the demo locally:"
    echo "   cd demo && npx serve -s build -l 8004"
    echo "   Then visit: http://localhost:8004"
else
    echo "❌ Demo build failed!"
    exit 1
fi

echo ""
echo "🎉 Demo build test completed successfully!"
