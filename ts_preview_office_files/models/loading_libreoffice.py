import subprocess
import platform
import shutil
import psutil
import os
import tempfile


# =====================================================
# LIBREOFFICE PATH
# =====================================================
if platform.system() == "Windows":

    LIBREOFFICE_PATH = (
        r"C:\Program Files\LibreOffice\program\soffice.exe"
    )

else:

    LIBREOFFICE_PATH = (
        shutil.which("soffice")
        or "/usr/bin/soffice"
    )


if not os.path.exists(LIBREOFFICE_PATH):

    raise Exception(
        f"LibreOffice not found: {LIBREOFFICE_PATH}"
    )


# =====================================================
# GLOBAL PROFILE
# =====================================================
LIBREOFFICE_PROFILE = os.path.join(

    tempfile.gettempdir(),

    "odoo_lo_profile"
)

os.makedirs(
    LIBREOFFICE_PROFILE,
    exist_ok=True
)


# =====================================================
# CHECK RUNNING
# =====================================================
def is_libreoffice_running():

    for proc in psutil.process_iter(['name', 'cmdline']):

        try:

            process_name = (
                proc.info['name'] or ''
            ).lower()

            cmdline = " ".join(
                proc.info.get('cmdline') or []
            ).lower()

            if (
                'soffice' in process_name
                or 'soffice.bin' in process_name
            ):

                # ensure same profile
                if LIBREOFFICE_PROFILE.lower() in cmdline:

                    return True

        except Exception:
            pass

    return False


# =====================================================
# START BACKGROUND PROCESS
# =====================================================
def start_libreoffice():

    if is_libreoffice_running():

        print(
            "LibreOffice already running"
        )

        return

    try:

        subprocess.Popen(

            [
                LIBREOFFICE_PATH,

                f'-env:UserInstallation=file:///{LIBREOFFICE_PROFILE.replace(os.sep, "/")}',

                '--headless',

                '--nologo',

                '--nodefault',

                '--nofirststartwizard',

                '--norestore',

                '--nolockcheck',

                '--invisible',
            ],

            creationflags=subprocess.CREATE_NO_WINDOW
            if platform.system() == "Windows"
            else 0
        )

        print(
            "LibreOffice background process started"
        )

    except Exception as e:

        print(
            f"LibreOffice startup failed: {e}"
        )

# =====================================================
# AUTO START
# =====================================================
start_libreoffice()