var jpoll = {};

// Console logging for Jpoll status
jpoll.log = function (text) {
    console.log("JPOLL: " + text);
};

// handler for polled messages
jpoll.log_message = function(time, message) {
    var seconds_only = time.split(".")[0];
    var combined_text = "[" +  seconds_only + "] " + message;
    jpoll.log("LOG_MESSAGE: " + combined_text);
    message = message.replace(/('[^']*')/g, "<span class='darkblue'>$1</span>");
    $("#jpoll_log").append(
        $("<p style='font-size: 1.25em;'>").append(
            $("<span class='darkgreen'>").html("[" + seconds_only + "]")                               
        ).append(
            $("<span>").html("  " + message)
        )
    );
    if ($("#jpoll_log")) {
        $("#jpoll_log").scrollTop($("#jpoll_log")[0].scrollHeight);
    };
};

// Initialize the page for jpoll.                                  
jpoll.init = function () {
   jpoll.init_log();
   $.each($(".jpoll_ajax_html_form"), (jpoll.make_form_ajax));
};

// set up the log div for log_messages
jpoll.init_log = function () {
    $("#jpoll_log").css({
        "overflow": "auto", 
        "height": "40em", 
        "max-height": "40em", 
        "border": "2px solid", 
        "border-color":"gray",
        "border-radius" : "6px",
        "padding" : "3px",
    });
};

// Function which handles a "done" message.
jpoll.done = function(time, result) {
    jpoll.log("DONE (built-in): " + result.result);
    jpoll.stop();
    jpoll.channel = null;
    if (result.status != 1) {
       window.location = result.result;
    } else {   // FAILED
       jpoll.log_message(time, "FAILED: <pre>" + result.result + "</pre>");
    };
};

// Function which handles a successful response.
jpoll.response_success = function (form, result) {
    jpoll.log("RESPONSE_SUCCESS (built-in): " + result.length + " bytes");
    jpoll.stop();
    var doc = document.open();
    doc.write(result);
    doc.close();
};

jpoll.response_error = function (form, response) {
    console.log("RESPONSE_ERROR (built-in): ", form, " : ", response);
    // Suppress proxy errors but respond to normal errors.
    // Many errors have a normal page response and won't get here anyway.
    if (response.status == 0) {
        jpoll.log("Ignoring normal error status: " + response.status);
        return;
    };
	if (response.status == 504 || response.status == 522) {
        jpoll.log("Ignoring proxy status error response: " + response.status);
        return;
    };
    var page = response.responseText.toLowerCase();
    var proxy_error = (page.indexOf("proxy") != -1) && (page.indexOf("error") != -1);
    if (proxy_error) {
        console.log("Ignoring proxy text response: " + page);
        return;
    };
    jpoll.stop();
    var doc = document.open();
    doc.write("<p>REQUEST FAILED:</p><pre>" + response.responseText + "<pre>");
    doc.close();
};

jpoll.ajax_error = function (event, jqxhr, settings, thrownError) {
	console.log("AJAX ERROR (built-in): ",  event, jqxhr, settings, thrownError);
    if (jqxhr.status == 0) {
		jpoll.log("Ignoring normal ajax status 0.");
        return;
    }
};

// Establish the polling channel.
jpoll.open_channel = function() {
    return $.getJSON("/jpoll/open_channel/").done(function(response) {
        jpoll.log("OPEN_CHANNEL succeeded: " + response);
        jpoll.channel = response;
    }).fail(function(response) {
        jpoll.log("OPEN_CHANNEL failed: " + response);        
    });
};

jpoll.interval_msec = 2500;

// Start the poller.
jpoll.start = function (interval_msec) {
    jpoll.log("starting.");
    jpoll.init_log();
    if (interval_msec) {
        jpoll.interval_msec = interval_msec;
    } else {
        jpoll.interval_msec = 2500;
    };
    jpoll.poll_interval_id = setInterval(jpoll.pull_messages, jpoll.interval_msec);
};

// For fully independent pages like submission pages,  does everything including
// channel creation.
jpoll.start_all =  function (interval_msec) {
   jpoll.init();
   jpoll.open_channel();
   jpoll.start(interval_msec);
}

// Stop the poller.
jpoll.stop = function () {
    jpoll.log("stopping.");
    if (jpoll.poll_interval_id) {
        clearInterval(jpoll.poll_interval_id);
        jpoll.poll_interval_id = null;
    };  
};


jpoll.last_seen = -1;

// Poll for messages
jpoll.pull_messages = function() {
    // jpoll.log("PULL_MESSAGES")
    return $.getJSON("/jpoll/pull_messages/" + jpoll.channel + "/" + jpoll.last_seen + "/", function (response) {
        // jpoll.log("PULL_MESSAGES succeeded: " + response);
        // This event should basically execute jpoll.XXX(YYY) where XXX is msg[0] and YYY is msg[1]
        for (var index in response) {
            var msg = response[index];
            // jpoll.log("processing " + msg.time + " " + msg.type);
            if (msg.id < jpoll.last_seen) {
                jpoll.log("Dropping duplicate message: " + msg.id + " " + msg.time + " " + msg.data);
                continue;
            }
            jpoll.last_seen = msg.id;
            switch(msg.type) {
                case "log_message" : 
                    jpoll.log_message(msg.time, msg.data);
                    break;
                case "done" :
					jpoll.done(msg.time, msg.data);
                    break;
            };
        };
    }).error(function(response) {
					console.log("PULL_MESSAGES failed: ")
					console.log(response.responseText);
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
            jpoll.log("AJAX submit " + form + " succeeded: " + html.length + " bytes");
            return jpoll.response_success(form, html);
            // document.body.innerHtml = html;
        },
        error: function(html) {
			console.log("AJAX submit " + form + " failed " + html);
            return jpoll.response_error(form, html);
        },
    });
    $(document).ajaxError(function(event, jqxhr, settings, thrownError) {
					jpoll.ajax_error(event, jqxhr, settings, thrownError)
    });    
    // jpoll.open_channel();   //  potentially this could be done later,  just before submit.
};    

// Automatically set up every form on the page with class='jpoll_ajax_html_form' as an ajax form returning html.
// This is essentially a non-blocking submit,  which at first order,  "just works" thanks to jquery.forms.js
// $(function () {
//   jpoll.init();
// });
