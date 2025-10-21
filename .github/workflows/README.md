# GitHub Workflows

This directory contains GitHub Actions workflows for the Needle project.

## Workflows

### 📚 Deploy Documentation and Demo (`deploy-books.yaml`)

**Triggers:**
- Push to `main` branch when `docs/` or `demo/` directories change
- Manual workflow dispatch

**What it does:**
1. **Builds the demo**: Installs Node.js dependencies and builds the React demo
2. **Builds documentation**: Uses mdBook to build the documentation
3. **Integrates demo**: Copies the demo build into the documentation structure
4. **Deploys to GitHub Pages**: Serves both docs and demo from the same site

**Output:**
- Documentation: `https://uic-indexlab.github.io/Needle/`
- Demo: `https://uic-indexlab.github.io/Needle/demo/`

### 🚀 Release Needlectl (`release-needlectl.yaml`)

**Triggers:**
- Push tags matching `v*` pattern
- Manual workflow dispatch

**What it does:**
1. **Builds binaries**: Creates needlectl binaries for Linux and macOS
2. **Creates release**: Automatically creates GitHub releases
3. **Uploads artifacts**: Attaches built binaries to the release

### 🎨 Deploy Demo (`deploy-demo.yaml`)

**Triggers:**
- Push to `main` branch when `demo/` directory changes
- Manual workflow dispatch

**What it does:**
1. **Builds demo**: Installs dependencies and builds the React demo
2. **Deploys to GitHub Pages**: Serves the demo as a standalone site

**Note:** This workflow is separate from the main documentation deployment and can be used for demo-only updates.

## Demo Integration

The demo is integrated into the main documentation site in two ways:

1. **Embedded Demo**: The demo is copied into `docs/book/demo/` and served alongside the documentation
2. **Standalone Demo**: The demo can also be deployed as a standalone site using the `deploy-demo.yaml` workflow

## Local Testing

To test the demo build process locally:

```bash
# From the Needle root directory
./scripts/test-demo-build.sh
```

This will:
- Install demo dependencies
- Build the demo
- Verify the build output
- Provide instructions for local testing

## Demo Customization

The demo can be customized by:

1. **Adding new queries**: Edit `demo/src/sample-queries.json`
2. **Adding images**: Place images in `demo/public/demo-images/`
3. **Updating mock data**: Modify `demo/src/services/mockApi.js`

For detailed customization instructions, see [Demo Customization Guide](../demo/CUSTOMIZE_DEMO.md).

## Troubleshooting

### Demo Build Fails
- Check Node.js version (requires 18+)
- Verify all dependencies are installed
- Check for TypeScript/ESLint errors

### Documentation Build Fails
- Check mdBook installation
- Verify markdown syntax
- Check for broken links

### GitHub Pages Deployment Issues
- Verify repository permissions
- Check GitHub Pages settings
- Review workflow logs for specific errors