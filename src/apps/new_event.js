document.getElementById('eventForm').onsubmit = function(event) {
    event.preventDefault(); // Prevent form from submitting the traditional way

    // Get values from the form
    var eventName = document.getElementById('eventName').value;
    var eventDate = document.getElementById('eventDate').value;
    var eventTime = document.getElementById('eventTime').value;

    // Here you could send the data to a server or process it further
    console.log("Event Scheduled:",eventDate, eventTime);

    // Select the submit button
    var submitButton = document.getElementById('submit');
    submitButton.onclick = function() {
        window.Telegram.WebApp.sendData(JSON.stringify("NONRECURRINGEVENT~".concat(eventName, "~", eventDate, "~", eventTime)));

    };

};
