# Third-party notices

The project source is licensed under MIT. The components below retain their own licenses when included in the Windows bundle.

- **Bergamot translator worker** — Mozilla Public License 2.0. The vendored source files and license are in `app/data/bergamot/`; provenance and checksums are documented in that folder's README.
- **Node.js runtime** — Node.js v24.19.0. Its upstream license and bundled third-party notices are in `app/runtime/node-LICENSE.txt`; the matching version is pinned in `app/runtime/node-version.txt`.
- **Qt for Python / PySide6** — Community wheels are dual licensed under LGPLv3, GPLv2/GPLv3, or commercial terms. The release uses the open-source terms. The LGPLv3 and GPLv3 texts are in `app/licenses/`; PySide6 and dependency license files are collected into the installed bundle's `licenses/runtime/` folder. Qt and PySide6 source is available from [Qt's source downloads](https://download.qt.io/official_releases/qt/) and [the PySide source repository](https://code.qt.io/cgit/pyside/pyside-setup.git/).
- **Translation models** — model weights are not included. The app downloads selected files from the upstream URLs in `app/data/registry.json` and verifies their SHA-256 hashes.
- **Inno Setup Vietnamese translation** — the installer uses the user-contributed Vietnamese message file maintained by memecoder from the [Inno Setup source repository](https://github.com/jrsoftware/issrc/blob/main/Files/Languages/Unofficial/Vietnamese.isl). Its upstream attribution is retained in `app/installer/languages/Vietnamese.isl`.

Python runtime and package dependency license files are collected into the generated bundle's `licenses/runtime/` folder where supplied by their distributions. The Qt libraries remain separate shared libraries in the installed app folder so users can replace them with interface-compatible modified builds.
