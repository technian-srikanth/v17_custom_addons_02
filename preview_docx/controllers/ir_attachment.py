from odoo import http
from odoo.http import request
import base64


class PublicDoc(http.Controller):

    @http.route(
        '/public/doc/<int:attachment_id>/<string:filename>',
        type='http',
        auth='public',
        csrf=False
    )
    def public_doc(self, attachment_id, filename=None, **kwargs):

        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)

        if not attachment.exists():
            return request.not_found()

        # Decode binary data
        file_content = base64.b64decode(attachment.datas or b'')

        headers = [
            ('Content-Type', attachment.mimetype or 'application/octet-stream'),
            ('Content-Disposition', f'inline; filename="{attachment.name}"')
        ]

        return request.make_response(file_content, headers)