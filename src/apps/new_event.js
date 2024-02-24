document.getElementById('eventForm').onsubmit = function(event) {
    event.preventDefault(); // Prevent form from submitting the traditional way

    // Get values from the form
    var eventName = document.getElementById('eventName').value;
    var eventDate = document.getElementById('eventDate').value;
    var eventTime = document.getElementById('eventTime').value;

    // Here you could send the data to a server or process it further
    console.log("Event Scheduled:", eventName, eventDate, eventTime);

    // Optionally, clear the form or provide feedback to the user
    alert(`Event "${eventName}" scheduled for ${eventDate} at ${eventTime}.`);
    this.reset(); // Reset form fields
};
