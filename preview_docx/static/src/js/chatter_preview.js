/** @odoo-module **/

document.addEventListener(
    "click",
    function (ev) {

        const card =
            ev.target.closest(
                ".o-mail-AttachmentCard"
            );

        if (!card) {
            return;
        }

        const nameEl =
            card.querySelector(
                ".text-truncate"
            );

        const filename =
            nameEl
                ? nameEl.innerText.trim()
                : "";

        if (
            !filename.toLowerCase().endsWith(".docx")
        ) {
            return;
        }

        ev.preventDefault();
        ev.stopPropagation();

        const btn =
            card.querySelector(
                'button[title="Download"]'
            );

        const downloadUrl =
            btn.getAttribute(
                "data-download-url"
            );

        const urlObj =
            new URL(
                downloadUrl,
                window.location.origin
            );

        const attachmentId =
            urlObj.pathname.match(/\d+/)?.[0];

        const url = `/public/doc/${attachmentId}/${filename}`;
        window.open(url, "_blank")

        console.log(
            "attachmentId",
            attachmentId
        );
    }
);