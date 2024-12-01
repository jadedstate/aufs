# custom_button.py

from PyQt5.QtWidgets import QPushButton, QMenu, QAction
from PyQt5.QtGui import QFont, QMouseEvent
from PyQt5.QtCore import Qt
from lib.qtwidgets.widgets.refresh_filesystem_data import FileDataProcessor
import os

class StandardButtons(QPushButton):
    def __init__(self, text="Button", parent=None):
        super().__init__(test, parent)
        
    @staticmethod
    def defaultCancel(text="Cancel", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(100, 30)  # Fixed width and height
        button.setStyleSheet("background-color: lightcoral; color: #333333;")  # Light red background
        button.setFont(QFont("Arial", 10, QFont.Bold))  # Black Arial, 10pt, bold
        return button

    @staticmethod
    def defaultItalicsButton(text="Italics", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(100, 30)  # Fixed width and height
        button.setStyleSheet("background-color: lightgrey; color: #333333;")  # Light grey background
        button.setFont(QFont("Arial", 10, QFont.StyleItalic))  # Black Arial, 10pt, italics
        return button

    @staticmethod
    def defaultGreyButton(text="Grey", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(100, 30)  # Fixed width and height
        button.setStyleSheet("background-color: lightgrey; color: #333333;")  # Light grey background
        button.setFont(QFont("Arial", 10))  # Black Arial, 10pt, Grey
        return button

    @staticmethod
    def defaultBlueButton(text="Blue", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(100, 30)  # Fixed width and height
        button.setStyleSheet("background-color: lightblue; color: #333333;")  # Light blue background
        button.setFont(QFont("Arial", 10))  # Black Arial, 10pt, Grey
        return button

    @staticmethod
    def defaultGreenButton(text="Green", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(100, 30)  # Fixed width and height
        button.setStyleSheet("background-color: #aaeeaa; color: #333333; color: #333333;")  # Light green background
        button.setFont(QFont("Arial", 10))  # Black Arial, 10pt, Grey
        return button

    @staticmethod
    def defaultRedButton(text="Green", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(100, 30)  # Fixed width and height
        button.setStyleSheet("background-color: #eeaaaa; color: #333333;")  # Light red background
        button.setFont(QFont("Arial", 10))  # Black Arial, 10pt, Grey
        return button

    @staticmethod
    def defaultLightRedButton(text="Green", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(100, 30)  # Fixed width and height
        button.setStyleSheet("background-color: #cc8888; color: #333333;")  # Light red background
        button.setFont(QFont("Arial", 10))  # Black Arial, 10pt, Grey
        return button

    @staticmethod
    def defaultLightPurpleButton(text="Green", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(100, 30)  # Fixed width and height
        button.setStyleSheet("background-color: #cc88aa; color: #333333;")  # Light red background
        button.setFont(QFont("Arial", 10))  # Black Arial, 10pt, Grey
        return button

    @staticmethod
    def defaultYellowButton(text="Green", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(100, 30)  # Fixed width and height
        button.setStyleSheet("background-color: #eeeeaa; color: #333333;")  # Light red background
        button.setFont(QFont("Arial", 10))  # Black Arial, 10pt, Grey
        return button

    @staticmethod
    def defaultWideGreyButton(text="Grey", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(200, 30)  # Fixed width and height
        button.setStyleSheet("background-color: lightgrey; color: #333333;")  # Light grey background
        button.setFont(QFont("Arial", 10))  # Black Arial, 10pt, Grey
        return button

    @staticmethod
    def defaultWideBlueButton(text="Blue", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(200, 30)  # Fixed width and height
        button.setStyleSheet("background-color: lightblue; color: #333333;")  # Light blue background
        button.setFont(QFont("Arial", 10))  # Black Arial, 10pt, Grey
        return button

    @staticmethod
    def defaultWideGreenButton(text="Green", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(200, 30)  # Fixed width and height
        button.setStyleSheet("background-color: #aaeeaa; color: #333333;")  # Light green background
        button.setFont(QFont("Arial", 10))  # Black Arial, 10pt, Grey
        return button

    @staticmethod
    def defaultWideRedButton(text="Green", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(200, 30)  # Fixed width and height
        button.setStyleSheet("background-color: #eeaaaa; color: #333333;")  # Light red background
        button.setFont(QFont("Arial", 10))  # Black Arial, 10pt, Grey
        return button

    @staticmethod
    def defaultWideYellowButton(text="Green", parent=None):
        button = QPushButton(text, parent)
        button.setFixedSize(200, 30)  # Fixed width and height
        button.setStyleSheet("background-color: #eeeeaa; color: #333333;")  # Light red background
        button.setFont(QFont("Arial", 10))  # Black Arial, 10pt, Grey
        return button

    @staticmethod
    def defaultGreyWithRMBMenuButton(text="Grey RMB", parent=None, menu_items=None, lmb_action=None):
        button = QPushButton(text, parent)
        button.setFixedSize(100, 30)  # Standard fixed size
        button.setStyleSheet("background-color: lightgrey; color: #333333;")  # Grey background
        button.setFont(QFont("Arial", 10))  # Standard font

        # Right-click menu setup
        button.menu = QMenu(parent)
        if menu_items:
            for item_text, item_action in menu_items:
                action = QAction(item_text, button)
                action.triggered.connect(item_action)
                button.menu.addAction(action)

        button.setContextMenuPolicy(Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(lambda pos: button.menu.exec_(button.mapToGlobal(pos)))

        # Left-click action setup
        if lmb_action:
            button.clicked.connect(lmb_action)

        return button

    @staticmethod
    def defaultGreyWithLRMBMenusButton(text="Grey LRMB", parent=None, left_menu_items=None, right_menu_items=None):
        button = QPushButton(text, parent)
        button.setFixedSize(100, 30)  # Standard fixed size
        button.setStyleSheet("background-color: lightgrey; color: #333333;")  # Grey background
        button.setFont(QFont("Arial", 10))  # Standard font

        # Left-click menu setup
        button.left_menu = QMenu(parent)
        if left_menu_items:
            for item_text, item_action in left_menu_items:
                action = QAction(item_text, button)
                action.triggered.connect(item_action)
                button.left_menu.addAction(action)

        # Right-click menu setup
        button.right_menu = QMenu(parent)
        if right_menu_items:
            for item_text, item_action in right_menu_items:
                action = QAction(item_text, button)
                action.triggered.connect(item_action)
                button.right_menu.addAction(action)

        # Mouse event override to handle left and right clicks
        def mousePressEvent(event, button=button, left_menu=button.left_menu, right_menu=button.right_menu):
            if event.button() == Qt.RightButton:
                right_menu.exec_(event.globalPos())
            elif event.button() == Qt.LeftButton:
                left_menu.exec_(button.mapToGlobal(event.pos()))

        button.mousePressEvent = mousePressEvent

        return button
        
class FilesAndOrLinksUpdateButton(QPushButton):
    """
    A QPushButton subclass to update files and/or links based on the selected project.

    Requires a callback function to dynamically fetch job setup data, which should 
    be structured as follows:

    def get_job_setup_data_for_button(self):
        # Fetches job setup data based on the current UI selection.
        selected_project_item = self.project_list.currentItem()
        selected_project = selected_project_item.text() if selected_project_item else ""
        if not selected_project:
            QMessageBox.warning(self, "Error", "Set your JOB first")
            return None
        
        # Assumes self.df is a DataFrame containing project setup data.
        return self.df[self.df['PROJECT'] == selected_project].iloc[0].to_dict() if selected_project else None

    This method ensures that the button can dynamically update based on the currently 
    selected project in the UI. Pass this function as the `get_job_setup_data_callback` 
    parameter when instantiating the button.
    """

class FilesAndOrLinksUpdateButton(QPushButton):
    def __init__(self, get_job_setup_data_callback, parent=None):
        super().__init__("Files and/or Links Update", parent)
        self.get_job_setup_data = get_job_setup_data_callback
        self.setToolTip("Click for options.")
        # Directory blacklist
        self.dir_blacklist = ['IO']

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.showRMBMenu(event.globalPos())
        elif event.button() == Qt.LeftButton:
            self.showLMBMenu(event.globalPos())
        else:
            super().mousePressEvent(event)

    def showLMBMenu(self, globalPos):
        job_setup_data = self.get_job_setup_data()
        if not job_setup_data:
            print("Job setup data not available for LMB menu.")
            return

        menu = QMenu()
        # Existing actions
        updateAllAction = menu.addAction("Update all Files and Links")
        updateAllAction.triggered.connect(lambda: self.updateAll(job_setup_data))
        
        # New actions
        updateJobFilesAction = menu.addAction("Update Job Files")
        updateJobLinksAction = menu.addAction("Update Job Links")
        updateJobFilesAction.triggered.connect(lambda: self.updateAllJob(job_setup_data, 'files'))
        updateJobLinksAction.triggered.connect(lambda: self.updateAllJob(job_setup_data, 'links'))
        
        menu.exec_(globalPos)

    def showRMBMenu(self, globalPos):
        job_setup_data = self.get_job_setup_data()
        if not job_setup_data:
            print("Job setup data not available for RMB menu.")
            return

        # Main RMB menu
        menu = QMenu("Update Specific")
        
        # New functionality to dynamically create a submenu for directories in WD
        wdMenu = QMenu("Directories in WD", menu)
        working_dir_path = self.getWorkingDirectoryPath(job_setup_data)
        if os.path.isdir(working_dir_path):
            dir_names = [name for name in os.listdir(working_dir_path) 
                        if os.path.isdir(os.path.join(working_dir_path, name)) 
                        and name not in self.dir_blacklist]
            if dir_names:
                for dir_name in dir_names:
                    action = wdMenu.addAction(dir_name)
                    action.triggered.connect(lambda checked, dn=dir_name: self.updateSpecificDirectory(working_dir_path, dn))
            else:
                wdMenu.addAction("Nothing to update")
        else:
            wdMenu.addAction("Invalid working directory")
        menu.addMenu(wdMenu)
        
        menu.exec_(globalPos)

    def updateAllJob(self, job_setup_data, update_type):
        print(f"Updating all job {update_type}...")

        # Extracting root path based on the system
        system_root = self.getWorkingDirectoryPath(job_setup_data).replace("\\", "/")
        workpaths = [system_root]

        # Initialize FileDataProcessor
        fdp = FileDataProcessor(job_setup_data=job_setup_data)

        # Filter out 'IO/' directories from workpaths and proceed with the update
        workpaths_filtered = [path for path in workpaths if not any(blacklisted in path for blacklisted in self.dir_blacklist)]
        for path in workpaths_filtered:
            if update_type == 'files':
                fdp.update_fs_files_data(specific_path=path)
            elif update_type == 'links':
                fdp.update_fs_links_data(specific_path=path)

    def getWorkingDirectoryPath(self, job_setup_data):
        # Extract ROOTWIN/ROOTMAC/ROOTLINUX based on the system
        system_root = job_setup_data.get('ROOTWIN', '')  # Adjust based on actual system detection
        client = job_setup_data.get('CLIENT', '')
        project = job_setup_data.get('PROJECT', '')
        working_dir_path = os.path.join(system_root, 'jobs', client, project)
        return working_dir_path

    def updateSpecificDirectory(self, working_dir_path, dir_name):
        specific_path = os.path.join(working_dir_path, dir_name).replace("\\", "/")
        print(f"Updating specific directory: {specific_path}")

        # Initialize FileDataProcessor with the specific path
        fdp = FileDataProcessor(job_setup_data=self.get_job_setup_data(), file_path=specific_path)

        # Assuming the existence of methods to update files or links in a specific directory within FileDataProcessor
        # You might need to adjust this part to fit your actual update logic
        fdp.update_fs_files_data(specific_path)
        fdp.update_fs_links_data(specific_path)

    def updateAll(self, job_setup_data):
        print("Updating all files and links...")
        workpaths = job_setup_data.get('WORKPATHS', '').split(',')
        # Filter for paths that include '/IN/' or '/OUT/' after normalizing
        workpaths_filtered = [path.strip() for path in workpaths if path.strip() and ("/IN/" in path or "/OUT/" in path)]
        for path in workpaths_filtered:
            fdp = FileDataProcessor(job_setup_data=job_setup_data)
            fdp.refresh_all_data_for_path(path)

    def updateSpecific(self, update_type, job_setup_data):
        print(f"Updating {update_type}...")
        workpaths = job_setup_data.get('WORKPATHS', '').split(',')
        # Filter for paths that include '/IN/' or '/OUT/' after normalizing
        workpaths_filtered = [path.strip() for path in workpaths if path.strip() and ("/IN/" in path or "/OUT/" in path)]
        for path in workpaths_filtered:
            fdp = FileDataProcessor(job_setup_data=job_setup_data)
            if update_type == 'files':
                fdp.update_fs_files_data(specific_path=path)
            elif update_type == 'links':
                fdp.update_fs_links_data(specific_path=path)

class StageButton(QPushButton):
    def __init__(self, stage, shot_name, main_window, checkbox, parent=None):
        super().__init__("", parent)
        self.stage = stage
        self.shot_name = shot_name
        self.main_window = main_window
        self.checkbox = checkbox  # Assign the checkbox passed as an argument
        self.originalStyle = ""
        self.updateButtonAppearance()
        self.rv_sequences_menu = None  # Initialize the RV sequences submenu

        # Set word wrapping and maximum width
        self.setMinimumWidth(150)  # Adjust the value as needed

    def updateButtonAppearance(self):
        #print("Updating button appearance for", self.shot_name)  # Debug print

        from_dir = f"G:/jobs/primary_vfx/HF23/IO/from_manmath/mbTeam/{self.stage}/{self.shot_name}"
        to_dir = f"G:/jobs/primary_vfx/HF23/IO/to_manmath/mbTeam/{self.stage}/{self.shot_name}"

        latest_from = self.findLatestNKFile(from_dir) if os.path.exists(from_dir) else None
        latest_to = self.findLatestNKFile(to_dir) if os.path.exists(to_dir) else None

        if latest_from:
            self.setText(latest_from)
            self.setStyleSheet("background-color: lightblue;")
        elif latest_to:
            self.setText("Template")
            self.setStyleSheet("background-color: yellow;")
        else:
            self.setText("-")
            self.setStyleSheet("")  # Reset to default style
            self.setEnabled(True)

        # Store the current style as the original style after setting it
        self.originalStyle = self.styleSheet()

        # Force GUI update
        self.update()

    def populateMenuWithItems(self, menu, items, action_callback):
        """
        Populates the given menu with items, connecting each item's triggered signal to the provided callback.

        :param menu: QMenu to populate
        :param items: List of items to populate the menu with. Each item is a dictionary with relevant data.
        :param action_callback: Function to be called when an action is triggered. This function should accept 
                                a single argument that is the item associated with the action.
        """
        for item in items:
            # Assuming each 'item' in 'items' is a dictionary with 'SEQUENCE', 'FIRSTFRAME', and 'LASTFRAME'
            action_text = f"{item['SEQUENCE']} ({item['FIRSTFRAME']}-{item['LASTFRAME']})"
            action = QAction(action_text, self)
            action.triggered.connect(partial(action_callback, item))
            menu.addAction(action)

    def makeMMJpgsFromTemplate(self, seq_info):
        """
        Creates a temporary Nuke script to make JPGs from a template for a given sequence.
        
        :param seq_info: Dictionary containing 'SEQUENCE', 'FIRSTFRAME', and 'LASTFRAME'.
        """
        # Assuming you have the template path stored or passed as an argument to the class
        template_path01 = self.template_path01

        # Extract the sequence information
        sequence_formatted = seq_info['SEQUENCE']
        first_frame = seq_info['FIRSTFRAME']
        last_frame = seq_info['LASTFRAME']

        # Use the NukeIt instance to create and run the Nuke script
        nuke_it_instance = NukeIt()

        temp_script_path = nuke_it_instance.nukeReadWithFirstLastTemp(
            sequence_formatted=sequence_formatted,
            first_frame=first_frame,
            last_frame=last_frame,
            template_path01=template_path01
        )
        
        # Now run the created Nuke script
        nuke_it_instance.runNukeWithFile(temp_script_path)

    def getBaseDirectory(self, mouse_button):
        if mouse_button == Qt.RightButton:
            return f"G:/jobs/primary_vfx/HF23/IO/from_manmath/mbTeam/{self.stage}/{self.shot_name}" # Change this to env variable
        elif mouse_button == Qt.LeftButton:
            return f"G:/jobs/primary_vfx/HF23/IO/to_manmath/mbTeam/{self.stage}/{self.shot_name}" # Change this to env variable

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.showLeftClickMenu(event.pos())
        elif event.button() == Qt.RightButton:
            self.showRightClickMenu(event.pos())
        else:
            super().mousePressEvent(event)

    def showLeftClickMenu(self, position):
        menu = QMenu(self)

        if self.stage == "STAGE_1":
            # Define actions for STAGE_1
            stage_1_action = QAction("No LMB actions", self)
            stage_1_action.triggered.connect(lambda: self.performActionForStage1())
            menu.addAction(stage_1_action)
        elif self.stage == "STAGE_2":
            # Define actions for STAGE_2
            stage_2_action = QAction("No LMB actions", self)
            stage_2_action.triggered.connect(lambda: self.performActionForStage2())
            menu.addAction(stage_2_action)
        if self.stage == "STAGE_3":
            # Define actions for STAGE_3
            stage_3_action = QAction("No LMB actions", self)
            stage_3_action.triggered.connect(lambda: self.performActionForStage3())
            menu.addAction(stage_3_action)
        if self.stage == "STAGE_4":
            # Define actions for STAGE_4
            stage_4_action = QAction("No LMB actions", self)
            stage_4_action.triggered.connect(lambda: self.performActionForStage4())
            menu.addAction(stage_4_action)

        menu.exec_(self.mapToGlobal(position))

    def showRightClickMenu(self, position):
        menu = QMenu(self)
        open_in_rv_menu = QMenu("Open in RV", self)
        open_in_rv_menu.aboutToShow.connect(self.populateRVSequencesMenu)
        menu.addMenu(open_in_rv_menu)

        if self.stage == "STAGE_1":
            # Define actions for STAGE_1
            stage_1_action = QAction("No RMB actions", self)
            stage_1_action.triggered.connect(lambda: self.performActionForStage1())
            #menu.addAction(stage_1_action)
        elif self.stage == "STAGE_2":
            # Define actions for STAGE_2
            stage_2_action = QAction("No RMB actions", self)
            stage_2_action.triggered.connect(lambda: self.performActionForStage2())
            menu.addAction(stage_2_action)
        if self.stage == "STAGE_3":
            # Define actions for STAGE_3
            stage_3_action = QAction("No RMB actions", self)
            stage_3_action.triggered.connect(lambda: self.performActionForStage3())
            menu.addAction(stage_3_action)
        if self.stage == "STAGE_4":
            # Define actions for STAGE_4
            stage_4_action = QAction("No RMB actions", self)
            stage_4_action.triggered.connect(lambda: self.performActionForStage4())
            menu.addAction(stage_4_action)

        menu.exec_(self.mapToGlobal(position))

    def launchRV(self, sequence):
        # This function will be called when a sequence is selected from the submenu
        rv_player = OpenRV()
        rv_player.launch_rv(sequence)

    def openNKFile(self, file_path):
        try:
            subprocess.Popen(['start', file_path], shell=True)
        except Exception as e:
            print(f"Error opening NK file: {e}")
