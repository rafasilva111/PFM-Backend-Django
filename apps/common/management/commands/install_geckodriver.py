import os
import platform
import tarfile
import requests
from django.core.management.base import BaseCommand

GECKODRIVER_VERSION = "v0.34.0"
GECKODRIVER_URL = "https://github.com/mozilla/geckodriver/releases/download"

class Command(BaseCommand):
    help = "Download and install Geckodriver"

    def handle(self, *args, **options):
        system = platform.system().lower()
        arch = "64" if platform.architecture()[0] == "64bit" else "32"

        if system == "linux":
            filename = f"geckodriver-{GECKODRIVER_VERSION}-linux{arch}.tar.gz"
        elif system == "darwin":
            filename = f"geckodriver-{GECKODRIVER_VERSION}-macos.tar.gz"
        elif system == "windows":
            filename = f"geckodriver-{GECKODRIVER_VERSION}-win{arch}.zip"
        else:
            self.stdout.write(self.style.ERROR("Unsupported OS"))
            return

        download_url = f"{GECKODRIVER_URL}/{GECKODRIVER_VERSION}/{filename}"
        dest_dir = os.path.join(os.getcwd(), "bin")
        dest_path = os.path.join(dest_dir, "geckodriver")

        os.makedirs(dest_dir, exist_ok=True)

        self.stdout.write(f"Downloading Geckodriver from {download_url}...")

        response = requests.get(download_url, stream=True)
        if response.status_code == 200:
            tar_path = os.path.join(dest_dir, filename)
            with open(tar_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)

            self.stdout.write("Extracting Geckodriver...")

            if filename.endswith(".tar.gz"):
                with tarfile.open(tar_path, "r:gz") as tar:
                    tar.extractall(path=dest_dir)
            elif filename.endswith(".zip"):
                import zipfile
                with zipfile.ZipFile(tar_path, "r") as zip_ref:
                    zip_ref.extractall(dest_dir)

            os.chmod(dest_path, 0o755)
            self.stdout.write(self.style.SUCCESS(f"Geckodriver installed at: {dest_path}"))

        else:
            self.stdout.write(self.style.ERROR(f"Failed to download Geckodriver. HTTP {response.status_code}"))
