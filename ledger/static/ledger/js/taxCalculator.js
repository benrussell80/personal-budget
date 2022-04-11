function calculateMonthlyExtraWithholdingsNeeded({
    monthlyStateBurden,
    monthlyFederalBurden,
    stateBurdenYtd,
    federalBurdenYtd,
    statePaidYtd,
    federalPaidYtd,
    monthlyStatePmt,
    monthlyFederalPmt,
    monthsRemaining,
}) {
    extraStateWithholding = Math.max(
        0,
        monthlyStateBurden - monthlyStatePmt + (stateBurdenYtd - statePaidYtd) / monthsRemaining
    )
    extraFederalWithholding = Math.max(
        0,
        monthlyFederalBurden - monthlyFederalPmt + (federalBurdenYtd - federalPaidYtd) / monthsRemaining
    )

    estimatedStateRefund = Math.max(
        0,
        (monthlyStatePmt - monthlyStateBurden) * monthsRemaining + statePaidYtd - stateBurdenYtd
    )
    estimatedFederalRefund = Math.max(
        0,
        (monthlyFederalPmt - monthlyFederalBurden) * monthsRemaining + federalPaidYtd - federalBurdenYtd
    )

    return {
        extraStateWithholding,
        extraFederalWithholding,
        estimatedStateRefund,
        estimatedFederalRefund,
    }
}

function displayResults({
    extraStateWithholding,
    extraFederalWithholding,
    estimatedStateRefund,
    estimatedFederalRefund,
}) {
    document.querySelector('#ExtraStateWH').textContent = extraStateWithholding.toFixed(2);
    document.querySelector('#ExtraFederalWH').textContent = extraFederalWithholding.toFixed(2);
    document.querySelector('#EstStateRef').textContent = estimatedStateRefund.toFixed(2);
    document.querySelector('#EstFederalRef').textContent = estimatedFederalRefund.toFixed(2);
}

/**
 * 
 * @param {Event} event 
 */
function handleTaxCalculationFormSubmit(event) {
    event.preventDefault();

    let form = document.querySelector('#TaxCalculator');
    if (form) {
        const monthlyStateBurden = form.querySelector('[name="monthlyStateBurden"]').valueAsNumber;
        const monthlyFederalBurden = form.querySelector('[name="monthlyFederalBurden"]').valueAsNumber;
        const stateBurdenYtd = form.querySelector('[name="stateBurdenYtd"]').valueAsNumber;
        const federalBurdenYtd = form.querySelector('[name="federalBurdenYtd"]').valueAsNumber;
        const statePaidYtd = form.querySelector('[name="statePaidYtd"]').valueAsNumber;
        const federalPaidYtd = form.querySelector('[name="federalPaidYtd"]').valueAsNumber;
        const monthlyStatePmt = form.querySelector('[name="monthlyStatePmt"]').valueAsNumber;
        const monthlyFederalPmt = form.querySelector('[name="monthlyFederalPmt"]').valueAsNumber;
        const monthsRemaining = form.querySelector('[name="monthsRemaining"]').valueAsNumber;
        const results = calculateMonthlyExtraWithholdingsNeeded({
            monthlyStateBurden,
            monthlyFederalBurden,
            stateBurdenYtd,
            federalBurdenYtd,
            statePaidYtd,
            federalPaidYtd,
            monthlyStatePmt,
            monthlyFederalPmt,
            monthsRemaining,
        });
        displayResults(results);
        // clear form
    }
}