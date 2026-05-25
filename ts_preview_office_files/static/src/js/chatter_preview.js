/** @odoo-module **/
import {Dialog} from "@web/core/dialog/dialog";
import {Component, xml} from "@odoo/owl";

export class DocumentPreview extends Component {
    static components = {Dialog};
    downloadFile() {
        const url =
            `/web/content/${this.props.attachmentId}?download=true`;
        const a = document.createElement("a");
        a.href = url;
        a.download = this.props.title;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }
}

DocumentPreview.template = xml`
<Dialog
    size="'fullscreen'"
    technical="false"
    contentClass="'o_full_screen_preview'">

<t t-set-slot="header">
    <div class="header">
        <h5
            class="mb-0 text-truncate text-white"
            t-esc="props.title"/>
        <div class="section-2">
            <button
                class="download-btn btn btn-secondary"
                t-on-click="downloadFile">
                <i class="fa fa-download"/>
                Download
            </button>
            <button
                class="btn-close"
                t-on-click="props.close"/>
        </div>
    </div>
</t>

<div class="o_preview_container d-flex flex-column justify-content-center fixed bottom-0 m-0 p-0">
    <div
        id="doc_viewer"
        class="o_doc_viewer flex-grow-1 overflow-auto">
        Loading preview...
    </div>
</div>

<t t-set-slot="footer">.</t>
</Dialog>
`;

async function waitForPdf(url, loadingEl) {
    for (let i = 0; i < 30; i++) {
        const response = await fetch(url);
        if (response.status === 202) {
            loadingEl.style.display = "flex";
            await new Promise(
                r => setTimeout(r, 2500)
            );
            continue;
        }
        if (response.ok) {

            loadingEl.style.display = "none";

            return await response.arrayBuffer();
        }
        throw new Error(
            `HTTP ${response.status}`
        );
    }

    throw new Error("Preview timeout");
}

async function renderPdf(
    pdfData,
    container,
    scale = 1.2
) {

    const pdfModule = await import(
        "/ts_preview_office_files/static/lib/pdf.mjs"
    );
    const pdfjsLib = pdfModule;
    pdfjsLib.GlobalWorkerOptions.workerSrc =
        "/ts_preview_office_files/static/lib/pdf.worker.mjs";
    const pdf =
        await pdfjsLib.getDocument({
            data: pdfData
        }).promise;
    for (
        let pageNum = 1;
        pageNum <= pdf.numPages;
        pageNum++
    ) {
        const page =
            await pdf.getPage(pageNum);
        const viewport =
            page.getViewport({
                scale: scale
            });
        const wrapper =
            document.createElement("div");
        wrapper.style.margin = "10px auto";
        wrapper.style.width = "fit-content";
        const canvas =
            document.createElement("canvas");
        const ctx =
            canvas.getContext("2d");

        canvas.height = viewport.height;
        canvas.width = viewport.width;
        wrapper.appendChild(canvas);
        container.appendChild(wrapper);
        await page.render({
            canvasContext: ctx,
            viewport: viewport
        }).promise;
    }
}


