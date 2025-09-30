# Architecture Layout

## Big picture
I want to reconsider my approach to the python script. First of all, I want to move from JSON to SQLite3 as much of the current logic is just opening and reading from json files logic. I want to start with a firm schema, keep it as basic as possible, and consider how I would process the files without any python script. Technically, I could store any data in the database through the terminal, and I could move and rename files as well, which is all that this goal burns down to. 

## The schema

### Files table
- id
- sha256_hash
- extension
- created_ts
- inserted_ts
- collection_id
- description
- embedding

### Collections table
- id
- inserted_ts
- description
- embedding


## Collection logic
Collections make handling semantically similar files easier. Without collections, I would either need to copy and paste the same description for each of them, or try to make the descriptions so percise that there are differences between them. With collections, I can store a description "These photos are of our family trip to lake tahoe", and associate it with that collection of photos. I will choose to avoid nested collections for now. A file may only belong to one collection.

## Top level interface
Idea: Files can be placed in three seperate folders. 

1. This folder iterates through every file, lets me record description for it, then deletes it. Good for when I dont want to associate it to a collection
2. This folder makes a new collection, lets me record a description for it, and then associates every file in it with that description before deleting all the files.
3. This folder lets me ingest a file and record a description for it, but does not delete it. It can later be moved to folder two to be ingested as part of a collection. Since it already exists, it just gets associated to the collection and then deleted. This is good for files which I want to associate with a collection but also be able to individually identify. 

## Optional description / collection stratergy
Instead of passing them down through function chains, ill just create the file and add it first without them, then associate the description / collection afterwards.