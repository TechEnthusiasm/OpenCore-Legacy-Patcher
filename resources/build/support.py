# Support files for build

from resources import constants, utilities

from pathlib import Path
import shutil, plistlib, subprocess, zipfile

class build_support:

    def __init__(self, model, versions, config):
        self.model = model
        self.constants: constants.Constants = versions
        self.config = config


    @staticmethod
    def get_item_by_kv(iterable, key, value):
        item = None
        for i in iterable:
            if i[key] == value:
                item = i
                break
        return item


    def get_kext_by_bundle_path(self, bundle_path):
        kext = self.get_item_by_kv(self.config["Kernel"]["Add"], "BundlePath", bundle_path)
        if not kext:
            print(f"- Could not find kext {bundle_path}!")
            raise IndexError
        return kext


    def get_efi_binary_by_path(self, bundle_path, entry_location, efi_type):
        efi_binary = self.get_item_by_kv(self.config[entry_location][efi_type], "Path", bundle_path)
        if not efi_binary:
            print(f"- Could not find {efi_type}: {bundle_path}!")
            raise IndexError
        return efi_binary


    def enable_kext(self, kext_name, kext_version, kext_path, check=False):
        kext = self.get_kext_by_bundle_path(kext_name)

        if callable(check) and not check():
            # Check failed
            return

        # Is the kext already enabled?
        if kext["Enabled"] is True:
            return

        print(f"- Adding {kext_name} {kext_version}")
        shutil.copy(kext_path, self.constants.kexts_path)
        kext["Enabled"] = True


    def sign_files(self):
        if self.constants.vault is False:
            return

        if utilities.check_command_line_tools() is False:
            # sign.command checks for the existence of '/usr/bin/strings' however does not verify whether it's executable
            # sign.command will continue to run and create an unbootable OpenCore.efi due to the missing strings binary
            # macOS has dummy binaries that just reroute to the actual binaries after you install Xcode's Command Line Tools
            print("- Missing Command Line tools, skipping Vault for saftey reasons")
            print("- Install via 'xcode-select --install' and rerun OCLP if you wish to vault this config")
            return

        print("- Vaulting EFI")
        subprocess.run([str(self.constants.vault_path), f"{self.constants.oc_folder}/"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


    def validate_pathing(self):
        # Verify whether all files are accounted for on-disk
        # This ensures that OpenCore won't hit a critical error and fail to boot
        print("- Validating generated config")
        if not Path(self.constants.opencore_release_folder / Path("EFI/OC/config.plist")):
            print("- OpenCore config file missing!!!")
            raise Exception("OpenCore config file missing")

        config_plist = plistlib.load(Path(self.constants.opencore_release_folder / Path("EFI/OC/config.plist")).open("rb"))

        for acpi in config_plist["ACPI"]["Add"]:
            if not Path(self.constants.opencore_release_folder / Path("EFI/OC/ACPI") / Path(acpi["Path"])).exists():
                print(f"  - Missing ACPI Table: {acpi['Path']}")
                raise Exception(f"Missing ACPI Table: {acpi['Path']}")

        for kext in config_plist["Kernel"]["Add"]:
            kext_path = Path(self.constants.opencore_release_folder / Path("EFI/OC/Kexts") / Path(kext["BundlePath"]))
            kext_binary_path = Path(kext_path / Path(kext["ExecutablePath"]))
            kext_plist_path = Path(kext_path / Path(kext["PlistPath"]))
            if not kext_path.exists():
                print(f"- Missing kext: {kext_path}")
                raise Exception(f"Missing {kext_path}")
            if not kext_binary_path.exists():
                print(f"- Missing {kext['BundlePath']}'s binary: {kext_binary_path}")
                raise Exception(f"Missing {kext_binary_path}")
            if not kext_plist_path.exists():
                print(f"- Missing {kext['BundlePath']}'s plist: {kext_plist_path}")
                raise Exception(f"Missing {kext_plist_path}")

        for tool in config_plist["Misc"]["Tools"]:
            if not Path(self.constants.opencore_release_folder / Path("EFI/OC/Tools") / Path(tool["Path"])).exists():
                print(f"  - Missing tool: {tool['Path']}")
                raise Exception(f"Missing tool: {tool['Path']}")

        for driver in config_plist["UEFI"]["Drivers"]:
            if not Path(self.constants.opencore_release_folder / Path("EFI/OC/Drivers") / Path(driver["Path"])).exists():
                print(f"  - Missing driver: {driver['Path']}")
                raise Exception(f"Missing driver: {driver['Path']}")

        # Validating local files
        # Report if they have no associated config.plist entry (i.e. they're not being used)
        for tool_files in Path(self.constants.opencore_release_folder / Path("EFI/OC/Tools")).glob("*"):
            if tool_files.name not in [x["Path"] for x in config_plist["Misc"]["Tools"]]:
                print(f"  - Missing tool from config: {tool_files.name}")
                raise Exception(f"Missing tool from config: {tool_files.name}")

        for driver_file in Path(self.constants.opencore_release_folder / Path("EFI/OC/Drivers")).glob("*"):
            if driver_file.name not in [x["Path"] for x in config_plist["UEFI"]["Drivers"]]:
                print(f"- Found extra driver: {driver_file.name}")
                raise Exception(f"Found extra driver: {driver_file.name}")


    def cleanup(self):
        print("- Cleaning up files")
        # Remove unused entries
        entries_to_clean = {
            "ACPI":   ["Add", "Delete", "Patch"],
            "Booter": ["Patch"],
            "Kernel": ["Add", "Block", "Force", "Patch"],
            "Misc":   ["Tools"],
            "UEFI":   ["Drivers"],
        }

        for entry in entries_to_clean:
            for sub_entry in entries_to_clean[entry]:
                for item in list(self.config[entry][sub_entry]):
                    if item["Enabled"] is False:
                        self.config[entry][sub_entry].remove(item)

        plistlib.dump(self.config, Path(self.constants.plist_path).open("wb"), sort_keys=True)
        for kext in self.constants.kexts_path.rglob("*.zip"):
            with zipfile.ZipFile(kext) as zip_file:
                zip_file.extractall(self.constants.kexts_path)
            kext.unlink()

        for item in self.constants.oc_folder.rglob("*.zip"):
            with zipfile.ZipFile(item) as zip_file:
                zip_file.extractall(self.constants.oc_folder)
            item.unlink()

        if not self.constants.recovery_status:
            # Crashes in RecoveryOS for unknown reason
            for i in self.constants.build_path.rglob("__MACOSX"):
                shutil.rmtree(i)

        # Remove unused plugins inside of kexts
        # Following plugins are sometimes unused as there's different variants machines need
        known_unused_plugins = [
            "AirPortBrcm4331.kext",
            "AirPortAtheros40.kext",
            "AppleAirPortBrcm43224.kext",
            "AirPortBrcm4360_Injector.kext",
            "AirPortBrcmNIC_Injector.kext"
        ]
        for kext in Path(self.constants.opencore_release_folder / Path("EFI/OC/Kexts")).glob("*.kext"):
            for plugin in Path(kext / "Contents/PlugIns/").glob("*.kext"):
                should_remove = True
                for enabled_kexts in self.config["Kernel"]["Add"]:
                    if enabled_kexts["BundlePath"].endswith(plugin.name):
                        should_remove = False
                        break
                if should_remove:
                    if plugin.name not in known_unused_plugins:
                        raise Exception(f" - Unknown plugin found: {plugin.name}")
                    shutil.rmtree(plugin)

        Path(self.constants.opencore_zip_copied).unlink()