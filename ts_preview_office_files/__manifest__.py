{
    'name': 'Attachment files preview',
    'version': '17.0.0.0.1',
    'depends': ['base', 'mail', 'web', 'queue_job'],
    'author': 'Nians',
    'description': """ CSV ,XLSX ,PPTX AND  DOCX Attachments files preview """,
    'assets': {
        'web.assets_backend': [
            'ts_preview_office_files/static/lib/jszip.min.js',

            'ts_preview_office_files/static/src/js/chatter_preview.js',
            'ts_preview_office_files/static/src/css/document_preview.css',

            # preview xls and csv
            "ts_preview_office_files/static/lib/xls/spreadheet.js",
            "ts_preview_office_files/static/src/css/spreadhseet.css",
            "ts_preview_office_files/static/lib/xls/xlsx.full.min.js",

            # preview pptx and  Docx
            "ts_preview_office_files/static/lib/pdf.mjs",
            "ts_preview_office_files/static/lib/pdf.worker.mjs",
        ],
    },
}
