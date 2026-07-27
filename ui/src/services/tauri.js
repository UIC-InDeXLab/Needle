// Helpers for running inside the Tauri desktop shell.
// Gracefully degrade to browser behaviour when not running under Tauri.

export const isTauri = () =>
  typeof window !== 'undefined' && Boolean(window.__TAURI_INTERNALS__ || window.__TAURI__);

/**
 * Open a native folder picker and return the selected absolute path,
 * or null if the user cancelled. Returns null when not running in Tauri.
 */
export const pickDirectory = async (title = 'Select a folder to index') => {
  if (!isTauri()) return null;
  try {
    const { open } = await import('@tauri-apps/plugin-dialog');
    const selected = await open({
      directory: true,
      multiple: false,
      title,
    });
    if (!selected) return null;
    return Array.isArray(selected) ? selected[0] : selected;
  } catch (err) {
    console.error('Native directory picker failed:', err);
    return null;
  }
};
