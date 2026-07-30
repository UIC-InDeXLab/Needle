# Command Line

Every Needle package ships `needlectl`, a command line interface to the same
backend the app uses. It is not a separate product: both read and write the same
settings, so a change made in one shows up in the other.

Use it to script indexing, run searches from a terminal, or drive Needle on a
machine you only reach over SSH.

## Getting it on PATH

**Linux** — the `.deb` and `.rpm` install it for you.

**macOS** — it ships inside the app bundle:

```sh
sudo ln -sf /Applications/Needle.app/Contents/Resources/bin/needlectl \
  /usr/local/bin/needlectl
```

**Windows** — add the app's `resources\bin` folder to your PATH:

```powershell
$dir = "$env:LOCALAPPDATA\Needle\resources\bin"
[Environment]::SetEnvironmentVariable(
  "Path", "$([Environment]::GetEnvironmentVariable('Path','User'));$dir", "User")
```

## Before you start

`needlectl` talks to the backend over HTTP, so **Needle must be running** —
either the desktop app, or a backend you started yourself.

```sh
needlectl service status
```

On a brand new install, run setup once (the same thing the welcome screen does):

```sh
needlectl service setup --profile fast
```

## Indexing folders

```sh
needlectl directory add ~/Pictures
needlectl directory list
needlectl directory describe 1

needlectl directory disable 1     # keep indexed, exclude from searches
needlectl directory enable 1
needlectl directory remove ~/Pictures
```

## Searching

```sh
needlectl query run "snow covered mountain peaks"
needlectl query run "a red bus on a city street" --n 20
needlectl --output json query run "a cat on a windowsill"
```

Searches use whichever generators are enabled, in the order set under
**Generators** in the app — the CLI does not keep its own copy.

## Generators

```sh
needlectl generator list                     # order, state, and why
needlectl generator models                   # on-device models
needlectl generator download sd-turbo        # fetch weights, with progress
needlectl generator test needle-local        # one throwaway image

needlectl generator enable needle-local
needlectl generator disable openai
needlectl generator order needle-local openai stability
needlectl generator fallback off             # use only the first enabled one
needlectl generator model sdxl-turbo

needlectl generator credentials openai       # prompts, never echoed
```

## System

```sh
needlectl service info          # version, platform, storage, library counts
needlectl service gpu on
needlectl --version
```

## Output formats

Every command takes `--output human|json|yaml`, so results can be piped:

```sh
needlectl --output json query run "a mountain lake" \
  | jq -r '.results[]'
```
