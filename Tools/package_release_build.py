#!/usr/bin/env python3
# Packages a full release build that can be unzipped and you'll have your SS14 client or server.

import os
import shutil
import subprocess
import sys
import zipfile
import argparse

from typing import List, Optional

try:
    from colorama import init, Fore, Style
    init()

except ImportError:
    # Just give an empty string for everything, no colored logging.
    class ColorDummy(object):
        def __getattr__(self, name):
            return ""

    Fore = ColorDummy()
    Style = ColorDummy()


p = os.path.join

PLATFORM_WINDOWS = "windows"
PLATFORM_LINUX = "linux"
PLATFORM_MACOS = "mac"

SHARED_IGNORED_RESOURCES = {
    "ss13model.7z",
    "ResourcePack.zip",
    "buildResourcePack.py",
    "CONTENT_GOES_HERE",
    ".gitignore"
}
CLIENT_IGNORED_RESOURCES = {
    "Maps",
    "emotes.xml",
    "Groups"
}
SERVER_IGNORED_RESOURCES = {
    "Textures",
    "Fonts",
    "Audio",
    "Scenes",
    "Nano",
    "Shaders",
}

LAUNCHER_RESOURCES = {
    "Nano",
    "Fonts",
}

WINDOWS_NATIVES = {
    "freetype6.dll",
    "openal32.dll",
    "swnfd.dll",
    "glfw3.dll"
}

LINUX_NATIVES = {
    "libglfw.so.3",
    "libswnfd.so"
}

MAC_NATIVES = {
    "libglfw.3.dylib",
    "libswnfd.dylib"
}

SERVER_EXTRA_CONTENT_ASSEMBLIES = [
    "Dapper.dll"
]

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Packages the SS14 content repo for release on all platforms.")
    parser.add_argument("--platform",
                        "-p",
                        action="store",
                        choices=[PLATFORM_WINDOWS, PLATFORM_MACOS, PLATFORM_LINUX],
                        nargs="*",
                        help="Which platform to build for. If not provided, all platforms will be built")

    args = parser.parse_args()
    platforms = args.platform
    if not platforms:
        platforms = [PLATFORM_WINDOWS, PLATFORM_MACOS, PLATFORM_LINUX]

    if os.path.exists("release"):
        print(Fore.BLUE + Style.DIM +
              "Cleaning old release packages (release/)..." + Style.RESET_ALL)
        shutil.rmtree("release")

    os.mkdir("release")

    if PLATFORM_WINDOWS in platforms:
        wipe_bin()
        build_windows()

    if PLATFORM_LINUX in platforms:
        wipe_bin()
        build_linux()

    if PLATFORM_MACOS in platforms:
        wipe_bin()
        build_macos()


def wipe_bin():
    print(Fore.BLUE + Style.DIM +
          "Clearing old build artifacts (if any)..." + Style.RESET_ALL)
    if os.path.exists(p("RobustToolbox", "bin")):
        shutil.rmtree(p("RobustToolbox", "bin"))

    if os.path.exists("bin"):
        shutil.rmtree("bin")


def build_windows():  # type: () -> None
    # Run a full build.
    print(Fore.GREEN + "Building project for Windows x64..." + Style.RESET_ALL)

    subprocess.run([
        "dotnet",
        "build",
        "SpaceStation14.sln",
        "-c", "Release",
        "--nologo",
        "/v:m",
        "/p:TargetOS=Windows",
        "/t:Rebuild",
        "/p:FullRelease=True"
    ], check=True)

    publish_client_server("win-x64", "Windows")

    print(Fore.GREEN + "Packaging Windows x64 client..." + Style.RESET_ALL)

    client_zip = zipfile.ZipFile(
        p("release", "SS14.Client_Windows_x64.zip"), "w",
        compression=zipfile.ZIP_DEFLATED)

    copy_dir_into_zip(p("RobustToolbox", "bin", "Client", "win-x64", "publish"), "", client_zip)
    copy_client_natives(WINDOWS_NATIVES, client_zip, "")
    copy_resources("Resources", client_zip, server=False)
    copy_content_assemblies(p("Resources", "Assemblies"), client_zip, server=False)
    # Cool we're done.
    client_zip.close()

    print(Fore.GREEN + "Packaging Windows x64 server..." + Style.RESET_ALL)
    server_zip = zipfile.ZipFile(p("release", "SS14.Server_Windows_x64.zip"), "w",
                                 compression=zipfile.ZIP_DEFLATED)
    copy_dir_into_zip(p("RobustToolbox", "bin", "Server", "win-x64", "publish"), "", server_zip)
    copy_resources(p("Resources"), server_zip, server=True)
    copy_content_assemblies(p("Resources", "Assemblies"), server_zip, server=True)
    server_zip.close()

