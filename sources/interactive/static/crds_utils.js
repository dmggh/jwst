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

$(function() {
    // tune jquery-ui accordions to be closed at start.
    $( ".accordion" ).accordion({
             autoHeight: false,
             collapsible: true,
             active:false,
     });
});

