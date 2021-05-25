


  
(function($) { 
    $.fn.CSV = function(id,type){

        return new CSV(this,id,type);
    }


    var CSV = function(modal,id,type){
        this.id = id;
        this.modal = modal;
        this.type = type;
        this.source = undefined;

        
        var _this = this;
        //데이터베이스 선택 변경되면 
        $(".database-opt").change(function(){
            _this.request_table($(this).val());
        });

        // modal close
        $(this.modal).on('hidden.bs.modal', function (e) {
            _this.init();
    
        });



    }
    CSV.prototype = {
        constructor:CSV,
        //modal 초기화
        init : function() {
           
            $(this.modal).find('form')[0].reset()
            this.set_progress_kind("");
            this.set_progress(0+"%");
            this.show_error("");
            // 외부 접속시 
            if($(this.modal).find(".database-opt").length > 0){
                this.request_table($(this.modal).find(".database-opt option:selected").val());
            }
        },
        //외부접속시 선택한 데이터베이스 테이블 요청
        request_table : function(database_name){
            var _this = this;
            $(".table-opt").empty();
            var url = "/ajax_request_tables/"+this.id+"/"+database_name
            this.ajax_get(url)
            .done(function(response){
                //테이블 조회시 에러 발생하면
                if(response.error != undefined) _this.show_error(response.error);
                else $(".table-opt").append(_this.make_table_option(response.tables));
                
                if(_this.type == "export")
                    $("#save-file-name").val($("#export-modal .table-opt option:selected").val()+".csv");
            })
            
        },
        make_table_option : function(table_list){
            var options = "";
            for(var table of  table_list)
                options += "<option>"+table[0]+"</option>"
                
            return options;
        },
        set_progress_kind:function(text){
            $(".progress-kind").text(text);
        },
        show_progress:function(url){
            var _this = this;
            _this.source = new EventSource(url);
            
            _this.source.onmessage = function(event) {
                
                var data = event.data.split("&&");
                var state = data[0];
                var progress = data[1];
        
                _this.show_error("");
                _this.set_progress(progress+'%');
                if(data.length == 3){
                    _this.show_error(data[2]);
                    _this.source.close();
                }
                if(parseInt(progress) == 100){
                    console.log("연결 close");
                    _this.set_progress_kind("완료");
                    _this.source.close();

                    console.log(_this.type)
                    console.log(data[2]);
                    console.log(data[3]);
                    if(_this.type == "export"){
                        
                        $("input[name=encryption_file_name]").val(data[2]);
                        $("input[name=csv_file_name]").val(data[3]);
                        
                        $("#csv-download-form").submit();
                    }
                }
                
        
            }
        },
        show_error:function(error){
            if(error!="")
                $(".csv-error").css("display","block");
            else
                $(".csv-error").css("display","none");
        
            $(".csv-error-text").text(error);
        },
        is_selected_table:function(){
            if($(this.modal).find(".table-opt option:selected").val() == undefined){
                this.show_error("테이블을 선택해주세요.")
                return false;
            }
            this.show_error("");
            return true;
        },
        set_progress:function(percent){
            $('.progress-bar').css('width', percent).attr('aria-valuenow',percent);
            $('.progress-bar-label').text(percent);
        },

        ajax_get:function(url){
            return  $.ajax({
                url : url, 
                method : "GET",    
            })
            .fail(function(error){
                alert(error);
            })
        },
        ajax_post:function(url,data){
            return  $.ajax({
                url : url, 
                method : "POST",
                data:data,    
            })
            .fail(function(error){
                alert(error);
            })
        }

    }


}(jQuery));