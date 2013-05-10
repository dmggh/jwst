var jpoll = {};

// Console logging for Jpoll status
jpoll.log = function (text) {
    console.log("JPOLL: " + text);
};

// Function which handles a "log_message" message.
jpoll.log_message = function(text) {
    $("#jpoll_log").append("<p>" + text + "<p>");
    $("#jpoll_log").scrollTop($("#jpoll_log")[0].scrollHeight);
    console.log("JPOLL (built-in): " + text);
};

// Establish the polling channel.
jpoll.open_channel = function() {
    return $.getJSON("/jpoll/open_channel/").done(function(response) {
        jpoll.log("open_channel succeeded: " + response);
        jpoll.channel = response;
    }).fail(function(response) {
        jpoll.log("open_channel failed: " + response);        
    });
};

// Start the poller.
jpoll.start = function (interval_msec) {
    if (interval_msec) {
        jpoll.interval_msec = interval_msec;
    };
    jpoll.poll_interval_id = setInterval(jpoll.pull_messages, jpoll.interval_msec);
};

// Stop the poller.
jpoll.stop = function () {
    if (jpoll.poll_interval_id) {
        clearInterval(jpoll.poll_interval_id);
        jpoll.poll_interval_id = null;
    };  
};


// Poll for messages
jpoll.pull_messages = function() {
    return $.getJSON("/jpoll/pull_messages/").done(function(response) {
        jpoll.log("pull_messages succeeded: " + response);
        // This event should basically execute jpoll.XXX(YYY) where XXX is msg[0] and YYY is msg[1]
        for (var msg in response) {
            jpoll.log("processing " + response[msg]);
            switch(response[msg][0]) {
                case "log_message" : 
                    jpoll.log_message(response[msg][1]);
                    break;
            };
        };
    }).fail(function(response) {
        jpoll.log("pull_messages failed: " + response);
    });
};

jpoll.interval_msec = 2500;

// Set up a form to submit an asynchronous request using AJAX
jpoll.make_form_ajax = function(form_id, data_type) {
    // prepare the form when the DOM is ready
    if (!data_type) {
        data_type = "html"
    };
    $("#" + form_id).ajaxForm({ 
        // dataType identifies the expected content type of the server response 
        dataType:  data_type,
        done: function (html) {
            jpoll.log(form_id + " succeeded.");
            jpoll.stop();
            document.body.innerHtml = html;
        },
        fail: function(html) {
            jpoll.log(form_id + " succeeded.");
            jpoll.stop();
        },
    });
    jpoll.open_channel();   //  potentially this could be done later,  just before submit.
};    

// Automatically set up every form on the page with class='jpoll_ajax_html_form' as an ajax form returning html.
// This is essentially a non-blocking submit,  which at first order,  "just works" thanks to jquery.forms.js
$(function () {
   $(".jpoll_ajax_html_form").each(jpoll.make_form_ajax);  
});
