# Bundled SVN CLI for MK Workbench

MK Workbench's XOCD publish workflow uses the Subversion command-line client for unattended cleanup, update, add, commit, and validation.

## Distribution model

The Windows EXE build prepares and embeds the x64 SlikSVN command-line client:

- SlikSVN version: **1.14.5**
- Subversion version: **1.14.5**
- Source archive: https://sliksvn.com/pub/Slik-Subversion-1.14.5-x64.zip
- SHA-256: `77D4FE02999DDA3BDC3A20E86243AE6EDE99AAF072B4C12B0CDEDB54D88E954A`
- License: Apache License 2.0 for Apache Subversion

SlikSVN's documentation states that its Windows client is a standalone command-line client and that it can be embedded in a product provided the Apache License 2.0 terms are followed.

The build process downloads the archive only when the local `tools/svn/bin/svn.exe` runtime is missing, verifies the SHA-256 checksum, and includes the complete SVN `bin` directory in the PyInstaller one-file executable.

The SVN runtime is intentionally excluded from Git by `.gitignore`. It is a build artifact, not application source.

## Authentication

MK Workbench does not store SVN usernames or passwords.

The bundled `svn.exe` uses Subversion's normal per-user configuration/authentication locations. Users therefore continue to use their existing SVN/TortoiseSVN authentication cache. The XOCD workflow runs SVN commands with `--non-interactive`; if valid cached authentication is unavailable, the operation fails clearly instead of opening a credential prompt.

## Resolution order

The application looks for the SVN CLI in this order:

1. `MK_WORKBENCH_SVN_EXE` environment override.
2. Bundled SVN runtime in the MK Workbench package.
3. `svn.exe` already available on PATH.
4. Standard TortoiseSVN/SlikSVN installation paths.

TortoiseSVN remains available for manual SVN administration.

## Build

From the repository root on Windows:

```powershell
.\build_phase1_test.ps1
```

The script prepares the bundled SVN runtime before running PyInstaller. The resulting one-file EXE contains the SVN CLI, so end users do not need to install the SVN command-line tools separately.

The first build downloads the SlikSVN archive. Later builds reuse the prepared runtime until its version is changed in `scripts/prepare_svn_cli.ps1`.

## Important

This bundle contains the SVN command-line runtime only. It does not contain SVN credentials, the user's SVN working copy, or the TortoiseSVN GUI.
