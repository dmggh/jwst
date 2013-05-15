var crds = {};

// Set the overall value of a group of radio inputs named `radio_name`
// to `radio_value`.   Clear those not selected.
crds.set_radio  = function (radio_name, radio_value) {
    $("input:radio[name=" + radio_name + "]").prop("checked", false);
    $("input:radio[value=" + radio_value + "]").prop("checked", true);
  };

 // Strip the path off a filename,  returning only the basename.
 // basename("C:\fakepath\something.txt") -->  "something.txt"
crds.basename = function (path, suffix) {
    var b = path.replace(/^.*[\/\\]/g, '');     
    if (typeof(suffix) == 'string' && b.substr(b.length - suffix.length) == suffix) {
        b = b.substr(0, b.length - suffix.length);
    }
    return b;
 };

crds.info_html = function(pars) {
    var css = pars["css"] || {       
        "font-size": "1.4em",
        "font-weight": "bold",
        "color":"green",
    };
    return $("</p>").text(pars["text"]).css(css);
};

crds.set_info_box = function(pars) {
    $("#crds_info_box").html(crds.info_html(pars));
};

crds.append_info_box = function(pars) {
    $("#crds_info_box").append(crds.info_html(pars));
};

crds.clear_info_box = function () { 
    crds.set_info_box({text:""}); 
};

crds.log = function (args) {
    console.log(args);
};

crds.format_time = function(seconds) {
    var days = Math.floor(seconds / 3600 / 24);
    var seconds = seconds % (3600 * 24);
    var hours = Math.floor(seconds / 3600);
    seconds = seconds % 3600;
    var minutes = Math.floor(seconds / 60);
    seconds = seconds % 60;
    return days + ":" + crds.f02d(hours) + ":" + crds.f02d(minutes) + ":" + crds.f02d(seconds);
};

crds.f02d = function(n) {
    if (n > 9) {
        return "" + n;
    } else {
        return "0" + n;
    }
};

crds.lock_status_json = null;   // object not string.

crds.poll_lock_status = function () {
    $.getJSON("/lock_status/", function (json) {
        crds.lock_status_json = json;
        if (json.status == "ok" && !json.is_expired) {
            $(".lock_timer").html(json.time_remaining);
            $(".locked_instrument").html(json.name);
        } else {
            var fail_message;
            if (json.status != "ok") {
                fail_message = "LOCK FAILED: " + json.exception;
            } else {
                fail_message = "LOCK TIMEOUT: " + json.instrument;
            };
            $('#contents').html("<br/><br/><br/><h3 class='red' style='font-size: 1.5em;' align='center' >" + fail_message + " When ready to continue,  log out and log back in.");
            $('.locked_instrument').html("");
            $('.lock_timer').html("");
            clearInterval(crds.lock_timer_interval);
            if (crds.lock_timeout_action) {
                crds.lock_timeout_action();
            };
        };
    });
};

$(function() {
    // tune jquery-ui accordions to be closed at start.
    $( ".accordion" ).accordion({
             autoHeight: false,
             collapsible: true,
             active:false,
     });
});

