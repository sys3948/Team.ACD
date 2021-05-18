const alter_table_event = (e) => {
      $.ajax({
        url : location.pathname,
        type : 'post',
        data : {'table_name' : document.getElementById('table-name').value},
        success : (response) => {
          if(response.confirm){
            let body = document.getElementById('column-table-body');
            let table_info = response.table_info.replace("[[", "").replace("]]", "");
            table_info = table_info.replaceAll("], [", "//");
            table_info.split("//").forEach(element => {
              const column_name = element.split(",")[0].replaceAll("'","");
              let type;
              let type_length;
              if(element.split(",")[1].includes("(")){
                type = element.split(",")[1].replace("b", "").replace("(", ".").replace(")","").replaceAll(" ","").split(".")[0].replaceAll("'","");
                type_length = element.split(",")[1].replace("b", "").replace("(", ".").replace(")","").replaceAll("'","").split(".")[1];
              } else{
                type = element.split(",")[1].replace("b", "").replaceAll("'","").replaceAll(" ","");
                type_length = false;
              }
              let null_able;
              if(element.split(",")[2].replaceAll("'", "").replaceAll(" ", "") === "YES"){
                null_able = true;
              } else {
                null_able = false;
              }
              let pk_able = false;
              let unique_able = false;
              if(!element.split(",")[3].replaceAll("'", "").replaceAll(" ", "")){
                // pk & unique를 설정 하지 않을 경우.
                pk_able = false;
                unique_able = false;
              } else{
                // pk & unique를 설정할 경우
                if(element.split(",")[3].replaceAll("'", "").replaceAll(" ", "") === 'PRI'){
                  pk_able = true;
                }
                if(element.split(",")[3].replaceAll("'", "").replaceAll(" ", "") === 'UNI'){
                  unique_able = true;
                }
              }

              console.log(element);
              console.log(type);
              let row = body.insertRow(body.rows.length);
              let cel0 = row.insertCell(0);
              let cel1 = row.insertCell(1);
              let cel2 = row.insertCell(2);
              let cel3 = row.insertCell(3);
              let cel4 = row.insertCell(4);
              let cel5 = row.insertCell(5);
              let cel6 = row.insertCell(6);

              cel0.innerHTML = '<input class="form-control input-colum column-name" type="text" placeholder="이름을 입력해주세요." value='+ column_name +' />';
              if(response.dbms === 'mysql' || response.dbms === 'maria'){
                console.log('mysql');
                console.log(type);
                if(type === 'tinyint'){
                  cel1.innerHTML =  '<div class="form-group select">' +
                                      '<select class="form-control column-type">' +
                                        '<option value="tinyint" selected>tinyint</option>' +
                                        '<option value="int">int</option>' +
                                        '<option value="float">float</option>' +
                                        '<option value="varchar">varchar</option>' +
                                        '<option value="text">Text</option>' +
                                        '<option value="datetime">datetime</option>' +
                                      '</select>' +
                                    '</div>';
                }
                if(type === 'int'){
                  console.log('type int!');
                  cel1.innerHTML =  '<div class="form-group select">' +
                                      '<select class="form-control column-type">' +
                                        '<option value="tinyint">tinyint</option>' +
                                        '<option value="int" selected>int</option>' +
                                        '<option value="float">float</option>' +
                                        '<option value="varchar">varchar</option>' +
                                        '<option value="text">Text</option>' +
                                        '<option value="datetime">datetime</option>' +
                                      '</select>' +
                                    '</div>';
                }
                if(type === 'float'){
                  cel1.innerHTML =  '<div class="form-group select">' +
                                      '<select class="form-control column-type">' +
                                        '<option value="tinyint">tinyint</option>' +
                                        '<option value="int">int</option>' +
                                        '<option value="float" selected>float</option>' +
                                        '<option value="varchar">varchar</option>' +
                                        '<option value="text">Text</option>' +
                                        '<option value="datetime">datetime</option>' +
                                      '</select>' +
                                    '</div>';
                }
                if(type === 'varchar'){
                  cel1.innerHTML =  '<div class="form-group select">' +
                                      '<select class="form-control column-type">' +
                                        '<option value="tinyint">tinyint</option>' +
                                        '<option value="int">int</option>' +
                                        '<option value="float">float</option>' +
                                        '<option value="varchar" selected>varchar</option>' +
                                        '<option value="text">Text</option>' +
                                        '<option value="datetime">datetime</option>' +
                                      '</select>' +
                                    '</div>';
                }
                if(type === 'text'){
                  cel1.innerHTML =  '<div class="form-group select">' +
                                      '<select class="form-control column-type">' +
                                        '<option value="tinyint">tinyint</option>' +
                                        '<option value="int">int</option>' +
                                        '<option value="float">float</option>' +
                                        '<option value="varchar">varchar</option>' +
                                        '<option value="text" selected>Text</option>' +
                                        '<option value="datetime">datetime</option>' +
                                      '</select>' +
                                    '</div>';
                }
                if(type === 'datetime'){
                  cel1.innerHTML =  '<div class="form-group select">' +
                                      '<select class="form-control column-type">' +
                                        '<option value="tinyint">tinyint</option>' +
                                        '<option value="int">int</option>' +
                                        '<option value="float">float</option>' +
                                        '<option value="varchar">varchar</option>' +
                                        '<option value="text">Text</option>' +
                                        '<option value="datetime" selected>datetime</option>' +
                                      '</select>' +
                                    '</div>';
                }
              }
              if(response.dbms === 'oracle'){
                if(type === 'number'){
                  cel1.innerHTML =  '<div class="form-group select">' +
                                      '<select class="form-control column-type">' +
                                        '<option value="number">number</option>' +
                                        '<option value="float">float</option>' +
                                        '<option value="varchar2">varchar2</option>' +
                                        '<option value="clob">clob(text)</option>' +
                                        '<option value="date">date</option>' +
                                      '</select>' +
                                    '</div>';
                }
                if(type === 'float'){
                  cel1.innerHTML =  '<div class="form-group select">' +
                                      '<select class="form-control column-type">' +
                                        '<option value="number">number</option>' +
                                        '<option value="float">float</option>' +
                                        '<option value="varchar2">varchar2</option>' +
                                        '<option value="clob">clob(text)</option>' +
                                        '<option value="date">date</option>' +
                                      '</select>' +
                                    '</div>';
                }
                if(type === 'varchar2'){
                  cel1.innerHTML =  '<div class="form-group select">' +
                                      '<select class="form-control column-type">' +
                                        '<option value="number">number</option>' +
                                        '<option value="float">float</option>' +
                                        '<option value="varchar2">varchar2</option>' +
                                        '<option value="clob">clob(text)</option>' +
                                        '<option value="date">date</option>' +
                                      '</select>' +
                                    '</div>';
                }
                if(type === 'clob'){
                  cel1.innerHTML =  '<div class="form-group select">' +
                                      '<select class="form-control column-type">' +
                                        '<option value="number">number</option>' +
                                        '<option value="float">float</option>' +
                                        '<option value="varchar2">varchar2</option>' +
                                        '<option value="clob">clob(text)</option>' +
                                        '<option value="date">date</option>' +
                                      '</select>' +
                                    '</div>';
                }
                if(type === 'date'){
                  cel1.innerHTML =  '<div class="form-group select">' +
                                      '<select class="form-control column-type">' +
                                        '<option value="number">number</option>' +
                                        '<option value="float">float</option>' +
                                        '<option value="varchar2">varchar2</option>' +
                                        '<option value="clob">clob(text)</option>' +
                                        '<option value="date">date</option>' +
                                      '</select>' +
                                    '</div>';
                }
              }

              if(type_length){
                cel2.innerHTML = '<input class="form-control input-colum column-type-length" type="text" placeholder="타입 길이값을 입력해주세요." value="'+ type_length +'" />';
              }else{
                cel2.innerHTML = '<input class="form-control input-colum column-type-length" type="text" placeholder="타입 길이값을 입력해주세요." value="" />';
              }

              if(null_able){
                cel3.innerHTML = '<input type="checkbox" class="form-control column-not-null" value="not null" checked />';
              } else{
                cel3.innerHTML = '<input type="checkbox" class="form-control column-not-null" value="not null" />';
              }

              if(unique_able){
                cel4.innerHTML = '<input type="checkbox" class="form-control column-unique" value="unique" checked />';
              } else {
                cel4.innerHTML = '<input type="checkbox" class="form-control column-unique" value="unique" />';
              }

              if(pk_able){
                cel5.innerHTML = '<input type="checkbox" class="form-control column-pk" value="primary key" checked />';
              }else{
                cel5.innerHTML = '<input type="checkbox" class="form-control column-pk" value="primary key" />';
              }
              cel6.innerHTML = '<input type="text" class="form-control input-colum column-default-value" value="" />';

            });
            document.getElementById('table').style.display = 'block';
          }else{
            document.getElementById('alert-block').style.display = 'block';
            document.getElementById('alert-msg').innerText = response.msg;
          }
        }
      })
    }