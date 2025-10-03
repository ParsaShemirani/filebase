CREATE TABLE files (
	id INTEGER NOT NULL, 
	inserted_ts TEXT NOT NULL, 
	sha256_hash TEXT NOT NULL, 
	extension TEXT NOT NULL, 
	created_ts TEXT NOT NULL, 
	collection_id INTEGER, 
	description TEXT, 
	embedding TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (sha256_hash), 
	FOREIGN KEY(collection_id) REFERENCES collections (id)
);

CREATE TABLE collections (
	id INTEGER NOT NULL, 
	inserted_ts TEXT NOT NULL, 
	description TEXT, 
	embedding TEXT, 
	PRIMARY KEY (id)
);