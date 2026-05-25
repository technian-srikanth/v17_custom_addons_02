{
    'name': 'Attachment files preview',
    'version': '17.0.0.0.1',
    'depends': ['base', 'mail', 'web', 'queue_job'],
    'author': 'Nians',
    'description': """ CSV ,XLSX ,PPTX AND  DOCX Attachments files preview """,
    'assets': {
        'web.assets_backend': [
            'preview_docx/static/src/js/chatter_preview.js',
        ],
    },
}
