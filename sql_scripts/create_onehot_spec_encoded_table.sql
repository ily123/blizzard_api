
/*
* Table encoding compostion of a run using one-hot type of encoding
* 
*
* To run in shell:
* > mysql -u username -p < path-to\scriptName.sql
*
*/


use keyruns;


/* Table for key run data. */
create table run_spec_compostion(




id bigint unsigned PRIMARY KEY NOT NULL,
dungeon smallint unsigned NOT NULL,
level tinyint unsigned NOT NULL,
period smallint unsigned NOT NULL,
timestamp bigint unsigned NOT NULL,
duration bigint unsigned NOT NULL,
region tinyint unsigned NOT NULL);


