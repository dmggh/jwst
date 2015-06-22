crds.set_header_contents = function (input) {
		// console.log("set_header_contents", input);
		var file = input.files[0];
		if (file) {
		
				crds.set_info_box({text: "Loading FITS header... " + file.name });                                   
				crds.append_info_box({text: "This may take a while for large files.", css:{color:"darkblue"}});
				crds.process_file_header_string(file);
		};
};

crds.process_file_header_string = function (file) {
		//console.log("process_file_header_string", file);
		if (/.fits$/.test(file.name)) {
            	return crds.process_fits_header_string(file);
		} else {
                alert("Browser can't handle headers for this file type.   Use 'Uploaded' instead.");
                return "";
		};
};

crds.process_fits_header_string = function (file) {
		// console.log("process_fits_header_string", file);
		var fits = new astro.FITS(file, function(fits) { 
						var hdr = new Object();
						for (var i in fits.hdus) {
								var hdu = fits.hdus[i];
								for (var key in hdu.header.cards) {
										if (key =="COMMENT" || key == "HISTORY") {
												continue;
										};
										if (!(key in hdr)) {
												hdr[key] = hdu.header.cards[key]
										} else {
												// console.log("Multiple header definitions for '" + key + "'.  Using first.");
										};
								};
						};
						var hdr_string = "";
						for (key in hdr) {
								hdr_string += key + " " + hdr[key].value + "\n";
						};
						crds.set_header_textarea(file, hdr_string);
				});
		return fits;
};

crds.set_header_textarea = function(file,  header_val) {
		// console.log("set_header_textarea", file, header_val);
		$("#dataset_local_textarea").val(header_val);
		$("#dataset_name").val(file.name);		
		crds.clear_info_box();
		crds.set_radio_clear_fits("dataset_local");
};
      
crds.set_radio_clear_fits = function(mode) {
		// console.log("crds.set_radio_clear_fits " +  mode);
		if (mode != "dataset_local") {
				$("#dataset_name").val("");
				$("#dataset_local_file").val("");
				$("#dataset_local_textarea").val("");
		};
		if (mode != "dataset_archive") {
		 		$("#dataset_archive").val("");
		};
		if (mode != "dataset_uploaded") {
		 		$("#dataset_uploaded").val("");
		};
		crds.set_radio("dataset_mode", mode);
};

function validate(evt) {
		// console.log("dataset_bestrefs crds.validate()", evt);
        if (!crds.validate_select_pmap()) {
				return false;
        }
        var dataset_mode = $("input[name='dataset_mode']:checked").val();
        console.log("dataset_mode", dataset_mode);
        if (dataset_mode == "dataset_uploaded") {
				if ($("#dataset_uploaded")[0].files.length == 0) {
						alert("Did you add some files?");
						return false;
				}
        } else if (dataset_mode == "dataset_archive") {
				if (!$("#dataset_archive").val()) {
						alert("Did you set the dataset id?");
						return false;
				}
        } else if (dataset_mode == "dataset_local") {
				if (!$("textarea[name='dataset_local']").length) {
						alert("Did you choose a FITS file to extract a header from?");
						return false;
				}   
        } else {
				console.log("Invalid dataset_mode");
        }      
        return true;
};

