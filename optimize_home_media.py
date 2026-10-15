from pathlib import Path
from shutil import copy2
from PIL import Image, ImageOps

ROOT = Path("/home/hhycode/yayinevim")
BACKUP = ROOT / "media_optimization_backup_20260521"
TARGET_DIRS = [ROOT / "media" / "blog", ROOT / "media" / "kitaplar", ROOT / "media" / "anasayfa"]
EXTS = {".jpg", ".jpeg", ".png"}
MIN_BYTES = 700 * 1024
MAX_DIMENSION = 1600
JPEG_QUALITY = 82


def optimize_image(path: Path) -> tuple[int, int, bool]:
    before = path.stat().st_size
    suffix = path.suffix.lower()
    rel = path.relative_to(ROOT)
    backup_path = BACKUP / rel
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if not backup_path.exists():
        copy2(path, backup_path)

    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        has_alpha = img.mode in ("RGBA", "LA") or ("transparency" in img.info)
        width, height = img.size
        largest = max(width, height)
        if largest > MAX_DIMENSION:
            ratio = MAX_DIMENSION / largest
            new_size = (round(width * ratio), round(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        tmp = path.with_suffix(path.suffix + ".tmp")
        if suffix in {".jpg", ".jpeg"}:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.save(tmp, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        elif suffix == ".png":
            if has_alpha:
                img.save(tmp, format="PNG", optimize=True, compress_level=9)
            else:
                if img.mode not in ("RGB", "L", "P"):
                    img = img.convert("RGB")
                img.save(tmp, format="PNG", optimize=True, compress_level=9)
        else:
            return before, before, False

    after = tmp.stat().st_size
    if after < before:
        tmp.replace(path)
        return before, after, True
    tmp.unlink(missing_ok=True)
    return before, before, False


def main() -> None:
    changed = []
    skipped = 0
    for directory in TARGET_DIRS:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in EXTS:
                continue
            if path.stat().st_size < MIN_BYTES:
                skipped += 1
                continue
            try:
                before, after, did_change = optimize_image(path)
            except Exception as exc:
                print(f"ERROR {path.relative_to(ROOT)} {exc}")
                continue
            if did_change:
                changed.append((before, after, path.relative_to(ROOT)))

    total_before = sum(item[0] for item in changed)
    total_after = sum(item[1] for item in changed)
    print(f"changed={len(changed)} skipped_small={skipped}")
    print(f"saved_bytes={total_before - total_after}")
    for before, after, rel in sorted(changed, reverse=True)[:80]:
        pct = 100 - (after / before * 100)
        print(f"{before:9d} -> {after:9d}  {pct:5.1f}%  {rel}")


if __name__ == "__main__":
    main()
