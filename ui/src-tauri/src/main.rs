// Prevents an additional console window on Windows in release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use tauri::{Manager, RunEvent, State};

/// Holds the spawned backend child so we can terminate it on exit.
#[derive(Default)]
struct BackendProcess(Mutex<Option<Child>>);

/// Best-effort: kill any leftover backend from a previous run so we don't stack
/// duplicate processes (e.g. after a crash or a package reinstall).
fn kill_stale_backend() {
    let _ = Command::new("pkill").args(["-x", "needle-backend"]).status();
}

fn main() {
    // WebKitGTK on some GPU/driver combinations (e.g. newer Mesa on Fedora) fails
    // to create an EGL display and renders a blank window. Disabling the DMABUF
    // renderer and hardware compositing avoids this. Users can override by
    // presetting these variables.
    if std::env::var_os("WEBKIT_DISABLE_DMABUF_RENDERER").is_none() {
        std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
    }
    if std::env::var_os("WEBKIT_DISABLE_COMPOSITING_MODE").is_none() {
        std::env::set_var("WEBKIT_DISABLE_COMPOSITING_MODE", "1");
    }

    kill_stale_backend();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendProcess::default())
        .setup(|app| {
            // Per-user data directory for SQLite + LanceDB + credentials.
            let data_dir = app
                .path()
                .app_data_dir()
                .expect("failed to resolve app data dir");
            std::fs::create_dir_all(&data_dir).ok();

            // Bundled config + backend live under <resource_dir>/resources/.
            let resource_dir = app
                .path()
                .resource_dir()
                .expect("failed to resolve resource dir");
            let config_dir = resource_dir.join("resources");
            let backend_exe = config_dir.join("backend").join("needle-backend").join("needle-backend");

            // Ensure the backend executable is runnable (perms may be lost by bundlers).
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                if let Ok(meta) = std::fs::metadata(&backend_exe) {
                    let mut perms = meta.permissions();
                    perms.set_mode(0o755);
                    let _ = std::fs::set_permissions(&backend_exe, perms);
                }
            }

            let mut cmd = Command::new(&backend_exe);
            cmd.env("NEEDLE_DATA_DIR", data_dir.to_string_lossy().to_string())
                .env("SERVICE__CONFIG_DIR_PATH", config_dir.to_string_lossy().to_string())
                .stdout(Stdio::inherit())
                .stderr(Stdio::inherit());

            // On Linux, ask the kernel to kill the backend if this app process dies
            // for any reason (including a crash), so it can never be orphaned.
            #[cfg(target_os = "linux")]
            unsafe {
                use std::os::unix::process::CommandExt;
                cmd.pre_exec(|| {
                    libc::prctl(libc::PR_SET_PDEATHSIG, libc::SIGKILL as libc::c_ulong);
                    Ok(())
                });
            }

            match cmd.spawn() {
                Ok(child) => {
                    let state: State<BackendProcess> = app.state();
                    *state.0.lock().unwrap() = Some(child);
                }
                Err(e) => {
                    eprintln!("[needle] failed to start backend at {:?}: {}", backend_exe, e);
                }
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Needle")
        .run(|app_handle, event| {
            // Ensure the backend is terminated when the app exits.
            if let RunEvent::ExitRequested { .. } | RunEvent::Exit = event {
                let state: State<BackendProcess> = app_handle.state();
                let child = state.0.lock().unwrap().take();
                if let Some(mut child) = child {
                    let _ = child.kill();
                    let _ = child.wait();
                }
            }
        });
}

