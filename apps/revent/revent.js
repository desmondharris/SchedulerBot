 // Spawn elements for day selectors
document.getElementById('freqs').addEventListener('change', function() {
    let selectedValue = this.value; // Get selected option value
    switch (selectedValue) {
        case 'weekly':
            // If different frequency selected, remove the old element
            if (document.getElementById("onDayOfMonth")) {
                document.getElementById("onDayOfMonth").remove();
            }
            // Spawn day selector
            let onDay = document.createElement("select");
            onDay.id = "onDay";
            let days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
            for (let i = 0; i < days.length; i++) {
                const option = document.createElement("option");
                option.value = days[i];
                option.text = days[i];
                onDay.appendChild(option);
            }
            document.getElementById("toSpawn").appendChild(onDay);
            break;
        case 'monthly':
            if (document.getElementById("onDay")) {
                document.getElementById("onDay").remove();
            }
            // Spawn day selector
            let onDayOfMonth = document.createElement("input");
            onDayOfMonth.id = "onDayOfMonth";
            onDayOfMonth.type = "number";
            onDayOfMonth.min = "1";
            onDayOfMonth.max = "31";

            document.getElementById("toSpawn").appendChild(onDayOfMonth);

    }
});

document.getElementById('eventForm').onsubmit = function(event) {
    let eventName = document.getElementById('eventName').value;
    let eventTime = document.getElementById('eventTime').value;
    let freq = document.getElementById('freqs').value;

    // Collect selected reminders
    let selectedReminders = document.querySelectorAll('input[name="reminders"]:checked');
    let reminders = Array.from(selectedReminders).map(checkbox => checkbox.value);

    // Send info to backend
    let freqString = "";
    if (freq === "weekly") {
        freqString = "WEEKLY".concat("~", document.getElementById('onDay').value);
    } else if (freq === "monthly") {
        freqString = "MONTHLY".concat("~", document.getElementById('onDayOfMonth').value);
    } else if (freq === "daily") {
        freqString = "DAILY";
    }

    let data = {
        type: "RECURRINGEVENT",
        eventName: eventName,
        freq: freqString,
        eventTime: eventTime,
        reminders: reminders
    };

    window.Telegram.WebApp.sendData(JSON.stringify(data));
    window.Telegram.WebApp.close();
}
