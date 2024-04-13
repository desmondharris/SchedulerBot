document.getElementById('eventForm').onsubmit = function(event) {
    event.preventDefault(); // Prevent form from submitting the traditional way

    // Get values from the form
    let eventName = document.getElementById('eventName').value;
    let eventDate = document.getElementById('eventDate').value;
    let eventTime = document.getElementById('eventTime').value;

    // Select the submit button
    var submitButton = document.getElementById('submit');
    submitButton.onclick = function() {
        // Collect selected reminders
        let selectedReminders = document.querySelectorAll('input[name="reminders"]:checked');
        let reminders = Array.from(selectedReminders).map(checkbox => checkbox.value);
        let data = {
            type: "NONRECURRINGEVENT",
            eventName: eventName,
            eventDate: eventDate,
            eventTime: eventTime,
            reminders: reminders
        };
        window.Telegram.WebApp.sendData(JSON.stringify(data));
        window.Telegram.WebApp.close();
    };

};