if (!window._docPreviewClickAttached) {
    window._docPreviewClickAttached = true;
    document.addEventListener(
        "click",
        async function (ev) {
            const card =
                ev.target.closest(
                    ".o-mail-AttachmentCard"
                );
            if (!card) return;
            const nameEl =
                card.querySelector(
                    ".text-truncate"
                );
            const filename =
                nameEl
                    ? nameEl.innerText.trim()
                    : "";
            if (
                ![
                    ".csv",
                    ".xlsx",
                    ".xls",
                    ".xlsb",
                    ".xlsm",
                    ".docx",
                    ".doc",
                    ".pptx",
                    ".ppt"
                ].some(
                    ext =>
                        filename
                            .toLowerCase()
                            .endsWith(ext)
                )
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

            const attachmentId =
                new URL(
                    downloadUrl,
                    window.location.origin
                )
                    .pathname
                    .split("/")
                    .pop();

            const dialogService =
                owl.Component.env.services.dialog;

            dialogService.add(
                DocumentPreview,
                {
                    title: filename,
                    attachmentId: attachmentId,
                }
            );

            await new Promise(
                r => setTimeout(r, 50)
            );

            const viewer =
                document.getElementById(
                    "doc_viewer"
                );

            if (!viewer) return;

            viewer.classList.remove(
                "docx-mode",
                "other-mode"
            );

            viewer.replaceChildren();

            if (
                filename.endsWith(".xlsx")
                || filename.endsWith(".xls")
                || filename.endsWith(".xlsb")
                || filename.endsWith(".xlsm")
                || filename.endsWith(".csv")
            ) {

                viewer.classList.add(
                    "other-mode"
                );

                const response =
                    await fetch(
                        `/sheet/preview/${attachmentId}`
                    );

                const data =
                    await response.json();

                const spreadsheet =
                    x_spreadsheet(viewer, {

                        mode: "read",

                        showToolbar: false,

                        showGrid: true,

                        showContextmenu: false
                    });

                const sheets = [];

                data.sheets.forEach(sheet => {

                    const MIN_ROWS = 25;

                    const sheetRows = {

                        len: Math.max(
                            sheet.rows.length,
                            MIN_ROWS
                        )
                    };

                    sheet.rows.forEach(
                        (row, r) => {

                            const cells = {};

                            row.forEach(
                                (cell, c) => {

                                    cells[c] = {

                                        text: cell
                                            ? String(cell)
                                            : ""
                                    };
                                }
                            );

                            sheetRows[r] = {
                                cells
                            };
                        }
                    );

                    sheets.push({

                        name: sheet.name,

                        rows: sheetRows
                    });
                });

                spreadsheet.loadData(
                    sheets
                );
            }

            else if (
                filename.endsWith(".docx")
                || filename.endsWith(".doc")
            ) {

                viewer.classList.add(
                    "docx-mode"
                );

                const wrapper =
                    document.createElement("div");
                const loading =
                    document.createElement("div");

                loading.style.cssText = `
                    padding:40px;
                    text-align:center;
                    font-size:18px;
                `;

                loading.textContent =
                    "Generating preview...";

                const container =
                    document.createElement("div");

                container.id =
                    "pdf_container";

                wrapper.appendChild(
                    loading
                );

                wrapper.appendChild(
                    container
                );

                viewer.replaceChildren(
                    wrapper
                );

                try {

                    const pdfData =
                        await waitForPdf(

                            `/docx/preview/${attachmentId}`,

                            loading
                        );

                    await renderPdf(
                        pdfData,
                        container,
                        1.2
                    );

                } catch (err) {

                    console.error(err);

                    viewer.replaceChildren(
                        Object.assign(
                            document.createElement("div"),
                            {

                                style:
                                    "padding:20px",

                                textContent:
                                    "Unable to generate preview."
                            }
                        )
                    );
                }
            }

            else if (
                filename.endsWith(".pptx")
                || filename.endsWith(".ppt")
            ) {

                viewer.classList.add(
                    "other-mode"
                );

                const wrapper =
                    document.createElement("div");

                const loading =
                    document.createElement("div");

                loading.style.cssText = `
                    padding:40px;
                    text-align:center;
                    font-size:18px;
                `;

                loading.textContent =
                    "Generating preview...";

                const container =
                    document.createElement("div");

                container.id =
                    "pdf_container";

                wrapper.appendChild(
                    loading
                );

                wrapper.appendChild(
                    container
                );

                viewer.replaceChildren(
                    wrapper
                );

                try {

                    const pdfData =
                        await waitForPdf(

                            `/ppt/preview/${attachmentId}`,

                            loading
                        );

                    await renderPdf(
                        pdfData,
                        container,
                        1.2
                    );

                } catch (err) {

                    console.error(err);

                    viewer.replaceChildren(
                        Object.assign(
                            document.createElement("div"),
                            {

                                style:
                                    "padding:20px",

                                textContent:
                                    "Unable to generate preview."
                            }
                        )
                    );
                }
            }
        }
    );
}


if (!window._docPreviewHoverAttached) {
    window._docPreviewHoverAttached = true;
    document.addEventListener(
        "mouseover",
        function (ev) {

            const card =
                ev.target.closest(
                    ".o-mail-AttachmentCard"
                );
            if (!card) return;

            if (!card.dataset.cursorSet) {

                card.style.cursor =
                    "zoom-in";

                card.dataset.cursorSet =
                    "true";
            }
        }
    );
}