create table user(
  id int auto_increment primary key,
  user_id varchar(20) not null unique,
  password_hash varchar(225) not null,
  email varchar(50) not null unique,
  stampdate datetime,
  grant_num int default 0,
  manager int default 0,
  confirmed boolean default 0
);

create table dbms_info(
  db_id int auto_increment primary key,
  user_id int not null,
  dbms varchar(10) not null,
  hostname varchar(16) not null,
  port_num varchar(5) not null,
  alias varchar(10),
  dbms_connect_pw varchar(30),
  dbms_connect_username varchar(30),
  dbms_schema varchar(30),
  inner_num int default 1,	
  foreign key(user_id) references user(id) on delete cascade
);

create table delete_user(
  id int auto_increment primary key,
  user_id varchar(20) not null unique,
  email varchar(50) not null unique,
  stampdate datetime
);

create index users on  user(user_id, email);

 DROP TRIGGER IF EXISTS delete_user_trg;
 
