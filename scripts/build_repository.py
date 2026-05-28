#!/usr/bin/env python3
import hashlib
import re
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADDONS = [
    "plugin.video.nikod.programfeed",
    "repository.nikod.programfeed",
]


def addon_version(addon_dir: Path) -> str:
    text = (addon_dir / "addon.xml").read_text(encoding="utf-8")
    match = re.search(r"<addon\b[^>]*\bversion=\"([^\"]+)\"", text)
    if not match:
        raise RuntimeError(f"Missing version in {addon_dir / 'addon.xml'}")
    return match.group(1)


def zip_addon(addon_id: str, version: str) -> Path:
    addon_dir = ROOT / addon_id
    zip_dir = ROOT / "zips" / addon_id
    zip_dir.mkdir(parents=True, exist_ok=True)
    zip_path = zip_dir / f"{addon_id}-{version}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(addon_dir.rglob("*")):
            if path.is_dir() or "__pycache__" in path.parts:
                continue
            archive.write(path, path.relative_to(ROOT))
    return zip_path


def build_addons_xml() -> str:
    addon_xml_parts = []
    for addon_id in ADDONS:
        addon_dir = ROOT / addon_id
        xml = (addon_dir / "addon.xml").read_text(encoding="utf-8").strip()
        xml = re.sub(r"^<\?xml[^>]*>\s*", "", xml)
        addon_xml_parts.append(xml)
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<addons>\n" + "\n".join(addon_xml_parts) + "\n</addons>\n"


def main() -> None:
    zips_root = ROOT / "zips"
    if zips_root.exists():
        shutil.rmtree(zips_root)
    zips_root.mkdir(parents=True)

    for addon_id in ADDONS:
        version = addon_version(ROOT / addon_id)
        zip_path = zip_addon(addon_id, version)
        print(f"built {zip_path.relative_to(ROOT)}")

    addons_xml = build_addons_xml()
    addons_xml_path = ROOT / "addons.xml"
    addons_xml_path.write_text(addons_xml, encoding="utf-8")
    checksum = hashlib.md5(addons_xml.encode("utf-8")).hexdigest()
    (ROOT / "addons.xml.md5").write_text(checksum, encoding="utf-8")
    print("built addons.xml")
    print("built addons.xml.md5")


if __name__ == "__main__":
    main()
