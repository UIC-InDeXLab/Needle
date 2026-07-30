// Prevents an additional console window on Windows in release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use tauri::{Manager, RunEvent, State};

/// Spawn child processes without flashing a console window on Windows.
#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

/// Holds the spawned backend child so we can terminate it on exit.
#[derive(Default)]
struct BackendProcess(Mutex<Option<Child>>);

/// Best-effort: kill any leftover backend from a previous run so we don't stack
/// duplicate processes (e.g. after a crash or a package reinstall).
#[cfg(unix)]
fn kill_stale_backend() {
    let _ = Command::new("pkill").args(["-x", "needle-backend"]).status();
}

#[cfg(target_os = "windows")]
fn kill_stale_backend() {
    use std::os::windows::process::CommandExt;
    let _ = Command::new("taskkill")
        .args(["/F", "/IM", "needle-backend.exe"])
        .creation_flags(CREATE_NO_WINDOW)
        .status();
}

/// Windows has no `PR_SET_PDEATHSIG`. Instead the backend is placed in a job
/// object marked "kill on job close": when this process exits for any reason the
/// job handle is released and Windows terminates the backend with it. The handle
/// is deliberately held for the lifetime of the process — closing it early would
/// kill the backend immediately.
#[cfg(target_os = "windows")]
mod win_job {
    use std::process::Child;
    use std::sync::OnceLock;

    use windows_sys::Win32::Foundation::{CloseHandle, HANDLE};
    use windows_sys::Win32::System::JobObjects::{
        AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
        SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    };
    use windows_sys::Win32::System::Threading::{OpenProcess, PROCESS_SET_QUOTA, PROCESS_TERMINATE};

    // Keeps the job handle alive for the whole process lifetime.
    static JOB: OnceLock<usize> = OnceLock::new();

    pub fn attach(child: &Child) {
        unsafe {
            let job: HANDLE = CreateJobObjectW(std::ptr::null(), std::ptr::null());
            if job.is_null() {
                return;
            }
            let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            SetInformationJobObject(
                job,
                JobObjectExtendedLimitInformation,
                &info as *const _ as *const core::ffi::c_void,
                std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            );

            let handle = OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, 0, child.id());
            if !handle.is_null() {
                AssignProcessToJobObject(job, handle);
                CloseHandle(handle);
            }
            let _ = JOB.set(job as usize);
        }
    }
}

fn main() {
    // WebKitGTK on some GPU/driver combinations (e.g. newer Mesa on Fedora) fails
    // to create an EGL display and renders a blank window. Disabling the DMABUF
    // renderer and hardware compositing avoids this. Users can override by
    // presetting these variables. (Linux only: macOS uses WKWebView and Windows
    // uses WebView2, neither of which is affected.)
    #[cfg(target_os = "linux")]
    {
        if std::env::var_os("WEBKIT_DISABLE_DMABUF_RENDERER").is_none() {
            std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
        }
        if std::env::var_os("WEBKIT_DISABLE_COMPOSITING_MODE").is_none() {
            std::env::set_var("WEBKIT_DISABLE_COMPOSITING_MODE", "1");
        }
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
            let backend_name = if cfg!(target_os = "windows") {
                "needle-backend.exe"
            } else {
                "needle-backend"
            };
            let backend_exe = config_dir
                .join("backend")
                .join("needle-backend")
                .join(backend_name);

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
                // The packaged backend has no git checkout to derive a version
                // from, so hand it the bundle's version instead.
                .env("NEEDLE_APP_VERSION", app.package_info().version.to_string())
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

            // The backend is a console subsystem binary; without this Windows
            // would show a stray console window next to the app.
            #[cfg(target_os = "windows")]
            {
                use std::os::windows::process::CommandExt;
                cmd.creation_flags(CREATE_NO_WINDOW);
            }

            match cmd.spawn() {
                Ok(child) => {
                    // Tie the backend's lifetime to this process (see win_job).
                    #[cfg(target_os = "windows")]
                    win_job::attach(&child);

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

