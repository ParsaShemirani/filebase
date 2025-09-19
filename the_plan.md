### Backend
The PostgreSQL database with node / edge structure is the record data holder. It is defined using the SQLAlchemy models. FastAPI is exposed, GraphQL later only for viewing files. Docker hosts the PostgreSQL instance as well as the API.

### Ingestion
To get from a file on my computer to being stored in the server, the file goes through the ingestion process. Ideally, as much of the information generation happens on the server side, to generate file data like bytes, type, etc. Some data like when the file was created and the semantic file description must be provided from the client, either manually by the user or via the computer program.

### Frontend
To start, a simple ingestion python program which allows ingesting a single file.