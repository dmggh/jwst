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
            $(".locked_instrument").html(json.user + " " + json.name);
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

// Tailor the CRDS base template to dynamically add a JPOLL log and
// hide the original column1 and column2 contents.
crds.setup_status_display = function (start_id, title) {

    // The #column1 was removed and replaced with twitter bootstrap
    // So, instead of looking for the div with id="column1"
    // I want to find the closest ancestor with a class that
    // starts with col-
    
    // Figure out the nearest ancestor div with "col-*" as a 
    // class name
    var div_col = $('#'+start_id).closest('div[class^=col-]');
    console.log('div col is ' + div_col);
    console.log(div_col);

    var div_col_classes = div_col.attr('class');
    console.log('div col classes are ' + div_col_classes);
    
    // Hide it (but maybe want to remove it)
    $(div_col).hide();
    
    // This is the big change:
    //    1. add in the classes from the one we just hid
    //    2.  insert after the one we just hid
    $("<div id='after-column1' class='"+div_col_classes+"'></div>").insertAfter(div_col);
    
    $("#after-column1").append(
        $("<h3>" + title + "</h3>").css({"text-align":"center"})
    ).append(
        $("<div id='jpoll_log'></div>")
    );
    $(".error").empty();
    
    // Initiate status/done polling to update log.
    jpoll.start();
    
    return true;                   
};

crds.validate_and_confirm_file_submit = function(form) {
    console.log("Validating file submission.");
    if (!crds.validate_select_pmap()) {
        return false;
    };
    console.log("Validating creator.");
    if (!$("#creator").val()) {
        alert("Did you add a Creator?");
        return false;
    };
    console.log("Validating description.");
    if (!$("#description").val()) {
        alert("Did you add a Description?");
        return false;
    };
    crds.set_info_box({text: "Processing files on the server now."});
    crds.append_info_box({
        text: "This may take several minutes depending on how many files you submitted and how.",
        css: {color: "darkblue"},
    });
    
    $("input[type='submit']").hide();
    
    // Added the form attribute id in here as it is a new parameter
    // to this function. 
    console.log('form is ');
    console.log(form);
    console.log('form id ' + $(form).attr('id'));
    crds.setup_status_display($(form).attr('id'), "Submission Status");
    
    return true;
};

crds.validate_and_confirm_add_delete = function(form) {
    console.log("Validating add delete");
    if (!crds.validate_select_pmap()) {
        return false;
    };
    console.log("Validating description.");
    if (!$("#description").val()) {
        alert("Did you add a Description?");
        return false;
    };
    crds.set_info_box({text: "Processing files on the server now."});
    crds.append_info_box({
        text: "This may take several minutes depending on how many files you submitted and how.",
        css: {color: "darkblue"},
    });
    
    $("input[type='submit']").hide();
    
    crds.setup_status_display($(form).attr('id'), "Add/Delete Status");
    
    return true;
};

crds.format_table = function (header_cols, body_rows) {
    var header = crds.tag("thead",
                          crds.tag("tr",
                                   crds.tag("th", header_cols)));
    var rows = new Array(), j = -1;
    $.each(body_rows, function (index, row) {
        rows[++j]= crds.tag("tr", 
                         crds.tag("td", row));
    });
    var body = crds.tag("tbody", rows.join(''));
    return crds.tag("table", header + body);
};

crds.tag = function (tag, items, attrs) {
    var attr_str = new Array(), j = -1;
    for (var attr in attrs) {
    	if (attrs.hasOwnProperty(attr)) {
	        attr_str[++j] = " " + attr + "='" + attrs[attr] +"'";
	    }
    };
    // items can be a simple string producing one element.
    if (typeof(items) === 'string') {
        var html = "<" + tag + attr_str.join('') + ">" + items + "</"+ tag + ">";
    } else {
    // items can be an array producing a concatenation of elements.
        var html_arr = new Array(), j = -1;
        var t1 = "<" + tag + attr_str.join('') + ">";
        var t2 =  "</"+ tag + ">";
        $.each(items, function (index, item) {
            html_arr[++j] = t1 + item + t2;
        });
        var html = html_arr.join('');
    };
    return html;
};

crds.html_unescape = function (escaped) {
    return escaped
        .replace(/&amp;/g, "&")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&quot;/g, "\"")
        .replace(/&#039;/g, "'");
};

crds.html_escape = function (text) {
    'use strict';
    var chr = {
        '"': '&quot;', '&': '&amp;', "'": '&#39;',
        '/': '&#47;',  '<': '&lt;',  '>': '&gt;'
    };
    return text.replace(/[\"&'\/<>]/g, function (a) { return chr[a]; });
};

$(function() {
    // tune jquery-ui accordions to be closed at start.
    $( ".accordion" ).accordion({
             autoHeight: false,
             collapsible: true,
             active:false,
     });
});

