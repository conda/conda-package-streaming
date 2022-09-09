use std::fs;
// use std::io;
use tar::Archive;
use zstd;

fn main() {
    std::process::exit(real_main());
}

fn real_main() -> i32 {
    let args: Vec<_> = std::env::args().collect();
    if args.len() < 2 {
        println!("Usage: {} <filename>", args[0]);
        return 1;
    }
    let fname = std::path::Path::new(&*args[1]);
    let file = fs::File::open(&fname).unwrap();
    let dest = fname.file_stem().unwrap();

    println!("Unpack to {:?}", dest);

    let mut archive = zip::ZipArchive::new(file).unwrap();

    for i in 0..archive.len() {
        let file = archive.by_index(i).unwrap();

        if (*file.name()).ends_with(".tar.zst") {
            println!("File {}", file.name());

            let decoder = zstd::stream::read::Decoder::new(file).unwrap();
            let mut archive = Archive::new(decoder);
            archive.unpack(dest).unwrap();
        }
    }

    0
}
