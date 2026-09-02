use serde::Serialize;
use std::{
    fs,
    path::{Component, Path, PathBuf},
};

#[derive(Serialize)]
struct ProjectFileEntry {
    name: String,
    kind: &'static str,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct ProjectSourceFile {
    name: String,
    relative_path: String,
}

fn project_directory(path: &str) -> Result<PathBuf, String> {
    let directory = PathBuf::from(path);
    if !directory.is_absolute() {
        return Err("Project directory must be an absolute path.".into());
    }
    let directory = directory
        .canonicalize()
        .map_err(|error| format!("Could not open project directory '{path}': {error}"))?;
    if !directory.is_dir() {
        return Err(format!("Project path '{path}' is not a directory."));
    }
    Ok(directory)
}

fn project_source_path(project_path: &str, relative_path: &str) -> Result<PathBuf, String> {
    let relative = Path::new(relative_path);
    if relative.is_absolute()
        || relative
            .components()
            .any(|component| !matches!(component, Component::Normal(_)))
    {
        return Err("Source file path is invalid.".into());
    }
    let is_latex = relative
        .extension()
        .and_then(|extension| extension.to_str())
        .is_some_and(|extension| extension.eq_ignore_ascii_case("tex"));
    if !is_latex {
        return Err("Only LaTeX source files can be opened here.".into());
    }

    let directory = project_directory(project_path)?;
    let source_path = directory
        .join(relative)
        .canonicalize()
        .map_err(|error| format!("Could not open source file '{relative_path}': {error}"))?;
    if !source_path.starts_with(&directory) || !source_path.is_file() {
        return Err("Source file is outside the project directory or is not a file.".into());
    }
    Ok(source_path)
}

#[tauri::command]
fn list_project_files(path: String) -> Result<Vec<ProjectFileEntry>, String> {
    let directory = project_directory(&path)?;
    let mut entries = fs::read_dir(&directory)
        .map_err(|error| {
            format!(
                "Could not read project directory '{}': {error}",
                directory.display()
            )
        })?
        .map(|entry| {
            let entry =
                entry.map_err(|error| format!("Could not read a project entry: {error}"))?;
            let file_type = entry.file_type().map_err(|error| {
                format!("Could not inspect '{}': {error}", entry.path().display())
            })?;
            Ok(ProjectFileEntry {
                name: entry.file_name().to_string_lossy().into_owned(),
                kind: if file_type.is_dir() {
                    "directory"
                } else {
                    "file"
                },
            })
        })
        .collect::<Result<Vec<_>, String>>()?;
    entries.sort_by(|first, second| {
        (first.kind != "directory", first.name.to_lowercase())
            .cmp(&(second.kind != "directory", second.name.to_lowercase()))
    });
    Ok(entries)
}

fn collect_latex_files(
    directory: &Path,
    relative_directory: &Path,
    files: &mut Vec<ProjectSourceFile>,
) -> Result<(), String> {
    let entries = fs::read_dir(directory).map_err(|error| {
        format!(
            "Could not read project directory '{}': {error}",
            directory.display()
        )
    })?;
    for entry in entries {
        let entry = entry.map_err(|error| format!("Could not read a project entry: {error}"))?;
        let name = entry.file_name().to_string_lossy().into_owned();
        let file_type = entry
            .file_type()
            .map_err(|error| format!("Could not inspect '{}': {error}", entry.path().display()))?;
        let relative_path = relative_directory.join(&name);
        if file_type.is_dir() && !file_type.is_symlink() && !name.starts_with('.') {
            collect_latex_files(&entry.path(), &relative_path, files)?;
        } else if file_type.is_file()
            && Path::new(&name)
                .extension()
                .and_then(|extension| extension.to_str())
                .is_some_and(|extension| extension.eq_ignore_ascii_case("tex"))
        {
            files.push(ProjectSourceFile {
                name,
                relative_path: relative_path.to_string_lossy().replace('\\', "/"),
            });
        }
    }
    Ok(())
}

#[tauri::command]
fn list_latex_files(path: String) -> Result<Vec<ProjectSourceFile>, String> {
    let directory = project_directory(&path)?;
    let mut files = Vec::new();
    collect_latex_files(&directory, Path::new(""), &mut files)?;
    files.sort_by_key(|file| file.relative_path.to_lowercase());
    Ok(files)
}

#[tauri::command]
fn read_project_source(path: String, relative_path: String) -> Result<String, String> {
    let source_path = project_source_path(&path, &relative_path)?;
    fs::read_to_string(&source_path).map_err(|error| {
        format!(
            "Could not read source file '{}': {error}",
            source_path.display()
        )
    })
}

#[tauri::command]
fn write_project_source(
    path: String,
    relative_path: String,
    content: String,
) -> Result<(), String> {
    let source_path = project_source_path(&path, &relative_path)?;
    fs::write(&source_path, content).map_err(|error| {
        format!(
            "Could not save source file '{}': {error}",
            source_path.display()
        )
    })
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            list_project_files,
            list_latex_files,
            read_project_source,
            write_project_source,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
