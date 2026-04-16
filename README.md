# 3MFresh 🧼✨
*A lightweight Python script to clean `.3MF` files by removing unnecessary metadata and other data. Designed primarily for Bambu Studio and Orca Slicer users.*

## 🔍 Why Use 3MFresh?
When downloading `.3MF` print profiles from **MakerWorld** or other sources, they often contain **metadata** that ties them to their original creator, model description, images, and other details.

This metadata can **persist even after modifying the file**, leading to confusion when using the profile for new prints. For example:
- A `.3MF` file may contain **optimized print settings for a specific filament**, but also **metadata** about the original model.
- If you **repurpose the print profile** by adding your own models, the **original metadata remains**—meaning the printer history and slicer still display **the old model's information**, rather than your custom project.

## 🚀 What It Cleans
- **`3D/3dmodel.model`** — Strips all creator metadata (designer name, title, description, cover images, etc.), keeping only the slicer application name/version and format version number, which are required for compatibility.
- **`Auxiliaries/`** — Removes the entire directory, which contains creator thumbnails, model photos, and assembly guides.
- **`_rels/.rels`** — Removes relationship entries pointing to the now-deleted Auxiliaries files. Without this step, BambuStudio v2.x will refuse to load the file entirely.
- **`Metadata/model_settings.config`** — Removes `source_file` entries, which expose local filesystem paths from whoever last saved the file.
- **`Metadata/` preview images** — Removes plate preview PNGs (plate thumbnails, top views, pick views). These are visual snapshots of the original creator's print plate and regenerate automatically the next time the file is sliced.

## 📥 Installation
1. **Clone the repository**
   ```bash
   git clone https://github.com/brossow/3MFresh.git
   cd 3MFresh
   ```
   *Alternatively, download just the `.py` file into its own directory. The `input/` directory will be created automatically on first run.*

2. **Ensure Python 3 is installed.**
   ```bash
   python3 --version
   ```

3. No additional dependencies required — stdlib only.

## 🛠 Usage
1. Place `.3MF` files into the **`input/`** directory.
2. Run the script:
   ```bash
   python3 process_3mf.py
   ```
3. Cleaned files are in a timestamped subdirectory of **`processed/`**. Original files are moved to a matching subdirectory of **`originals/`** so nothing is ever overwritten or lost.

### Options
```
-q, --quiet    Suppress per-file detail; show only errors and the final summary.
-h, --help     Show help and exit.
```

## 📌 Notes
- Always make backups.
- The script has been tested with numerous `.3MF` files from MakerWorld, but comes with **no guarantees**, **no support**, and **you use it at your own risk**.
- Compatible with files created by **BambuStudio** and **Orca Slicer**, which share the same internal `.3MF` format.
- If you encounter a problem, open a detailed issue report on GitHub.
- Always make backups.

## 🤝 Contributing
Pull requests are welcome. Please fork the repository and submit a PR.

## 📝 License
This project is licensed under the MIT License. See `LICENSE` for details.
