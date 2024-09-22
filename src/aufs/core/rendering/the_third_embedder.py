import os

class TheThirdEmbedder:
    def __init__(self, base_path=None):
        """
        Initializes the embedder with the base path where the scripts are stored.
        Default is 'core/net' inside the current working directory.
        """
        self.base_path = base_path or os.path.join(os.getcwd(), 'core', 'net')

    def list_protocols(self):
        """
        Lists all available protocol directories inside the 'core/net' directory.
        :return: List of protocol directory names.
        """
        if not os.path.exists(self.base_path):
            return []

        # List directories only
        return [d for d in os.listdir(self.base_path) if os.path.isdir(os.path.join(self.base_path, d))]

    def list_scripts_for_protocol(self, protocol):
        """
        Lists all the scripts for a given protocol.
        :param protocol: The protocol directory (e.g., 'smb', 'ftp', etc.).
        :return: A list of available scripts following the net_{protocol}_{platform} pattern.
        """
        protocol_dir = os.path.join(self.base_path, protocol)

        if not os.path.exists(protocol_dir):
            print(f"Directory {protocol_dir} does not exist.")
            return []

        return [f for f in os.listdir(protocol_dir) if f.startswith(f'net_{protocol}_') and f.endswith(('.bash', '.ps1'))]

    def embed_script(self, script_path):
        """
        Embeds the script by reading its content.
        :param script_path: The full path to the script.
        :return: The script content.
        """
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script {script_path} does not exist.")

        with open(script_path, 'r') as script_file:
            script_content = script_file.read()

        print(f"Embedded script content from {script_path}")
        return script_content

    def get_scripts_for_all_platforms(self, protocol):
        """
        Fetches scripts for all platforms ('darwin', 'linux', 'win') for the given protocol.
        :param protocol: The protocol directory (e.g., 'smb', 'ftp').
        :return: Dictionary with platform as key and script content as value.
        """
        platform_script_map = {
            "darwin": f"net_{protocol}_darwin.bash",
            "linux": f"net_{protocol}_linux.bash",
            "win": f"net_{protocol}_win.ps1"
        }

        script_contents = {}
        for platform, script_name in platform_script_map.items():
            script_path = os.path.join(self.base_path, protocol, script_name)
            if os.path.exists(script_path):
                script_contents[platform] = self.embed_script(script_path)

        return script_contents
