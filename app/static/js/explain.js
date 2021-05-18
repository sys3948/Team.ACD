(function($){

    const MYSQL_ACCESS_TYPE = {
        "SYSTEM" : "Single row: system constant	",
        "CONST"  : "Single row: constant",
        "EQ_REF" : "Unique Key Lookup",
        "REF"    : "Non-Unique Key Lookup",
        "FULLTEXT" : "Fulltext Index Search",
        "REF_OR_NULL" : "Key Lookup + Fetch NULL Values",
        "INDEX_MERGE" : "Index Merge",
        "UNIQUE_SUBQUERY":"Unique Key Lookup into table of subquery",
        "INDEX_SUBQUERY" :"Non-Unique Key Lookup into table of subquery",
        "RANGE":"Index Range Scan",
        "INDEX":"Full Index Scan",
        "ALL":"Full Table Scan",
    }

    

    $.fn.show_explain = function(dbms,exp_results){
        $(this).empty();
        if(dbms == "oracle"){
           oracle_explain(this,exp_results);

        }else{
            mysql_explain(this,exp_results,0);
        }
            
    }

    //oracle 실행계획
    function oracle_explain(element,exp_results){

      for(var arr of exp_results){
          var depth = get_space_count(arr[0]);
          
          make_ul(
            element,
            arr[1].trim(),
            depth-1,
            arr[0].trim(),
            arr[4].trim()
          )
      }

    }
    //글자앞 공백 세기
    function get_space_count(str){
      var cnt = 0;
      for(var el of str){
        if(el != " ") break;
        cnt++;
      }
      return cnt;
    }

    


    //mysql 실행계획
    function mysql_explain(element,json,depth){
  
        Object.keys(json).forEach(function(key){
      
            if("nested_loop" == key){
                for(var i=0; i<json[key].length-1 ; i++){
                    var new_depth = depth+i;
                    make_ul(
                        element=element,
                        name=key,
                        new_depth,
                        access_type=null,
                        cost=0
                      );

                }
                

            }else if("grouping_operation" == key){
              
              make_ul(
                      element=element,
                      name=key,
                      depth=depth,
                      access_type=null,
                      cost=0
                    );
      
            }else if(/^.+_subqueries$/.test(key)){
              
              make_ul(
                      element=element,
                      name=key,
                      depth=depth,
                      access_type=null,
                      cost=json[key][0].query_block.cost_info.query_cost
                    );
      
            }else if(key == "query_block"){
              
              if($("#explain ul").length==0){
                make_ul(
                        element=element,
                        name=key,
                        depth=depth,
                        access_type=null,
                        cost=json[key].cost_info.query_cost
                        );
                mysql_explain(element,json[key],depth+1);
              }else{
                mysql_explain(element,json[key],depth);
              }
            }
            
            if(key == "table"){
            
              make_ul(
                        element=element,
                        name=json[key].table_name,
                        depth=depth,
                        access_type=MYSQL_ACCESS_TYPE[json[key].access_type.toUpperCase()],
                        cost=json[key].cost_info.eval_cost
                      );
                mysql_explain(element,json[key],depth+1);
            } 
      
            if(Array.isArray(json[key])){


                if(key == "nested_loop"){
                    var new_depth =  depth + json[key].length-1;
                    for(var i in json[key]){

                        new_depth = (i <= 1)?  new_depth  : --new_depth;
                        mysql_explain(element,json[key][i],new_depth);
                    }
                    
                }else{
                    for(var i in json[key]){
                        mysql_explain(element,json[key][i],depth+1);
                      }
                }
            }
          
              
        });
    }

    //mysql, mariadb 용
    function make_ul(element,name,depth,access_type,cost){
        console.log("element: "+element);
        console.log("name: "+name);
        console.log("depth: "+depth);
        console.log("acess_type: "+access_type);
        console.log("cost: "+cost);
        
        access_type = (access_type == null) ? "" : access_type;
        //cost = (name == "query_block") ? "query_cost:"+cost : "cost:"+cost;
        cost =  "Cost: "+cost;
        
        var ul = "";
        ul += "<ul id='depth-"+depth+"'>";
        ul += "<li>";
        ul += "<span class='text-info name'>"+name+"</span>&nbsp&nbsp";
        ul += "<span class='text-danger access_type'>"+access_type+"</span><br>";
        ul += "<span class='text-primary cost'>"+cost+"</span>";
        ul += "</li>";
        ul += "</ul>"
        
        if(depth == 0) $(element).append(ul)
        else $("#depth-"+(depth-1)).append(ul);
      
    }


}(jQuery));