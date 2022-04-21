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
    row.querySelectorAll('.errorlist').forEach(elem => elem.remove());

    let tableBody = document.querySelector(LAST_DETAIL_ROW_SELECTOR).parentElement;
    tableBody.appendChild(row);

    incrementTotalFormAmount();
    checkDeleteButtonDisabledStatus();
}

/**
 * Delete a row from the detail table.
 * @param {HTMLButtonElement} deleteButton 
 */
const deleteDetailTableRow = (deleteButton) => {
    let td = deleteButton.parentElement;
    let tr = td.parentElement;
    tr.remove();
    decrementTotalFormAmount();
    checkDeleteButtonDisabledStatus();
    updateTableTotals();
}

const checkDeleteButtonDisabledStatus = () => {
    let buttons = document.querySelectorAll('.delete-row-btn');
    let disable = buttons.length <= 1;
    if (disable) {
        buttons.forEach(elem => elem.setAttribute('disabled', ''))
    } else {
        buttons.forEach(elem => elem.removeAttribute('disabled'));
    }

}

const changeTotalFormAmount = (value) => {
    let totalFormsInput = document.querySelector(TOTAL_FORMS_SELECTOR);
    if (!totalFormsInput) return
    let numForms = parseInt(totalFormsInput.value) + value;
    totalFormsInput.value = numForms;
}

const incrementTotalFormAmount = () => changeTotalFormAmount(1);

const decrementTotalFormAmount = () => changeTotalFormAmount(-1);

const calculateDebitsAndCredits = () => {
    let debits = ([...document.querySelectorAll('input[name^="details-"][name$="-debit"]')])
        .map(elem => elem.valueAsNumber || 0).reduce((acc, cur) => acc + cur, 0);
    let credits = ([...document.querySelectorAll('input[name^="details-"][name$="-credit"]')])
        .map(elem => elem.valueAsNumber || 0).reduce((acc, cur) => acc + cur, 0);
    return [debits, credits]
};

const updateTableTotals = () => {
    let debitTotal = document.querySelector('#DebitTotal');
    let creditTotal = document.querySelector('#CreditTotal');
    let [debits, credits] = calculateDebitsAndCredits();
    debitTotal.textContent = debits.toFixed(2).toString();
    creditTotal.textContent = credits.toFixed(2).toString();
};

document.addEventListener('DOMContentLoaded', () => {
    updateTableTotals();
    document.querySelectorAll('input[name^="details-"][name$="-debit"], input[name^="details-"][name$="-credit"]').forEach(
        elem => elem.addEventListener('change', () => updateTableTotals())
    )
})