#!/usr/bin/env python3
import hashlib
import re
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES_URL = "https://theappartment.github.io/nikod-pf/"
INSTALLER_NAME = "NikodProgramFeed-installer.zip"
LEGACY_INSTALLER_NAME = "NikodProgramFeed-legacy-kodi18.zip"
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


def zip_legacy_plugin(addon_id: str) -> Path:
    addon_dir = ROOT / addon_id
    zip_path = ROOT / "zips" / LEGACY_INSTALLER_NAME
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(addon_dir.rglob("*")):
            if path.is_dir() or "__pycache__" in path.parts:
                continue
            archive_name = path.relative_to(ROOT)
            if path.name == "addon.xml" and path.parent == addon_dir:
                xml = path.read_text(encoding="utf-8")
                xml = re.sub(
                    r'(<addon\b[^>]*\bversion=")[^"]+(")',
                    r'\g<1>0.1.17\2',
                    xml,
                    count=1,
                )
                xml = re.sub(
                    r'<import addon="xbmc\.python" version="[^"]+"\s*/>',
                    '<import addon="xbmc.python" version="2.1.0"/>',
                    xml,
                    count=1,
                )
                archive.writestr(str(archive_name), xml)
            else:
                archive.write(path, archive_name)
    return zip_path


def build_addons_xml() -> str:
    addon_xml_parts = []
    for addon_id in ADDONS:
        addon_dir = ROOT / addon_id
        xml = (addon_dir / "addon.xml").read_text(encoding="utf-8").strip()
        xml = re.sub(r"^<\?xml[^>]*>\s*", "", xml)
        addon_xml_parts.append(xml)
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<addons>\n" + "\n".join(addon_xml_parts) + "\n</addons>\n"


def build_pages_site(plugin_zip: Path, legacy_zip: Path, repository_zip: Path) -> None:
    docs_root = ROOT / "docs"
    if docs_root.exists():
        shutil.rmtree(docs_root)
    docs_root.mkdir(parents=True)

    shutil.copy2(ROOT / "addons.xml", docs_root / "addons.xml")
    shutil.copy2(ROOT / "addons.xml.md5", docs_root / "addons.xml.md5")
    shutil.copytree(ROOT / "zips", docs_root / "zips")
    shutil.copy2(plugin_zip, docs_root / INSTALLER_NAME)
    shutil.copy2(legacy_zip, docs_root / LEGACY_INSTALLER_NAME)
    (docs_root / ".nojekyll").write_text("", encoding="utf-8")
    (docs_root / "index.html").write_text(
        f"""<html>
 <head>
  <title>Index of /nikod-pf</title>
 </head>
 <body>
<h1>Index of /nikod-pf</h1>
  <table>
   <tr>
       <th>
           <a href="?C=N;O=D">Name</a>
       </th>
       <th>
           <a href="?C=M;O=A">Last modified</a>
       </th>
       <th>
           <a href="?C=S;O=A">Size</a></th>
       <th>
           <a href="?C=D;O=A">Description</a>
       </th>
   </tr>
   <tr>
       <th colspan="5"><hr></th></tr>
    <tr>
        <td>
            <a href="/">Parent Directory</a>
        </td>
        <td>&nbsp;</td>
        <td align="right">  - </td><td>&nbsp;</td>
    </tr>
  <tr>
        <td>
            <a href="{INSTALLER_NAME}">{INSTALLER_NAME}</a>
        </td>
        <td align="right">2026-05-28  </td>
        <td align="right"> 6K </td><td>&nbsp;</td>
  </tr>
  <tr>
        <td>
            <a href="{LEGACY_INSTALLER_NAME}">{LEGACY_INSTALLER_NAME}</a>
        </td>
        <td align="right">2026-05-29  </td>
        <td align="right"> 6K </td><td>Kodi 18 legacy</td>
  </tr>
  <tr>
        <td>
            <a href="zips/repository.nikod.programfeed/repository.nikod.programfeed-0.1.0.zip">repository.nikod.programfeed-0.1.0.zip</a>
        </td>
        <td align="right">2026-05-28  </td>
        <td align="right"> 570 </td><td>&nbsp;</td>
  </tr>
   <tr>
       <th colspan="5"><hr></th>
   </tr>
</table>
""",
        encoding="utf-8",
    )


def main() -> None:
    zips_root = ROOT / "zips"
    if zips_root.exists():
        shutil.rmtree(zips_root)
    zips_root.mkdir(parents=True)

    plugin_zip = None
    repository_zip = None
    for addon_id in ADDONS:
        version = addon_version(ROOT / addon_id)
        zip_path = zip_addon(addon_id, version)
        if addon_id == "plugin.video.nikod.programfeed":
            plugin_zip = zip_path
        if addon_id.startswith("repository."):
            repository_zip = zip_path
        print(f"built {zip_path.relative_to(ROOT)}")

    legacy_zip = zip_legacy_plugin("plugin.video.nikod.programfeed")
    print(f"built {legacy_zip.relative_to(ROOT)}")

    addons_xml = build_addons_xml()
    addons_xml_path = ROOT / "addons.xml"
    addons_xml_path.write_text(addons_xml, encoding="utf-8")
    checksum = hashlib.md5(addons_xml.encode("utf-8")).hexdigest()
    (ROOT / "addons.xml.md5").write_text(checksum, encoding="utf-8")
    print("built addons.xml")
    print("built addons.xml.md5")
    if plugin_zip is None:
        raise RuntimeError("Missing plugin addon ZIP")
    if repository_zip is None:
        raise RuntimeError("Missing repository addon ZIP")
    build_pages_site(plugin_zip, legacy_zip, repository_zip)
    print("built docs GitHub Pages site")


if __name__ == "__main__":
    main()
