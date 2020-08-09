/*
* Create run table.
*
* To run in shell:
* > mysql -u username -p < path-to\scriptName.sql
*
*/
use keyruns;


/*drop table run;
/*drop table character;


/* Table for key run data. */
create table run(
id bigint unsigned PRIMARY KEY NOT NULL,
dungeon smallint unsigned NOT NULL,
level tinyint unsigned NOT NULL,
period smallint unsigned NOT NULL,
timestamp bigint unsigned NOT NULL,
duration bigint unsigned NOT NULL,
region tinyint unsigned NOT NULL);


/* Table for characters that occur in key runs */
create table player_character(
run_id bigint unsigned,
id bigint unsigned,
name tinytext,
spec smallint unsigned,
realm smallint unsigned);
