// <script type="text/javascript">
  
    var readStart = function(progressEvent) {
        console.log('readStart',progressEvent);
    }
    
    var readEnd = function(progressEvent) {
        console.log('readEnd',progressEvent,this);
        var fileReader = this;
        var fileContent = fileReader.result;
        var fileName = fileReader.file.name;
        // Note you can not retreive file path, for security reasons. 
        // But you are not supposed to need it, you already have the content ;)
        console.log('readEnd:',fileName,fileContent);
        fileread_done(fileReader.file,  fileReader.result);
    }
    
    // var readProgress = function(progressEvent) {
    //     console.log('readProgress',progressEvent);
    //     if (progressEvent.lengthComputable) {
    //         var percentage = Math.round((event.loaded * 100) / event.total);
    //         console.log('readProgress: Loaded : '+percentage+'%');
    //     }
    // }
    
    var readErr = function(progressEvent) {
        console.log('readErr',progressEvent);
        switch(progressEvent.target.error.code) {
            case progressEvent.target.error.NOT_FOUND_ERR:
                alert('File not found!');
                break;
            case progressEvent.target.error.NOT_READABLE_ERR:
                alert('File not readable!');
                break;
            case progressEvent.target.error.ABORT_ERR:
                break; 
            default: 
                alert('Unknow Read error.');
        }
    }
    
    var readFile = function(file) {
        var reader = new FileReader();
        reader.file = file; // We need it later (filename)
        reader.addEventListener('loadstart', readStart, false);
        reader.addEventListener('loadend', readEnd, false);
        reader.addEventListener('error', readErr, false);
        // reader.addEventListener('progress', readProgress, false);
        reader.readAsBinaryString(file);
    }
    
    var drop = function(event) {
        event.preventDefault();
        var dt = event.dataTransfer;
        var files = dt.files;
        for (var i = 0; i<files.length; i++) {
            var file = files[i];
            readFile(file);
        }
    }
    
    window.addEventListener("drop", drop);
    
      function get_header(filename, file_string) {
            if (/.fits$/.test(filename)) {
            	return fits_get_header(file_string);
            } else {
                alert("Browser can't handle headers for this file type.   Use 'Uploaded' instead.");
                return "";
            }
      }
      
      function fits_get_header(file_string) {
            var record_no = 0;
            var rec = fits_read_record(file_string, record_no);
            var header = "";
            while (rec.length) {
                var result = header_lines(get_cards(rec));
                header += result[0];
                if (result[1]) {
                    return header;
                }
                record_no += 1;
                rec = fits_read_record(file_string, record_no);
            }
            return header;
      }
      
      function fits_read_record(file_string, record_no) {  // read a FITS record
        var beg = 2880*record_no;
        var end = Math.min(file_string.length, 2880*(record_no + 1));
        // console.log(record_no + " " + beg + " " + end);
        return file_string.slice(beg, end);
      }
      
      function get_cards(record) {
        var i = 0;
        var cards = new Array();
        for ( ; 80*i < record.length; i++) {
            cards[i] = record.slice(80*i, 80*(i+1));
        }
        return cards;
      }
      
      function header_lines(cards) { // Return "header lines" assoc with cards
        var i;
        var header = "";
        for(i in cards) {
            var card = cards[i];
            if (card.slice(8,9) == "=") {
                header += card_line(card);
            } else {
                console.log("skipping card: " + card)
            }
            if (fits_keyword(card) == "END") {
                return [ header, true ];
            }
        }
        return [ header, false ];
      }
      
      function card_line(card) {  // format a card into "<key> <value> <eol>"
            var key = fits_keyword(card);
            var value;   
            if (card.indexOf("/") > 0) { // handle comments
                value = $.trim(card.slice(10, card.indexOf("/")));
            } else {
                value = $.trim(card.slice(10, card.length));
            }
            if (value[0] == "'") {
                value = $.trim(value.slice(1, value.length-1));
            }
            var line = key + " " + value + "\n";
            if ($.trim(line)) {
                return line;
            } else {
                return "";
            }
      }
      
      function fits_keyword(card) {   // return the FITS keyword of a card.
        return $.trim(card.slice(0,8));
      };   
      
      function set_contents(input) {
        
        console.log("set_contents:", input);
        
        var file = input.files[0];
                                           
        crds.set_info_box({text: "Loading FITS header... " + file.name });                                   
        crds.append_info_box({text: "This may take a while for large files.", css:{color:"darkblue"}});
      
        readFile(file);
        
      };
      
      function fileread_done(file,  file_contents) {
        
        // replace the file element with a text area containing header lines
        var header_val = get_header(file.name, file_contents);
        if (!header_val) {
            file.value = "";
            crds.set_radio("dataset_mode","dataset_uploaded");
            return;
        }
        var header_textarea = $("<textarea name='dataset_local' rows='5' cols='40'>")
                             .text(header_val)
        var dataset_name = $("<input type='hidden' name='dataset_name'/>")
                            .val(file.name);
        $("#dataset_local").after(header_textarea);
        header_textarea.after(dataset_name);
        $("#dataset_local").remove();
        $(file).val(file.name);

        crds.set_radio("dataset_mode", "dataset_local");
        crds.clear_info_box();
      }
      
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

      crds.set_radio_clear_fits = function(mode) {
	console.log("crds.set_radio_clear_fits " +  mode);
	crds.set_radio("dataset_mode", mode);
	if (mode != "dataset_local") {
	   var input = $("<input type='file' id='dataset_local' onchange='set_contents(this);'>Upload FITS Header");
	   $("#dataset_local_input_td").html(input);
	}
      }

// </script>
