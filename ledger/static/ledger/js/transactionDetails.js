const LAST_DETAIL_ROW_SELECTOR = 'table > tbody > tr:last-child';
const TOTAL_FORMS_SELECTOR = 'input[name="details-TOTAL_FORMS"]';
const INPUT_ID_PATTERN = /id_details-([0-9]+)-(.+)/i;
const INPUT_NAME_PATTERN = /details-([0-9]+)-(.+)/i;
const ADD_ROW_BUTTON_SELECTOR = '#AddRowButton';


/**
 * Add a row to the transaction details table
 */
const addRowToDetailTable = () => {
    let row = document.querySelector(LAST_DETAIL_ROW_SELECTOR);
    if (!row) return
    row = row.cloneNode(true);
    for (let child of row.children) {
        for (let element of child.children) {
            if (element instanceof HTMLInputElement || element instanceof HTMLSelectElement || element instanceof HTMLTextAreaElement) {
                let idMatch = element.id.match(INPUT_ID_PATTERN);
                let idNum = parseInt(idMatch[1]) + 1;
                let idField = idMatch[2];
                element.id = `id_details-${idNum}-${idField}`;

                let nameMatch = element.name.match(INPUT_NAME_PATTERN);
                let nameNum = parseInt(nameMatch[1]) + 1;
                let nameField = nameMatch[2];
                element.name = `details-${nameNum}-${nameField}`;

                if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
                    element.value = null;
                } else {
                    element.selectedIndex = 0
                }
            }
        }
    }
    let tableBody = document.querySelector(LAST_DETAIL_ROW_SELECTOR).parentElement;
    tableBody.appendChild(row);

    let totalFormsInput = document.querySelector(TOTAL_FORMS_SELECTOR);
    if (!totalFormsInput) return
    let numForms = parseInt(totalFormsInput.value) + 1;
    totalFormsInput.value = numForms;
}

