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
