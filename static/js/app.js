document.addEventListener('htmx:oobAfterSwap', cleanupLog);
document.body.addEventListener('triggerDefeatAnimation', defeatAnim);
document.body.addEventListener('triggerMove', moveAnim);
document.body.addEventListener('updateStatus', updateStatus);
document.body.addEventListener('click', levelStats);

function cleanupLog(event) {
    if (event.detail.target && event.detail.target.id === "event-log-swap") {
        const MAX_LOGS = 50;
        const container = event.detail.target;

        const logs = Array.from(container.querySelectorAll('.log-wrapper'));

        if (logs.length > MAX_LOGS) {
            const toPrune = logs.slice(MAX_LOGS);

            toPrune.forEach(el => {
                el.classList.add('log-pruning');

                setTimeout(() => {
                    if (el.parentNode) {
                        el.remove();
                    }
                }, 500);
            });
        }
    }
}

function defeatAnim(event) {
    const activeIds = event.detail.activeIds || [];
    const allSvgs = document.querySelectorAll('[id^="svg-"]');

    allSvgs.forEach(element => {
        if (!activeIds.includes(element.id)) {
            element.classList.add('defeat-animate');
            element.addEventListener('animationend', () => {
                element.remove();
            }, { once: true });
        }
    });
}

function moveAnim(event) {
    const updates = event.detail.moveIds || [];

    updates.forEach(item => {
        const element = document.getElementById(item.id);
        if (element) {
            element.style.top = `${item.top}%`;
            element.style.left = `${item.left}%`;
        }
    });
}

function updateStatus(event) {
    const e_hpbar = document.getElementById('status-hp-bar');
    const e_hptxt = document.getElementById('status-hp-text');

    const e_mpbar = document.getElementById('status-mp-bar');
    const e_mptxt = document.getElementById('status-mp-text');

    const e_xpbar = document.getElementById('status-xp-bar');
    const e_xptxt = document.getElementById('status-xp-text');

    const e_lvl = document.getElementById('status-level');

    e_hpbar.style.width = `${event.detail.hp_perc}%`;
    e_hpbar.setAttribute('aria-valuenow', event.detail.hp_curr);
    e_hpbar.setAttribute('aria-valuemax', event.detail.hp_max);
    e_hptxt.innerText = `${event.detail.hp_curr} / ${event.detail.hp_max} HP`;

    e_mpbar.style.width = `${event.detail.mp_perc}%`;
    e_mpbar.setAttribute('aria-valuenow', event.detail.mp_curr);
    e_mpbar.setAttribute('aria-valuemax', event.detail.mp_max);
    e_mptxt.innerText = `${event.detail.mp_curr} / ${event.detail.mp_max} MP`;

    const currentXPWidth = parseFloat(e_xpbar.style.width) || 0;
    if (currentXPWidth != event.detail.xp_perc) {
        if (currentXPWidth > event.detail.xp_perc) {
            e_xpbar.classList.add('no-transition');
        }
        else {
            e_xpbar.classList.remove('no-transition');
        }
    }

    e_xpbar.style.width = `${event.detail.xp_perc}%`;
    e_xpbar.setAttribute('aria-valuenow', event.detail.xp_curr);
    e_xpbar.setAttribute('aria-valuemax', event.detail.xp_max);
    e_xptxt.innerText = `${event.detail.xp_curr} / ${event.detail.xp_max} XP`;

    e_lvl.innerText = `Lvl ${event.detail.lvl}`;
}

function levelStats(event) {
    const statPlus = event.target.closest('.stat-add-btn');
    const statMinus = event.target.closest('.stat-min-btn');

    if (!statPlus && !statMinus) return;

    const form = document.getElementById('stat-form');

    let pointsRemaining = parseInt(form.getAttribute('data-stat-points'));
    let pointsOriginal = parseInt(form.getAttribute('data-stat-orig'));

    const statRow = event.target.closest('.stat-row');
    const inputField = statRow.querySelector('.stat-input');
    const displayVal = statRow.querySelector('.stat-display');
    const btnMinus = statRow.querySelector('.stat-min-btn');

    let baseVal = parseInt(statRow.getAttribute('data-base-val'));
    let addedVal = parseInt(inputField.value);

    if (statPlus && pointsRemaining > 0) {
        addedVal++;
        pointsRemaining--;
    }
    else if (statMinus && addedVal > 0) {
        addedVal--;
        pointsRemaining++;
    }

    inputField.value = addedVal;
    displayVal.innerText = baseVal + addedVal;

    // Toggle minus buttons
    if (addedVal > 0) {
        btnMinus.classList.remove('invisible');
    }
    else {
        btnMinus.classList.add('invisible');
    }

    // Update remaining stat points
    form.setAttribute('data-stat-points', pointsRemaining);
    document.getElementById('stat-points').innerText = pointsRemaining;

    const allPlusBtns = form.querySelectorAll('.stat-add-btn');
    const submitBtn = document.getElementById('submit-stats-btn');

    // Toggle plus buttons
    if (pointsRemaining === 0) {
        allPlusBtns.forEach(btn => {
            btn.classList.add('invisible');
        });
    }
    else {
        allPlusBtns.forEach(btn => {
            btn.classList.remove('invisible');
        });
    }

    // Toggle submit button
    if (pointsRemaining === pointsOriginal) {
        submitBtn.classList.add('invisible');
    }
    else {
        submitBtn.classList.remove('invisible');
    }
}