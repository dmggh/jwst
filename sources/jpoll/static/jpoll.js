var jpoll = {};

// Console logging for Jpoll status
jpoll.log = function (text) {
    console.log("JPOLL: " + text);
};

// Function which handles a "log_message" message.
jpoll.log_message = function(text) {
    $("#jpoll_log").append("<p>" + text + "<p>");
    console.log(text);
};

jpoll.open_channel = function() {
    return $.getJSON("/jpoll/open_channel/").done(function(response) {
        jpoll.log("open_channel succeeded: " + response);
        jpoll.channel = response;
    }).fail(function(response) {
        jpoll.log("open_channel failed: " + response);        
    });
};

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

jpoll.start = function (interval_msec) {
    if (interval_msec) {
        jpoll.interval_msec = interval_msec;
    };
    jpoll.open_channel();
    jpoll.poll_interval_id = setInterval(jpoll.pull_messages, jpoll.interval_msec);
};

jpoll.stop = function () {
    if (jpoll.poll_interval_id) {
        clearInterval(jpoll.poll_interval_id);
        jpoll.poll_interval_id = null;
    };  
};



