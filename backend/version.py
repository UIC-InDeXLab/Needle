# Backend version information
import subprocess
import os
from pathlib import Path

def get_version_from_git():
    """Get version from git tags using the same logic as CI/CD."""
    try:
        # Get the directory where this file is located
        backend_dir = Path(__file__).parent
        project_root = backend_dir.parent
        
        # Change to project root directory
        original_cwd = os.getcwd()
        os.chdir(project_root)
        
        try:
            # Get the latest needlectl tag
            result = subprocess.run(
                ["git", "tag", "-l", "needlectl/v*", "--sort=-v:refname"],
                capture_output=True,
                text=True,
                check=True
            )
            tags = result.stdout.strip().split('\n')
            
            if not tags or tags == ['']:
                # No tags found, use base version
                base_version = "0.1.0"
                commit_count = subprocess.run(
                    ["git", "rev-list", "--count", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=True
                ).stdout.strip()
            else:
                # Get the latest tag
                latest_tag = tags[0]
                # Extract version number without prefix
                base_version = latest_tag.replace("needlectl/v", "")
                
                # Count commits since last tag
                commit_count = subprocess.run(
                    ["git", "rev-list", "--count", f"{latest_tag}..HEAD"],
                    capture_output=True,
                    text=True,
                    check=True
                ).stdout.strip()
            
            # Split the base version
            major, minor, patch = map(int, base_version.split('.'))
            
            # Calculate new version
            new_patch = patch + int(commit_count)
            new_version = f"{major}.{minor}.{new_patch}"
            
            return new_version
            
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
            
    except Exception as e:
        # Fallback to a default version if git fails
        return "0.1.0"

# Get version dynamically from git
VERSION = get_version_from_git()
