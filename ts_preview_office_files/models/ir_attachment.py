from odoo import models, api, fields
from odoo.addons.queue_job.job import identity_exact

import base64
import tempfile
import subprocess
import os
import platform
import shutil


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


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    # =====================================================
    # PREVIEW STATUS
    # =====================================================
    preview_generated = fields.Boolean(
        default=False
    )

    preview_error = fields.Text()

    # =====================================================
    # CREATE
    # =====================================================
    @api.model_create_multi
    def create(self, vals_list):

        records = super().create(vals_list)

        supported_mimetypes = [

            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',

            'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        ]

        for rec in records:

            if (
                rec.mimetype in supported_mimetypes
                and rec.type == 'binary'
                and rec.datas
            ):

                rec.write({

                    'preview_generated': False,

                    'preview_error': False,
                })

                rec.with_delay(

                    identity_key=identity_exact,

                    priority=1,

                    channel='root.preview'

                ).generate_preview_job()

        return records

    # =====================================================
    # BACKGROUND JOB
    # =====================================================
    def generate_preview_job(self):

        self.ensure_one()

        try:

            # =====================================================
            # ALREADY GENERATED
            # =====================================================
            if self.preview_generated:
                return

            ext = (

                'docx'

                if self.mimetype.endswith(
                    'wordprocessingml.document'
                )

                else 'pptx'
            )

            # =====================================================
            # CONVERT
            # =====================================================
            self._convert_to_pdf_with_cache(ext)

            # =====================================================
            # SUCCESS
            # =====================================================
            self.write({

                'preview_generated': True,

                'preview_error': False,
            })

        except Exception as e:

            # =====================================================
            # ERROR
            # =====================================================
            self.write({

                'preview_error': str(e)
            })

    # =====================================================
    # PDF CONVERSION
    # =====================================================
    def _convert_to_pdf_with_cache(self, ext):

        self.ensure_one()

        if not self.datas:

            raise Exception(
                "Attachment has no data"
            )

        cache_key = (
            f"{self.id}_{self.checksum}"
        )

        cached_name = (
            f"cache_{cache_key}.pdf"
        )

        # =====================================================
        # CACHE CHECK
        # =====================================================
        preview_cache = self.env[
            'ir.attachment'
        ].sudo().search([

            ('name', '=', cached_name),

        ], limit=1)

        if preview_cache:

            return base64.b64decode(
                preview_cache.datas
            )

        # =====================================================
        # REMOVE OLD CACHE
        # =====================================================
        old_caches = self.env[
            'ir.attachment'
        ].sudo().search([

            ('name', 'like', f"cache_{self.id}_")

        ])

        old_caches.unlink()

        # =====================================================
        # FILE DATA
        # =====================================================
        file_data = base64.b64decode(
            self.datas
        )

        # =====================================================
        # TEMP DIRECTORY
        # =====================================================
        with tempfile.TemporaryDirectory() as tmpdir:

            # =====================================================
            # UNIQUE LIBREOFFICE PROFILE
            # =====================================================
            profile_dir = os.path.join(
                tmpdir,
                "lo_profile"
            )

            os.makedirs(profile_dir, exist_ok=True)

            # =====================================================
            # INPUT FILE
            # =====================================================
            input_path = os.path.join(

                tmpdir,

                f"input.{ext}"
            )

            with open(input_path, "wb") as f:

                f.write(file_data)

            if os.path.getsize(input_path) == 0:

                raise Exception(
                    "Input file is empty"
                )

            # =====================================================
            # LIBREOFFICE CONVERSION
            # =====================================================
            process = subprocess.run(
                [
                    LIBREOFFICE_PATH,

                    f'-env:UserInstallation=file:///{profile_dir.replace(os.sep, "/")}',

                    '--headless',

                    '--nologo',

                    '--nofirststartwizard',

                    '--nolockcheck',

                    '--nodefault',

                    '--invisible',

                    '--quickstart=no',

                    '--convert-to',
                    'pdf',

                    '--outdir',
                    tmpdir,

                    input_path,
                ],

                stdout=subprocess.PIPE,

                stderr=subprocess.PIPE,

                text=True,

                timeout=180
            )

            # =====================================================
            # CONVERSION ERROR
            # =====================================================
            if process.returncode != 0:

                raise Exception(

                    f"LibreOffice conversion failed:\n"
                    f"{process.stderr}"
                )

            # =====================================================
            # PDF PATH
            # =====================================================
            pdf_path = os.path.join(

                tmpdir,

                "input.pdf"
            )

            if not os.path.exists(pdf_path):

                raise Exception(
                    "PDF file not generated"
                )

            # =====================================================
            # READ PDF
            # =====================================================
            with open(pdf_path, "rb") as f:

                pdf_data = f.read()

        # =====================================================
        # SAVE CACHE
        # =====================================================
        self.env['ir.attachment'].sudo().create({

            'name': cached_name,

            'datas': base64.b64encode(
                pdf_data
            ),

            'mimetype': 'application/pdf',

            'type': 'binary',
        })

        return pdf_data