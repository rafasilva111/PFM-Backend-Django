import os
import subprocess
from django.core.management.base import BaseCommand
from pathlib import Path

class Command(BaseCommand):
    help = "Generate self-signed SSL cert and move it to nginx/ssl-secrets"

    def handle(self, *args, **kwargs):
        cert_file = "ssl_domain.crt"
        key_file = "ssl_domain.key"
        output_dir = Path("nginx/ssl-secrets")

        self.stdout.write("Generating self-signed SSL certificate...")

        try:
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                "-keyout", key_file,
                "-out", cert_file,
                "-days", "365",
                "-subj", "/CN=localhost"
            ], check=True)

            output_dir.mkdir(parents=True, exist_ok=True)
            os.replace(key_file, output_dir / key_file)
            os.replace(cert_file, output_dir / cert_file)

            self.stdout.write(self.style.SUCCESS(f"Certificate and key moved to {output_dir}"))
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"OpenSSL failed: {e}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error: {e}"))