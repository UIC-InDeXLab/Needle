# Getting Started

## Prerequisites

Needle is a self-contained desktop application. **End users do not need Docker,
PostgreSQL, or any external services** — everything (metadata via SQLite, vectors
via LanceDB, and on-device image generation) runs locally inside the app.

To **build** Needle from source you need:

- **Python 3.12+** — for the bundled backend. [Install Python](https://www.python.org/downloads/)
- **Node.js 18+** — for the UI. [Install Node.js](https://nodejs.org/)
- **Rust toolchain** — for the Tauri desktop shell. [Install Rust](https://rustup.rs/)

> **Note:** Needle is supported on **Linux**, **macOS** and **Windows**.
>
> On macOS, Needle requires **macOS 14 (Sonoma) or later** on an **Apple Silicon**
> Mac. Intel Macs are not supported: PyTorch stopped publishing macOS x86_64
> builds after 2.2, so the bundled backend cannot be built for them.
>
> On Windows, Needle requires **Windows 10 or later** (x64).

## Installation

### Option A — Download an installer (recommended)

Download the installer for your platform from the
[releases page](https://github.com/UIC-InDeXLab/Needle/releases):

- **macOS:** `Needle_x.y.z_macos_arm64.dmg` — open it and drag Needle to
  Applications, then see [Opening Needle on macOS](#opening-needle-on-macos) below.
- **Linux:** `Needle_x.y.z_linux_amd64.deb` (`sudo apt install ./Needle_*.deb`) or
  `Needle_x.y.z_linux_x86_64.rpm` (`sudo dnf install ./Needle_*.rpm`).
- **Windows:** `Needle_x.y.z_windows_x64-setup.exe` — run it, then see
  [Opening Needle on Windows](#opening-needle-on-windows) below.

Each release also ships a `.sha256` file so you can verify the download:

```bash
shasum -a 256 -c Needle_*_macos_arm64.dmg.sha256
```

### Opening Needle on macOS

The released app is **not signed with an Apple Developer ID**, because signing
and notarization require a paid Apple Developer account. The first time you open
it, macOS will refuse and show something like:

> **"Needle is damaged and can't be opened. You should move it to the Bin."**

**The app is not damaged.** That wording is what macOS shows for any app it
cannot attribute to a registered developer. When you download a file, your
browser attaches a `com.apple.quarantine` flag to it; Gatekeeper checks that
flagged apps are both signed by a known developer and notarized by Apple, and
Needle is neither.

To open it, remove the quarantine flag once:

```bash
xattr -dr com.apple.quarantine /Applications/Needle.app
```

Then launch Needle normally. You only need to do this once per install.

### Opening Needle on Windows

The released installer is **not code-signed**, because a signing certificate is
a paid, per-year purchase. Windows SmartScreen therefore blocks it the first
time with:

> **"Windows protected your PC"**

Click **More info**, then **Run anyway** to continue. The installer places
Needle under your user profile, so no administrator prompt is needed.

Some antivirus products also flag freshly built PyInstaller executables as
suspicious. This is a known false positive caused by the way the Python runtime
is bundled; verify the download against the published `.sha256` if in doubt, or
build from source.

> **Why not just right-click → Open?** That shortcut no longer works for
> unsigned apps on recent macOS versions. Removing the quarantine attribute (or
> approving the app under **System Settings → Privacy & Security** after a
> blocked launch attempt) is the supported route.

If you would rather not run that command, build from source instead — apps you
build locally are never quarantined, so they open with no extra steps.

### Option B — Build & install from source

```bash
git clone https://github.com/UIC-InDeXLab/Needle.git
cd Needle
./scripts/build-app.sh
```

This builds the UI, bundles the backend into the app, and produces an installer
for your platform under `ui/src-tauri/target/release/bundle/`. Apps you build
yourself are never quarantined, so they open without the warnings above.

### Accuracy profiles

Needle can trade speed for accuracy:

- **fast** (default): 2 lightweight models, quickest indexing and search.
- **balanced**: 4 models.
- **accurate**: 6 models, best results but slower and a larger download.

You pick a profile on the welcome screen at first launch, and can change it
later — though changing it means re-indexing your library.

### First launch

On first launch Needle asks you to pick an accuracy profile, then downloads the
embedding models for it (roughly 3.7 GB for **fast**) with live progress. Models
are cached in `~/.cache/huggingface`, so later launches start immediately.

![Needle's search screen after setup](media/app/search-home.png)

Once setup finishes, you're ready to
[add a folder and search it](searching.md).

> **Note:** Needle uses your GPU (CUDA) or Apple Silicon (MPS) when available.
> It is enabled by default, and you can turn it on or off later under
> **Status → Hardware acceleration**; switching reloads the models but does not
> re-download them.

## What's inside

The app runs a local backend on `127.0.0.1:8000` and starts it for you. Nothing
is exposed to the network, and no data leaves your machine.

If you want to script against it, the API is documented at
<http://127.0.0.1:8000/docs> while Needle is running.

## Next steps

- [Searching Your Images](searching.md) — add a folder and run your first query.
- [Image Generation](generating.md) — how Needle turns a query into images, and
  how to generate images yourself.
- [Status & Settings](status.md) — storage, updates and hardware acceleration.
