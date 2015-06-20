crds.set_header_contents = function (input) {
        
		var file = input.files[0];
		
		crds.set_info_box({text: "Loading FITS header... " + file.name });                                   
		crds.append_info_box({text: "This may take a while for large files.", css:{color:"darkblue"}});
		
		crds.process_file_header_string(file);
};

crds.process_file_header_string = function (file) {
		if (/.fits$/.test(file.name)) {
            	return crds.process_fits_header_string(file);
		} else {
                alert("Browser can't handle headers for this file type.   Use 'Uploaded' instead.");
                return "";
		};
};

crds.process_fits_header_string = function (file) {
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
        // replace the file element with a text area containing header lines
		console.log("set_header_textarea", file, header_val);
        if (!header_val) {
				return crds.set_radio_clear_fits("dataset_uploaded");
        } else {
				crds.set_radio("dataset_mode", "dataset_local");
				$("#dataset_local_textarea").text(header_val);
				$("#dataset_name").val(file.name);
				$("#dataset_local_file").replaceWith(
						'<input type="file" id="dataset_local_file" onchange="crds.set_header_contents(this);" />'
						);
				$("#dataset_local_file").on("change", function () {
								return crds.set_header_contents($("#dataset_local_file")[0]);
						});
				crds.clear_info_box();
		};
};
      
crds.set_radio_clear_fits = function(mode) {
		console.log("crds.set_radio_clear_fits " +  mode);
		if (mode != "dataset_local") {
				$("#dataset_name").val("");
				$("#dataset_local_file").val("");
				$("#dataset_local_textarea").val("");
		};
		// if (mode != "dataset_archive") {
		// 		$("#dataset_archive").val("");
		// };
		// if (mode != "dataset_uploaded") {
		// 		$("#dataset_uploaded").val("")
		// };
		crds.set_radio("dataset_mode", mode);
};

function validate(evt) {
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

