#!/usr/bin/env python3
"""把 web 插件打成盒子能装的 .zip 包。

用法：
    python3 package.py                      # 输出 <id>-<version>.zip
    python3 package.py -o dist/web.zip      # 指定输出

它做的事：
1. 读 plugin.manifest.json；
2. 把 extra/ 目录里的文件（图标、说明、示例数据……）逐条算 sha256 写进 files[]；
3. 用 ECDSA P-256 私钥（signing/plugin-ec.pem，没有就现生成）签清单；
4. 打包成 zip：dzhz.plugin.json + dzhz.plugin.sig + extra 里的文件。

私钥必须留着：盒子按 TOFU 记住第一包的签名者，更新时换了钥匙会被拒。
"""
import argparse
import base64
import hashlib
import json
import pathlib
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
SIGNING_DIR = ROOT / "signing"
DEFAULT_KEY = SIGNING_DIR / "plugin-ec.pem"
MANIFEST_FILE = ROOT / "plugin.manifest.json"
EXTRA_DIR = ROOT / "extra"


def openssl(*args, stdin=None):
    return subprocess.run(["openssl", *args], input=stdin, capture_output=True, check=True).stdout


def ensure_key(path: pathlib.Path) -> None:
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    openssl("ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(path))
    print(f"生成了新的签名私钥：{path}\n（一定要留着，丢了就没法给这个插件发更新）", file=sys.stderr)


def public_key_b64(key: pathlib.Path) -> str:
    der = openssl("ec", "-in", str(key), "-pubout", "-outform", "DER")
    return base64.b64encode(der).decode()


def main() -> None:
    parser = argparse.ArgumentParser(description="打 .zip 插件包")
    parser.add_argument("-o", "--out", type=pathlib.Path, help="输出路径，默认 <id>-<version>.zip")
    parser.add_argument("-k", "--key", type=pathlib.Path, default=DEFAULT_KEY, help="签名私钥（P-256）")
    parser.add_argument("--manifest", type=pathlib.Path, default=MANIFEST_FILE, help="清单模板")
    parser.add_argument("-v", "--version", help="覆盖清单里的 version")
    parser.add_argument("-c", "--version-code", type=int, help="覆盖清单里的 versionCode")
    args = parser.parse_args()

    if not args.manifest.is_file():
        sys.exit(f"找不到清单：{args.manifest}")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    ensure_key(args.key)

    if args.version:
        manifest["version"] = args.version
    if args.version_code is not None:
        manifest["versionCode"] = args.version_code

    # 随包文件：extra/ 里有什么就带什么
    files: list[dict] = []
    extras: list[tuple[str, bytes]] = []
    if EXTRA_DIR.is_dir():
        for local_path in sorted(EXTRA_DIR.rglob("*")):
            if not local_path.is_file():
                continue
            name = local_path.relative_to(EXTRA_DIR).as_posix()
            if name.startswith("."):
                continue
            data = local_path.read_bytes()
            files.append({"path": name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
            extras.append((name, data))

    manifest["files"] = files
    manifest["pubkey"] = public_key_b64(args.key)

    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    signature = openssl("dgst", "-sha256", "-sign", str(args.key), stdin=manifest_bytes)

    out = args.out or ROOT / f"{manifest['id']}-{manifest['version']}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("dzhz.plugin.json", manifest_bytes)
        z.writestr("dzhz.plugin.sig", base64.b64encode(signature))
        for name, data in extras:
            z.writestr(name, data)

    print(f"打好：{out}（{out.stat().st_size} 字节）")
    print(f"  {manifest['id']} v{manifest['version']}（versionCode {manifest['versionCode']}）")
    print(f"  随包文件 {len(files)} 个")


if __name__ == "__main__":
    main()
