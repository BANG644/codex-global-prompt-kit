# Source and License Notes

This kit intentionally mixes a user-specific configuration snapshot with selected third-party skills. It does not claim one license for all files. Keep this notice and the licenses shipped with individual materials when copying the kit.

| Material | Source and handling |
|---|---|
| Global `AGENTS.md`, `RTK.md`, and locally maintained skills | Exact local copies included at the user's direction for this public synchronization package. Their original folders did not provide a uniform license or upstream provenance; this kit does not assign a new license. |
| `html-effectiveness` | Exact local copy of `ThariqS/html-effectiveness` at commit `1787245d94aa680edf18b52027e3f859032776ba`. The included upstream `LICENSE` declares Apache-2.0 and must be retained. Its `.git` history is excluded. |
| `karpathy-guidelines` | The local skill declares `license: MIT` and cites Andrej Karpathy's observations. No upstream repository or copyright holder was recorded in the installed folder, so this kit does not invent one. |
| Ponytail plugin | Not vendored. The installer uses Codex's native marketplace workflow to fetch `DietrichGebert/ponytail` at commit `9b58c1ffb790c075ca32e70a89cf1d80588f4abf`; the upstream plugin manifest reports version `5.1.0` and MIT. |

The image-generation skill contains variable names and secret-file lookup instructions only. No API key, `.env` file, local `.local` directory, machine configuration, plugin cache, or account credential is included.
