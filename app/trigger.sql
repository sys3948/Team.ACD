DELIMITER //
CREATE TRIGGER delete_user_trg
	AFTER DELETE 
    ON user
    FOR EACH ROW
BEGIN
		INSERT INTO delete_user(user_id,email,stampdate) values(OLD.user_id,OLD.email,now());
END    

//