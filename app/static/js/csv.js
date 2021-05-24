


  
(function($) { 
    $.fn.CSV = function(){


    }


    var CSV = function(modal){
        this.modal = modal;

        $("#database-opt").change(function(){
            request_table($("#database-opt option:selected").val());
        });

    }
    CSV.prototype = {
        constructor:CSV,
        init : function() {
           
            $(this.modal).find('form')[0].reset()
            set_progress_kind("");
            set_progress(0+"%");
            show_import_error("");
            // 외부 접속시 
            if($("#database-opt").length > 0){
                request_table($("#database-opt option:selected").val());
            }
        },
        

    }


}(jQuery));