def build_macos() -> None:
    print(Fore.GREEN + "Building project for macOS x64..." + Style.RESET_ALL)

    subprocess.run([
        "dotnet",
        "build",
        "SpaceStation14.sln",
        "-c", "Release",
        "--nologo",
        "/v:m",
        "/p:TargetOS=MacOS",
        "/t:Rebuild",
        "/p:FullRelease=True"
    ], check=True)

    publish_client_server("osx-x64", "MacOS")

    print(Fore.GREEN + "Packaging macOS x64 client..." + Style.RESET_ALL)
    # Client has to go in an app bundle.
    client_zip = zipfile.ZipFile(p("release", "SS14.Client_macOS_x64.zip"), "a",
                                 compression=zipfile.ZIP_DEFLATED)

    contents = p("Space Station 14.app", "Contents", "Resources")
    copy_dir_into_zip(p("BuildFiles", "Mac", "Space Station 14.app"), "Space Station 14.app", client_zip)
    copy_dir_into_zip(p("RobustToolbox", "bin", "Client", "osx-x64", "publish"), contents, client_zip)
    copy_client_natives(MAC_NATIVES, client_zip, contents)
    copy_resources(p(contents, "Resources"), client_zip, server=False)
    copy_content_assemblies(p(contents, "Resources", "Assemblies"), client_zip, server=False)
    client_zip.close()

    print(Fore.GREEN + "Packaging macOS x64 server..." + Style.RESET_ALL)
    server_zip = zipfile.ZipFile(p("release", "SS14.Server_macOS_x64.zip"), "w",
                                 compression=zipfile.ZIP_DEFLATED)
    copy_dir_into_zip(p("RobustToolbox", "bin", "Server", "osx-x64", "publish"), "", server_zip)
    copy_resources(p("Resources"), server_zip, server=True)
    copy_content_assemblies(p("Resources", "Assemblies"), server_zip, server=True)
    server_zip.close()


def build_linux() -> None:
    # Run a full build.
    print(Fore.GREEN + "Building project for Linux x64..." + Style.RESET_ALL)

    subprocess.run([
        "dotnet",
        "build",
        "SpaceStation14.sln",
        "-c", "Release",
        "--nologo",
        "/v:m",
        "/p:TargetOS=Linux",
        "/t:Rebuild",
        "/p:FullRelease=True"
    ], check=True)

    publish_client_server("linux-x64", "Linux")

    print(Fore.GREEN + "Packaging Linux x64 client..." + Style.RESET_ALL)

    client_zip = zipfile.ZipFile(
        p("release", "SS14.Client_Linux_x64.zip"), "w",
        compression=zipfile.ZIP_DEFLATED)

    copy_dir_into_zip(p("RobustToolbox", "bin", "Client", "linux-x64", "publish"), "", client_zip)
    copy_resources("Resources", client_zip, server=False)
    copy_client_natives(LINUX_NATIVES, client_zip, "")
    copy_content_assemblies(p("Resources", "Assemblies"), client_zip, server=False)
    # Cool we're done.
    client_zip.close()

    print(Fore.GREEN + "Packaging Linux x64 server..." + Style.RESET_ALL)
    server_zip = zipfile.ZipFile(p("release", "SS14.Server_Linux_x64.zip"), "w",
                                 compression=zipfile.ZIP_DEFLATED)
    copy_dir_into_zip(p("RobustToolbox", "bin", "Server", "linux-x64", "publish"), "", server_zip)
    copy_resources(p("Resources"), server_zip, server=True)
    copy_content_assemblies(p("Resources", "Assemblies"), server_zip, server=True)
    server_zip.close()

