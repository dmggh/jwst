// <script type="text/javascript">
    $( function () {
        crds.validate_select_pmap = function () {
            console.log("validating select_pmap.");
            var pmap_mode = $("input[name='pmap_mode']:checked").val();
            if ( pmap_mode == "pmap_text") {
                var pmap = $("input[name='pmap_text']").val();
                if (!/^.+.pmap$/.test(pmap) && $.trim(pmap)) {
                    alert("Invalid .pmap name");
                    return false;
                };
            };
            var pmap_option;
            if (pmap_mode == "pmap_text") {
                pmap_option = pmap;
                title = "User Specified";
            } else if (pmap_mode == "pmap_edit") {
                pmap_option = $("input[value='pmap_edit']").parent().next().children().val();
                title = "Editing Context";
            } else if (pmap_mode == "pmap_operational") {
                pmap_option = $("input[value='pmap_operational']").parent().next().children().val();
                title = "Operational Context";
            } else if (pmap_mode == "pmap_menu") {
                pmap_option = $("select[name='pmap_menu'] option:selected").val()
                title = "Recent Context";
            } else {
                    console.log("Bad pmap_mode ", pmap_mode);
            };
    
            var pmap_label;
            if (pmap_option in crds.pmap_labels) {
               pmap_label = crds.pmap_labels[pmap_option].replace("*bad*","<span class='error'>*bad*</span>");
            } else {
               pmap_label = pmap_option + " *unknown*";
            };
            var pmap_status = pmap_label + " (" + title + ")";
            $("#pmap_status").html(pmap_status);
            return true;
        };
        crds.close_pmap_accordion = function () {
            $(".accordion").accordion({
                active: false
            });
        };
        crds.select_pmap_onchange = function (pmap_mode) {
           crds.validate_select_pmap();
           crds.close_pmap_accordion();
           crds.set_radio("pmap_mode", pmap_mode);
        };
        crds.pmap_labels = JSON.parse($("#pmap_labels_json").text());
        $("#pmap_labels_json").hide();  
        crds.validate_select_pmap();
    });
    
// </script>
