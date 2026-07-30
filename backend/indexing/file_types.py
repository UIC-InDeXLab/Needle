"""Shared helpers for discovering image files on disk.

The extension list and directory-walking logic used to be duplicated across the
indexing service, the consistency checker and the filesystem watcher, and the
copies had drifted apart (different tuples of extensions). Keeping them here
means a directory scan and a watcher event always agree on what counts as an
image.
"""

import os
from typing import Iterator, Set

from settings import settings

#: Extensions Pillow can decode and that the embedders are happy with.
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff")


def is_image(path: str) -> bool:
    return path.lower().endswith(IMAGE_EXTENSIONS)


def iter_image_paths(root: str, recursive: bool = None) -> Iterator[str]:
    """Yield image paths under ``root``.

    Symlinked directories are not followed: they can point back into the tree
    and would index the same file twice (or loop forever).
    """
    if recursive is None:
        recursive = settings.directory.recursive_indexing
    try:
        entries = list(os.scandir(root))
    except OSError:
        return
    for entry in entries:
        try:
            if entry.is_file(follow_symlinks=False):
                if is_image(entry.name):
                    yield entry.path
            elif recursive and entry.is_dir(follow_symlinks=False):
                yield from iter_image_paths(entry.path, recursive)
        except OSError:
            continue


def scan_image_paths(root: str, recursive: bool = None) -> Set[str]:
    """All image paths under ``root`` as a set, for diffing against the DB."""
    return set(iter_image_paths(root, recursive))
