import wx
import logging
import threading
import webbrowser
import locale

from pathlib import Path

from resources.wx_gui import (
    gui_main_menu,
    gui_support,
    gui_download,
    gui_macos_installer_flash
)
from resources import (
    constants,
    macos_installer_handler,
    utilities,
    network_handler,
    integrity_verification
)
from data import os_data, smbios_data, cpu_data


class macOSInstallerDownloadFrame(wx.Frame):
    """
    Create a frame for downloading and creating macOS installers
    Uses a Modal Dialog for smoother transition from other frames
    Note: Flashing installers is passed to gui_macos_installer_flash.py
    """
    def __init__(self, parent: wx.Frame, title: str, global_constants: constants.Constants, screen_location: tuple = None):
        logging.info("Initializing macOS Installer Download Frame")
        self.constants: constants.Constants = global_constants
        self.title: str = title
        self.parent: wx.Frame = parent

        self.available_installers = None
        self.available_installers_latest = None

        self.catalog_seed: macos_installer_handler.SeedType = macos_installer_handler.SeedType.DeveloperSeed

        self.frame_modal = wx.Dialog(parent, title=title, size=(330, 200))

        self._generate_elements(self.frame_modal)
        self.frame_modal.ShowWindowModal()


    def _generate_elements(self, frame: wx.Frame = None) -> None:
        """
        Format:
        - Title:  Create macOS Installer
        - Button: Download macOS Installer
        - Button: Use existing macOS Installer
        - Button: Return to Main Menu
        """

        frame = self if not frame else frame

        title_label = wx.StaticText(frame, label="Create macOS Installer", pos=(-1,5))
        title_label.SetFont(wx.Font(19, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, ".AppleSystemUIFont"))
        title_label.Centre(wx.HORIZONTAL)

        # Button: Download macOS Installer
        download_button = wx.Button(frame, label="Download macOS Installer", pos=(-1, title_label.GetPosition()[1] + title_label.GetSize()[1] + 5), size=(200, 30))
        download_button.Bind(wx.EVT_BUTTON, self.on_download)
        download_button.Centre(wx.HORIZONTAL)

        # Button: Use existing macOS Installer
        existing_button = wx.Button(frame, label="Use existing macOS Installer", pos=(-1, download_button.GetPosition()[1] + download_button.GetSize()[1] - 5), size=(200, 30))
        existing_button.Bind(wx.EVT_BUTTON, self.on_existing)
        existing_button.Centre(wx.HORIZONTAL)

        # Button: Return to Main Menu
        return_button = wx.Button(frame, label="Return to Main Menu", pos=(-1, existing_button.GetPosition()[1] + existing_button.GetSize()[1] + 5), size=(150, 30))
        return_button.Bind(wx.EVT_BUTTON, self.on_return)
        return_button.Centre(wx.HORIZONTAL)

        # Set size of frame
        frame.SetSize((-1, return_button.GetPosition()[1] + return_button.GetSize()[1] + 40))


    def _generate_catalog_frame(self) -> None:
        """
        Generate frame to display available installers
        """
        super(macOSInstallerDownloadFrame, self).__init__(None, title=self.title, size=(300, 200), style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        gui_support.GenerateMenubar(self, self.constants).generate()
        self.Centre()

        # Title: Pulling installer catalog
        title_label = wx.StaticText(self, label="Pulling installer catalog", pos=(-1,5))
        title_label.SetFont(wx.Font(19, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, ".AppleSystemUIFont"))
        title_label.Centre(wx.HORIZONTAL)

        # Progress bar
        progress_bar = wx.Gauge(self, range=100, pos=(-1, title_label.GetPosition()[1] + title_label.GetSize()[1] + 5), size=(250, 30))
        progress_bar.Centre(wx.HORIZONTAL)
        progress_bar_animation = gui_support.GaugePulseCallback(self.constants, progress_bar)
        progress_bar_animation.start_pulse()

        # Set size of frame
        self.SetSize((-1, progress_bar.GetPosition()[1] + progress_bar.GetSize()[1] + 40))

        self.Show()

        # Grab installer catalog
        def _fetch_installers():
            logging.info(f"Fetching installer catalog: {macos_installer_handler.SeedType(self.catalog_seed).name}")
            remote_obj = macos_installer_handler.RemoteInstallerCatalog(seed_override=self.catalog_seed)
            self.available_installers        = remote_obj.available_apps
            self.available_installers_latest = remote_obj.available_apps_latest

        thread = threading.Thread(target=_fetch_installers)
        thread.start()

        while thread.is_alive():
            wx.Yield()

        progress_bar_animation.stop_pulse()
        progress_bar.Hide()
        self._display_available_installers()


    def _display_available_installers(self, event: wx.Event = None, show_full: bool = False) -> None:
        """
        Display available installers in frame
        """
        icons = [
            [wx.Bitmap(wx.Bitmap(str(self.constants.icns_resource_path / "Generic.icns"),wx.BITMAP_TYPE_ICON).ConvertToImage().Rescale(32, 32, wx.IMAGE_QUALITY_HIGH)),wx.Bitmap(wx.Bitmap(str(self.constants.icns_resource_path / "Generic.icns"),wx.BITMAP_TYPE_ICON).ConvertToImage().Rescale(64, 64, wx.IMAGE_QUALITY_HIGH))],
            [wx.Bitmap(wx.Bitmap(str(self.constants.icns_resource_path / "BigSur.icns"),wx.BITMAP_TYPE_ICON).ConvertToImage().Rescale(32, 32, wx.IMAGE_QUALITY_HIGH)),wx.Bitmap(wx.Bitmap(str(self.constants.icns_resource_path / "BigSur.icns"),wx.BITMAP_TYPE_ICON).ConvertToImage().Rescale(64, 64, wx.IMAGE_QUALITY_HIGH))],
            [wx.Bitmap(wx.Bitmap(str(self.constants.icns_resource_path / "Monterey.icns"),wx.BITMAP_TYPE_ICON).ConvertToImage().Rescale(32, 32, wx.IMAGE_QUALITY_HIGH)),wx.Bitmap(wx.Bitmap(str(self.constants.icns_resource_path / "Monterey.icns"),wx.BITMAP_TYPE_ICON).ConvertToImage().Rescale(64, 64, wx.IMAGE_QUALITY_HIGH))],
            [wx.Bitmap(wx.Bitmap(str(self.constants.icns_resource_path / "Ventura.icns"),wx.BITMAP_TYPE_ICON).ConvertToImage().Rescale(32, 32, wx.IMAGE_QUALITY_HIGH)),wx.Bitmap(wx.Bitmap(str(self.constants.icns_resource_path / "Ventura.icns"),wx.BITMAP_TYPE_ICON).ConvertToImage().Rescale(64, 64, wx.IMAGE_QUALITY_HIGH))],
            [wx.Bitmap(wx.Bitmap(str(self.constants.icns_resource_path / "Sonoma.icns"),wx.BITMAP_TYPE_ICON).ConvertToImage().Rescale(32, 32, wx.IMAGE_QUALITY_HIGH)),wx.Bitmap(wx.Bitmap(str(self.constants.icns_resource_path / "Sonoma.icns"),wx.BITMAP_TYPE_ICON).ConvertToImage().Rescale(64, 64, wx.IMAGE_QUALITY_HIGH))]
        ]

        bundles = [wx.BitmapBundle.FromBitmaps(icon) for icon in icons]
        
        self.frame_modal.Destroy()
        self.frame_modal = wx.Dialog(self, title="Select macOS Installer", size=(460, 500))

        # Title: Select macOS Installer
        title_label = wx.StaticText(self.frame_modal, label="Select macOS Installer", pos=(-1,-1))
        title_label.SetFont(wx.Font(19, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, ".AppleSystemUIFont"))
        
        # macOS Installers list
        id = wx.NewIdRef()
        
        self.list = wx.ListCtrl(self.frame_modal, id, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER | wx.BORDER_SUNKEN)
        self.list.SetSmallImages(bundles)

        self.list.InsertColumn(0, "Version")
        self.list.InsertColumn(1, "Size")
        self.list.InsertColumn(2, "Release Date")

        installers = self.available_installers_latest if show_full is False else self.available_installers
        if show_full is False:
            self.frame_modal.SetSize((460, 370))

        if installers:
            locale.setlocale(locale.LC_TIME, '')
            logging.info(f"Available installers on SUCatalog ({'All entries' if show_full else 'Latest only'}):")
            for item in installers:
                extra = " Beta" if installers[item]['Variant'] in ["DeveloperSeed" , "PublicSeed"] else ""
                logging.info(f"- macOS {installers[item]['Version']} ({installers[item]['Build']}):\n  - Size: {utilities.human_fmt(installers[item]['Size'])}\n  - Source: {installers[item]['Source']}\n  - Variant: {installers[item]['Variant']}\n  - Link: {installers[item]['Link']}\n")
                index = self.list.InsertItem(self.list.GetItemCount(), f"macOS {installers[item]['Version']} {os_data.os_conversion.convert_kernel_to_marketing_name(int(installers[item]['Build'][:2]))}{extra} ({installers[item]['Build']})")
                if int(installers[item]['Build'][:2]) > os_data.os_data.sonoma:
                    self.list.SetItemImage(index, 0)
                else:
                    self.list.SetItemImage(index, int(installers[item]['Build'][:2])-19) # Darwin version to index conversion. i.e. Darwin 20 -> 1 -> BigSur.icns
                self.list.SetItem(index, 1, utilities.human_fmt(installers[item]['Size']))
                self.list.SetItem(index, 2, installers[item]['Date'].strftime("%x"))
                

                
        else:
            logging.error("No installers found on SUCatalog")
            wx.MessageDialog(self.frame_modal, "Failed to download Installer Catalog from Apple", "Error", wx.OK | wx.ICON_ERROR).ShowModal()

        self.list.SetColumnWidth(0, 280)
        self.list.SetColumnWidth(1, 55)
        if show_full is True:
            self.list.SetColumnWidth(2, 90)
        else:
            self.list.SetColumnWidth(2, 104) # Hack to get the highlight to fill the ListCtrl

        if show_full is False:
            self.list.Select(-1)

        self.list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_select_list)
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select_list)

        self.select_button = wx.Button(self.frame_modal, label="Download", pos=(-1, -1), size=(150, -1))
        self.select_button.SetFont(wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, ".AppleSystemUIFont"))
        self.select_button.Bind(wx.EVT_BUTTON, lambda event, installers=installers: self.on_download_installer(installers))
        self.select_button.SetToolTip("Download the selected macOS Installer.")
        self.select_button.SetDefault()
        if show_full is True:
            self.select_button.Disable()

        self.copy_button = wx.Button(self.frame_modal, label="Copy Link", pos=(-1, -1), size=(80, -1))
        self.copy_button.SetFont(wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, ".AppleSystemUIFont"))
        if show_full is True:
            self.copy_button.Disable()
        self.copy_button.SetToolTip("Copy the download link of the selected macOS Installer.")
        self.copy_button.Bind(wx.EVT_BUTTON, lambda event, installers=installers: self.on_copy_link(installers))

        return_button = wx.Button(self.frame_modal, label="Return to Main Menu", pos=(-1, -1), size=(150, -1))
        return_button.Bind(wx.EVT_BUTTON, self.on_return_to_main_menu)
        return_button.SetFont(wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, ".AppleSystemUIFont"))

        self.showolderversions_checkbox = wx.CheckBox(self.frame_modal, label="Show Older/Beta Versions", pos=(-1, -1))
        if show_full is True:
            self.showolderversions_checkbox.SetValue(True)
        self.showolderversions_checkbox.Bind(wx.EVT_CHECKBOX, lambda event: self._display_available_installers(event, self.showolderversions_checkbox.GetValue()))

        rectbox = wx.StaticBox(self.frame_modal, -1)
        rectsizer = wx.StaticBoxSizer(rectbox, wx.HORIZONTAL)
        rectsizer.Add(self.copy_button, 0, wx.EXPAND | wx.RIGHT, 5)
        rectsizer.Add(self.select_button, 0, wx.EXPAND | wx.LEFT, 5)

        checkboxsizer = wx.BoxSizer(wx.HORIZONTAL)
        checkboxsizer.Add(self.showolderversions_checkbox, 0, wx.ALIGN_CENTRE | wx.RIGHT, 5)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(10)
        sizer.Add(title_label, 0, wx.ALIGN_CENTRE | wx.ALL, 0)
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(rectsizer, 0, wx.ALIGN_CENTRE | wx.ALL, 0)
        sizer.Add(checkboxsizer, 0, wx.ALIGN_CENTRE | wx.ALL, 15)
        sizer.Add(return_button, 0, wx.ALIGN_CENTRE | wx.BOTTOM, 15)

        self.frame_modal.SetSizer(sizer)
        self.frame_modal.ShowWindowModal()

    def on_copy_link(self, installers: dict) -> None:

        selected_item = self.list.GetFirstSelected()
        if selected_item != -1:
            clipboard = wx.Clipboard.Get()

            if not clipboard.IsOpened():
                clipboard.Open()

            clipboard.SetData(wx.TextDataObject(list(installers.values())[selected_item]['Link']))

            clipboard.Close()

            wx.MessageDialog(self.frame_modal, "Download link copied to clipboard", "", wx.OK | wx.ICON_INFORMATION).ShowModal()

            
    def on_select_list(self, event):
        if self.list.GetSelectedItemCount() > 0:
            self.select_button.Enable()
            self.copy_button.Enable()  
        else:
            self.select_button.Disable()
            self.copy_button.Disable()
            
    def on_download_installer(self, installers: dict) -> None:
        """
        Download macOS installer
        """

        selected_item = self.list.GetFirstSelected()
        if selected_item != -1:

            logging.info(f"Selected macOS {list(installers.values())[selected_item]['Version']} ({list(installers.values())[selected_item]['Build']})")

            # Notify user whether their model is compatible with the selected installer
            problems = []
            model = self.constants.custom_model or self.constants.computer.real_model
            if model in smbios_data.smbios_dictionary:
                if list(installers.values())[selected_item]["OS"] >= os_data.os_data.ventura:
                    if smbios_data.smbios_dictionary[model]["CPU Generation"] <= cpu_data.CPUGen.penryn or model in ["MacPro4,1", "MacPro5,1", "Xserve3,1"]:
                        if model.startswith("MacBook"):
                            problems.append("Lack of internal Keyboard/Trackpad in macOS installer.")
                        else:
                            problems.append("Lack of internal Keyboard/Mouse in macOS installer.")

            if problems:
                logging.warning(f"Potential issues with {model} and {list(installers.values())[selected_item]['Version']} ({list(installers.values())[selected_item]['Build']}): {problems}")
                problems = "\n".join(problems)
                dlg = wx.MessageDialog(self.frame_modal, f"Your model ({model}) may not be fully supported by this installer. You may encounter the following issues:\n\n{problems}\n\nFor more information, see associated page. Otherwise, we recommend using macOS Monterey", "Potential Issues", wx.YES_NO | wx.CANCEL | wx.ICON_WARNING)
                dlg.SetYesNoCancelLabels("View Github Issue", "Download Anyways", "Cancel")
                result = dlg.ShowModal()
                if result == wx.ID_CANCEL:
                    return
                elif result == wx.ID_YES:
                    webbrowser.open("https://github.com/dortania/OpenCore-Legacy-Patcher/issues/1021")
                    return

            host_space = utilities.get_free_space()
            needed_space = list(installers.values())[selected_item]['Size'] * 2
            if host_space < needed_space:
                logging.error(f"Insufficient space to download and extract: {utilities.human_fmt(host_space)} available vs {utilities.human_fmt(needed_space)} required")
                dlg = wx.MessageDialog(self.frame_modal, f"You do not have enough free space to download and extract this installer. Please free up some space and try again\n\n{utilities.human_fmt(host_space)} available vs {utilities.human_fmt(needed_space)} required", "Insufficient Space", wx.OK | wx.ICON_WARNING)
                dlg.ShowModal()
                return

            self.frame_modal.Close()

            download_obj = network_handler.DownloadObject(list(installers.values())[selected_item]['Link'], self.constants.payload_path / "InstallAssistant.pkg")

            gui_download.DownloadFrame(
                self,
                title=self.title,
                global_constants=self.constants,
                download_obj=download_obj,
                item_name=f"macOS {list(installers.values())[selected_item]['Version']} ({list(installers.values())[selected_item]['Build']})",
            )

            if download_obj.download_complete is False:
                self.on_return_to_main_menu()
                return

            self._validate_installer(list(installers.values())[selected_item]['integrity'])


    def _validate_installer(self, chunklist_link: str) -> None:
        """
        Validate macOS installer
        """
        self.SetSize((300, 200))
        for child in self.GetChildren():
            child.Destroy()

        # Title: Validating macOS Installer
        title_label = wx.StaticText(self, label="Validating macOS Installer", pos=(-1,5))
        title_label.SetFont(wx.Font(19, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, ".AppleSystemUIFont"))
        title_label.Centre(wx.HORIZONTAL)

        # Label: Validating chunk 0 of 0
        chunk_label = wx.StaticText(self, label="Validating chunk 0 of 0", pos=(-1, title_label.GetPosition()[1] + title_label.GetSize()[1] + 5))
        chunk_label.SetFont(wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, ".AppleSystemUIFont"))
        chunk_label.Centre(wx.HORIZONTAL)

        # Progress bar
        progress_bar = wx.Gauge(self, range=100, pos=(-1, chunk_label.GetPosition()[1] + chunk_label.GetSize()[1] + 5), size=(270, 30))
        progress_bar.Centre(wx.HORIZONTAL)

        # Set size of frame
        self.SetSize((-1, progress_bar.GetPosition()[1] + progress_bar.GetSize()[1] + 40))
        self.Show()

        chunklist_stream = network_handler.NetworkUtilities().get(chunklist_link).content
        if chunklist_stream:
            logging.info("Validating macOS installer")
            utilities.disable_sleep_while_running()
            chunk_obj = integrity_verification.ChunklistVerification(self.constants.payload_path / Path("InstallAssistant.pkg"), chunklist_stream)
            if chunk_obj.chunks:
                progress_bar.SetValue(chunk_obj.current_chunk)
                progress_bar.SetRange(chunk_obj.total_chunks)

                wx.App.Get().Yield()
                chunk_obj.validate()

                while chunk_obj.status == integrity_verification.ChunklistStatus.IN_PROGRESS:
                    progress_bar.SetValue(chunk_obj.current_chunk)
                    chunk_label.SetLabel(f"Validating chunk {chunk_obj.current_chunk} of {chunk_obj.total_chunks}")
                    chunk_label.Centre(wx.HORIZONTAL)
                    wx.App.Get().Yield()

                if chunk_obj.status == integrity_verification.ChunklistStatus.FAILURE:
                    logging.error(f"Chunklist validation failed: Hash mismatch on {chunk_obj.current_chunk}")
                    wx.MessageBox(f"Chunklist validation failed: Hash mismatch on {chunk_obj.current_chunk}\n\nThis generally happens when downloading on unstable connections such as WiFi or cellular.\n\nPlease try redownloading again on a stable connection (ie. Ethernet)", "Corrupted Installer!", wx.OK | wx.ICON_ERROR)
                    self.on_return_to_main_menu()
                    return

        logging.info("macOS installer validated")

        # Extract installer
        title_label.SetLabel("Extracting macOS Installer")
        title_label.Centre(wx.HORIZONTAL)

        chunk_label.SetLabel("May take a few minutes...")
        chunk_label.Centre(wx.HORIZONTAL)

        progress_bar_animation = gui_support.GaugePulseCallback(self.constants, progress_bar)
        progress_bar_animation.start_pulse()

        # Start thread to extract installer
        self.result = False
        def extract_installer():
            self.result = macos_installer_handler.InstallerCreation().install_macOS_installer(self.constants.payload_path)

        thread = threading.Thread(target=extract_installer)
        thread.start()

        # Show frame
        self.Show()

        # Wait for thread to finish
        while thread.is_alive():
            wx.Yield()

        progress_bar_animation.stop_pulse()
        progress_bar.Hide()
        chunk_label.SetLabel("Successfully extracted macOS installer" if self.result is True else "Failed to extract macOS installer")
        chunk_label.Centre(wx.HORIZONTAL)

        # Create macOS Installer button
        create_installer_button = wx.Button(self, label="Create macOS Installer", pos=(-1, progress_bar.GetPosition()[1]), size=(170, 30))
        create_installer_button.Bind(wx.EVT_BUTTON, self.on_existing)
        create_installer_button.Centre(wx.HORIZONTAL)
        if self.result is False:
            create_installer_button.Disable()

        # Return to main menu button
        return_button = wx.Button(self, label="Return to Main Menu", pos=(-1, create_installer_button.GetPosition()[1] + create_installer_button.GetSize()[1]), size=(150, 30))
        return_button.Bind(wx.EVT_BUTTON, self.on_return_to_main_menu)
        return_button.Centre(wx.HORIZONTAL)

        # Set size of frame
        self.SetSize((-1, return_button.GetPosition()[1] + return_button.GetSize()[1] + 40))

        # Show frame
        self.Show()

        if self.result is False:
            wx.MessageBox("An error occurred while extracting the macOS installer. Could be due to a corrupted installer", "Error", wx.OK | wx.ICON_ERROR)
            return

        user_input = wx.MessageBox("Finished extracting the installer, would you like to continue and create a macOS installer?", "Create macOS Installer?", wx.YES_NO | wx.ICON_QUESTION)
        if user_input == wx.YES:
            self.on_existing()


    def on_download(self, event: wx.Event) -> None:
        """
        Display available macOS versions to download
        """
        self.frame_modal.Close()
        self.parent.Hide()
        self._generate_catalog_frame()
        self.parent.Close()


    def on_existing(self, event: wx.Event = None) -> None:
        """
        Display local macOS installers
        """
        frames = [self, self.frame_modal, self.parent]
        for frame in frames:
            if frame:
                frame.Close()
        gui_macos_installer_flash.macOSInstallerFlashFrame(
            None,
            title=self.title,
            global_constants=self.constants,
            **({"screen_location": self.GetScreenPosition()} if self else {})
        )
        for frame in frames:
            if frame:
                frame.Destroy()


    def on_return(self, event: wx.Event) -> None:
        """
        Return to main menu (dismiss frame)
        """
        self.frame_modal.Close()


    def on_return_to_main_menu(self, event: wx.Event = None) -> None:
        """
        Return to main menu
        """
        if self.frame_modal:
            self.frame_modal.Hide()
        main_menu_frame = gui_main_menu.MainFrame(
            None,
            title=self.title,
            global_constants=self.constants,
            screen_location=self.GetScreenPosition()
        )
        main_menu_frame.Show()
        if self.frame_modal:
            self.frame_modal.Destroy()
        self.Destroy()