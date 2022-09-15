use std::fs;
use std::path::Path;
use tar::Archive;
use zstd;

use pyo3::prelude::*;

fn _unpack_conda(fname: &Path, dest: &Path) {
    let file = fs::File::open(&fname).unwrap();

    let mut archive = zip::ZipArchive::new(file).unwrap();

    for i in 0..archive.len() {
        let file = archive.by_index(i).unwrap();

        if (*file.name()).ends_with(".tar.zst") {
            let decoder = zstd::stream::read::Decoder::new(file).unwrap();
            let mut archive = Archive::new(decoder);
            archive.unpack(dest).unwrap();
        }
    }
}

#[pyfunction]
fn unpack_conda(fname: &str, dest: &str) -> PyResult<()> {
    let fname_path = Path::new(fname);
    let dest_path = Path::new(dest);
    _unpack_conda(fname_path, dest_path);
    Ok(())
}

/// A Python module implemented in Rust.
#[pymodule]
fn rust_conda(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(unpack_conda, m)?)?;
    Ok(())
}