def publish_client_server(runtime: str, target_os: str) -> None:
    # Runs dotnet publish on client and server.
    base = [
        "dotnet", "publish",
        "--runtime", runtime,
        "--no-self-contained",
        "-c", "Release",
        f"/p:TargetOS={str}",
        "/p:FullRelease=True",
    ]

    subprocess.run(base + ["RobustToolbox/Robust.Client/Robust.Client.csproj"], check=True)
    subprocess.run(base + ["RobustToolbox/Robust.Server/Robust.Server.csproj"], check=True)

def copy_resources(target, zipf, server):
    # Content repo goes FIRST so that it won't override engine files as that's forbidden.
    ignore_set = SHARED_IGNORED_RESOURCES
    if server:
        ignore_set = ignore_set.union(SERVER_IGNORED_RESOURCES)
    else:
        ignore_set = ignore_set.union(CLIENT_IGNORED_RESOURCES)

    do_resource_copy(target, "Resources", zipf, ignore_set)
    do_resource_copy(target, p("RobustToolbox", "Resources"), zipf, ignore_set)


def copy_launcher_resources(target, zipf):
    # Copy all engine resources, since those are stripped down enough now.
    do_resource_copy(target, p("RobustToolbox", "Resources"), zipf, SHARED_IGNORED_RESOURCES)
    for folder in LAUNCHER_RESOURCES:
        copy_dir_into_zip(p("Resources", folder), p(target, folder), zipf)


def do_resource_copy(target, source, zipf, ignore_set):
    for filename in os.listdir(source):
        if filename in ignore_set:
            continue

        path = p(source, filename)
        target_path = p(target, filename)
        if os.path.isdir(path):
            copy_dir_into_zip(path, target_path, zipf)

        else:
            zipf.write(path, target_path)


def zip_entry_exists(zipf, name):
    try:
        # Trick ZipInfo into sanitizing the name for us so this awful module stops spewing warnings.
        zinfo = zipfile.ZipInfo.from_file("Resources", name)
        zipf.getinfo(zinfo.filename)
    except KeyError:
        return False
    return True


def copy_dir_into_zip(directory, basepath, zipf):
    if basepath and not zip_entry_exists(zipf, basepath):
        zipf.write(directory, basepath)

    for root, _, files in os.walk(directory):
        relpath = os.path.relpath(root, directory)
        if relpath != "." and not zip_entry_exists(zipf, p(basepath, relpath)):
            zipf.write(root, p(basepath, relpath))

        for filename in files:
            zippath = p(basepath, relpath, filename)
            filepath = p(root, filename)

            message = "{dim}{diskroot}{sep}{zipfile}{dim} -> {ziproot}{sep}{zipfile}".format(
                sep=os.sep + Style.NORMAL,
                dim=Style.DIM,
                diskroot=directory,
                ziproot=zipf.filename,
                zipfile=os.path.normpath(zippath))

            print(Fore.CYAN + message + Style.RESET_ALL)
            zipf.write(filepath, zippath)


def copy_content_assemblies(target, zipf, server):
    if server:
        source_dir = p("bin", "Content.Server")
        files = ["Content.Shared.dll", "Content.Server.dll"] + SERVER_EXTRA_CONTENT_ASSEMBLIES
    else:
        source_dir = p("bin", "Content.Client")
        files = ["Content.Shared.dll", "Content.Client.dll"]

    # Write assemblies dir if necessary.
    if not zip_entry_exists(zipf, target):
        zipf.write(".", target)

    for x in files:
        zipf.write(p(source_dir, x), p(target, x))


def copy_dir_or_file(src: str, dst: str):
    """
    Just something from src to dst. If src is a dir it gets copied recursively.
    """

    if os.path.isfile(src):
        shutil.copy2(src, dst)

    elif os.path.isdir(src):
        shutil.copytree(src, dst)

    else:
        raise IOError("{} is neither file nor directory. Can't copy.".format(src))

def copy_client_natives(fileNames: List[str], zipf: zipfile.ZipFile, zipPath: str):
    for fileName in fileNames:
        zipf.write(p("RobustToolbox", "bin", "Client", fileName), p(zipPath, fileName))
        print(f"writing native {fileName}")

if __name__ == '__main__':
    main()
