document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('booking-form');
    const saveBtn = document.getElementById('save-btn');
    const jsonOutput = document.getElementById('json-output');

    const daysOfWeek = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"];

    // Create inputs for each day
    daysOfWeek.forEach(day => {
        const dayDiv = document.createElement('div');
        dayDiv.classList.add('day-entry');
        dayDiv.innerHTML = `
            <label>
                <input type="checkbox" id="check-${day}" data-day="${day}">
                ${day}
            </label>
            <input type="text" id="time-${day}" placeholder="e.g., 20:30 - 21:30" disabled>
        `;
        form.appendChild(dayDiv);
    });

    // Enable/disable time input based on checkbox
    form.addEventListener('change', (e) => {
        if (e.target.type === 'checkbox') {
            const day = e.target.dataset.day;
            const timeInput = document.getElementById(`time-${day}`);
            timeInput.disabled = !e.target.checked;
            if (!e.target.checked) {
                timeInput.value = '';
            }
        }
    });

    // Generate JSON on button click
    saveBtn.addEventListener('click', () => {
        const config = {};
        daysOfWeek.forEach(day => {
            const checkbox = document.getElementById(`check-${day}`);
            if (checkbox.checked) {
                const timeInput = document.getElementById(`time-${day}`);
                if (timeInput.value.trim() !== "") {
                    config[day] = timeInput.value.trim();
                }
            }
        });
        jsonOutput.value = JSON.stringify(config, null, 4);
    });
});
