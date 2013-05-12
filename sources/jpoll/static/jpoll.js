var jpoll = {};

// Console logging for Jpoll status
jpoll.log = function (text) {
    console.log("JPOLL: " + text);
};

// Function which handles a "log_message" message.
jpoll.log_message = function(time, text) {
    $("#jpoll_log").append("<p>[" + time + "]  " + text + "<p>");
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

jpoll.interval_msec = 2500;

// Start the poller.
jpoll.start = function (interval_msec) {
    jpoll.log("starting.");
    if (interval_msec) {
        jpoll.interval_msec = interval_msec;
    } else {
        jpoll.interval_msec = 2500;
    };
    jpoll.poll_interval_id = setInterval(jpoll.pull_messages, jpoll.interval_msec);
};

// Stop the poller.
jpoll.stop = function () {
    jpoll.log("stopping.");
    if (jpoll.poll_interval_id) {
        clearInterval(jpoll.poll_interval_id);
        jpoll.poll_interval_id = null;
    };  
};


// Poll for messages
jpoll.pull_messages = function() {
    jpoll.log("pulling messages.")
    return $.getJSON("/jpoll/pull_messages/", function (response) {
        jpoll.log("pull_messages succeeded: " + response);
        // This event should basically execute jpoll.XXX(YYY) where XXX is msg[0] and YYY is msg[1]
        for (var index in response) {
            var msg = response[index];
            jpoll.log("processing " + msg.time + " " + msg.type);
            switch(msg.type) {
                case "log_message" : 
                    jpoll.log_message(msg.time, msg.data);
                    break;
            };
        };
    }).error(function(response) {
        jpoll.log("pull_messages failed: " + response);
    });
};

// Set up a form to submit an asynchronous request using AJAX
jpoll.make_form_ajax = function(junk, form) {
    jpoll.log("Ajaxifying form=" + form);
    $(form).ajaxForm({ 
        // dataType identifies the expected content type of the server response 
        dataType:  "html",
        // context: document,
        success: function (html) {
            jpoll.log("AJAX submit " + form + " succeeded: " + html);
            jpoll.stop();
            document.open();
            document.write(html);
            document.close();
            // document.body.innerHtml = html;
        },
        error: function(html) {
            jpoll.log("AJAX submit " + form + " failed: " + html);
            jpoll.stop();
        },
    });
    jpoll.open_channel();   //  potentially this could be done later,  just before submit.
};    

// Automatically set up every form on the page with class='jpoll_ajax_html_form' as an ajax form returning html.
// This is essentially a non-blocking submit,  which at first order,  "just works" thanks to jquery.forms.js
$(function () {
   $.each($(".jpoll_ajax_html_form"), (jpoll.make_form_ajax));  
});
